import { checkInput, checkOutput, getReviewStatus } from '../lib/api';
import { getCachedReview, getState, onStateChanged, setCachedReview } from '../lib/storage';
import { guardBus } from './guardBus.js';
import { getProvider } from './providers.js';

const provider = getProvider(window.location.hostname);

let enabled = true;
let bypassNextSend = false;
// 'auto' lets the backend's model_router pick small-vs-large based on the
// prompt's actual complexity.
let currentModel = 'auto';
// The prompt actually sent (after any masking), so the output check has the
// right grounding context.
let lastSentPrompt = '';

const pendingResponseTimers = new WeakMap();

// Tracks assistant-message nodes ControlPlane is currently rewriting (mask/
// review/block correction) so the MutationObserver below doesn't mistake our
// own DOM write for a fresh streamed response and re-trigger a check on it.
const correctingResponseNodes = new WeakSet();

// Tracks nodes with an in-flight output-guardrail request, so overlapping
// mutation events for the same node don't fire duplicate checks.
const checkingResponseNodes = new WeakSet();

function getPromptElement() {
    return document.querySelector(provider.promptSelector);
}

export function getPrompt() {
    return (
        getPromptElement()
            ?.innerText
            .trim()
        ?? ''
    );
}

/**
 * Replaces the composer's content with `text`.
 *
 * IMPORTANT: this returns whether the DOM write itself succeeded — it does
 * NOT guarantee the host page's own editor state (React/Lexical/ProseMirror,
 * whichever framework the site uses) actually adopted the change. Rich-text
 * editors frequently maintain their own internal model and can silently
 * ignore a raw innerHTML mutation, even with a dispatched `input` event,
 * because they never received the change through their own input pipeline.
 * When that happens the box can visually show the new text for a moment
 * while the editor still submits its OLD internal state on send — which is
 * exactly the bug that let an unredacted email through.
 *
 * Because of that, callers that inject redacted content MUST re-read
 * getPrompt() afterward and confirm it actually reflects the change before
 * treating the message as safe to send. See the verification step in
 * interceptSend() below — that check, not this function, is what actually
 * prevents unredacted content from going out.
 */
export function setPrompt(text) {
    const element = getPromptElement();

    if (!element)
        return false;

    element.focus();

    // Try execCommand first: unlike a raw innerHTML write, this goes through
    // the browser's native contenteditable input pipeline (it fires a real
    // `beforeinput`/`input` pair), which is what most rich-text editor
    // frameworks actually listen to. It's more likely to be picked up by
    // the page's own state than a synthetic event dispatched after the fact.
    try {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(element);
        selection.removeAllRanges();
        selection.addRange(range);
        const ok = document.execCommand('insertText', false, text);
        if (ok)
            return true;
    }
    catch {
        // execCommand is deprecated and some browsers/pages may reject it —
        // fall through to the manual DOM-write path below.
    }

    // Fallback: direct DOM write + synthetic input event. Best-effort only —
    // see the verification step in interceptSend(), which is the real
    // safety net regardless of which path was used here.
    element.innerHTML = '';

    const paragraph =
        document.createElement('p');

    paragraph.dir = 'auto';
    paragraph.textContent = text;

    element.appendChild(paragraph);

    element.dispatchEvent(
        new InputEvent('input', {
            bubbles: true,
            inputType: 'insertText',
            data: text,
        })
    );

    return true;
}

function getSendButton() {
    return document.querySelector(provider.sendSelector);
}

export function sendNow() {
    const sendButton = getSendButton();

    if (!sendButton)
        return false;

    /*
     * The user has already passed ControlPlane's input
     * guardrail. Record exactly what will be sent.
     */
    lastSentPrompt = getPrompt();

    /*
     * The synthetic click must not enter the interceptor
     * again and create another guardrail request.
     */
    bypassNextSend = true;

    sendButton.click();

    return true;
}

function wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Replaces the composer with `newContent` and sends it, verifying the swap
 * actually took before allowing the send — used whenever what should be
 * sent differs from what's currently typed (masked content, or an
 * approved/edited review result). Returns false (and sends nothing) if the
 * page wouldn't let the replacement take effect.
 */
async function replaceAndSend(originalPrompt, newContent) {
    setPrompt(newContent);
    await wait(120);
    const verifiedPrompt = getPrompt();
    const replacementDidNotStick = verifiedPrompt === originalPrompt || verifiedPrompt !== newContent;
    if (replacementDidNotStick) {
        return false;
    }
    sendNow();
    return true;
}

// Verdicts that must NEVER auto-send — the whole point of the guardrail is
// that these stop and wait for the user (or a reviewer) before anything
// leaves the browser.
const BLOCKING_VERDICTS = new Set(['block', 'review']);

async function interceptSend(event) {
    /*
     * If protection is disabled, let ChatGPT handle the
     * original event normally.
     */
    if (!enabled || bypassNextSend) {
        bypassNextSend = false;
        return;
    }

    const prompt = getPrompt();

    if (!prompt)
        return;

    /*
     * Stop ChatGPT's native send action until the input
     * guardrail decision has completed.
     */
    event.preventDefault();
    event.stopPropagation();

    if (
        'stopImmediatePropagation' in event
    ) {
        event.stopImmediatePropagation();
    }

    const promptHash = hashContent(prompt);

    // Check the persistent review cache BEFORE calling the backend at all —
    // same reasoning as the output side: without this, resending the exact
    // same message that's still awaiting review creates a second, redundant
    // review every time instead of recognizing one is already in flight.
    const cached = await getCachedReview(promptHash);
    if (cached?.status === 'resolved') {
        guardBus.emit({ status: 'pass', result: { reasons: ['Approved by reviewer'] } });
        const sent = await replaceAndSend(prompt, cached.finalContent);
        if (!sent) {
            guardBus.emit({ status: 'error', error: "This message was approved with edits, but this page wouldn't let ControlPlane apply them. Please paste the approved text yourself and send again." });
        }
        return;
    }
    if (cached?.status === 'pending') {
        guardBus.emit({ status: 'review', result: { reasons: ['Still awaiting reviewer approval — not sent again to avoid duplicate reviews.'] } });
        return;
    }

    guardBus.emit({
        status: 'checking',
    });

    try {
        const result = await checkInput(prompt, currentModel);
        guardBus.emit({ status: result.verdict, result });

        if (result.verdict === 'pass') {
            if (result.content && result.content !== prompt) {
                // Content differs from what's typed — either a reviewer's
                // approved edit (the review-approval shortcut on the
                // backend returns PASS with the reviewer's final text, not
                // the raw prompt) or a token-optimized rewrite. Either way,
                // sendNow() alone would send the RAW box contents and
                // silently ignore this — which was the exact bug that let
                // an approved-with-edits message go out unmodified.
                const sent = await replaceAndSend(prompt, result.content);
                if (!sent) {
                    guardBus.emit({ status: 'error', error: "ControlPlane couldn't safely apply the approved/optimized text to this page. Please copy it manually and send again." });
                }
                return;
            }
            // Unmodified clean content — behave like a normal chat client
            // and send it immediately.
            sendNow();
            return;
        }

        if (result.verdict === 'mask' && result.optimized_content) {
            const sent = await replaceAndSend(prompt, result.optimized_content);
            if (!sent) {
                // This is the failure mode that let an unredacted email
                // through: our write didn't reach the page's real editor
                // state. Hard stop — never send on unverified content.
                guardBus.emit({
                    status: 'error',
                    error: "Sensitive info was detected, but this page wouldn't let ControlPlane safely replace it in the message box. Nothing was sent — please remove the sensitive info yourself and send again.",
                });
            }
            return;
        }

        if (result.verdict === 'review' && result.review_id) {
            // Cache pending state so resending this exact message (or a
            // refresh, in the output-check case) doesn't spam duplicate
            // reviews while this one is still open.
            await setCachedReview(promptHash, { status: 'pending', reviewId: result.review_id });
            return;
        }

        // 'block' falls through here and simply stays stopped —
        // BLOCKING_VERDICTS exists so this behavior is explicit rather than
        // "whatever didn't match the cases above."
        if (!BLOCKING_VERDICTS.has(result.verdict) && result.verdict !== 'mask') {
            // Defensive: an unrecognized verdict should never silently send.
            console.warn('ControlPlane: unrecognized verdict, holding message:', result.verdict);
        } else if (result.verdict === 'mask') {
            // Backend said 'mask' but didn't return redacted content at all.
            // Fail closed — hold the message rather than sending the
            // original unredacted text.
            guardBus.emit({ status: 'error', error: 'Sensitive content was detected but could not be safely redacted. Message held.' });
        }
    }
    catch (error) {
        guardBus.emit({ status: 'error', error: error instanceof Error ? error.message : String(error) });
        // Fail closed: a check that errors out must NOT fall back to
        // sending the original, unchecked prompt.
    }
}

function getAssistantText(node) {
    return (
        node?.innerText?.trim()
        ?? ''
    );
}

// Small, fast, non-cryptographic hash — good enough to key a local cache by
// content, not to defeat an adversary. djb2.
function hashContent(text) {
    let hash = 5381;
    for (let i = 0; i < text.length; i += 1) {
        hash = ((hash << 5) + hash + text.charCodeAt(i)) | 0;
    }
    return String(hash >>> 0);
}

function applyResponseCorrection(
    node,
    content
) {
    if (!content)
        return;

    /*
     * Protect the MutationObserver from treating our own
     * redaction/replacement as a new ChatGPT response.
     */
    correctingResponseNodes.add(node);

    node.innerHTML = '';

    const paragraph =
        document.createElement('p');

    paragraph.dir = 'auto';
    paragraph.textContent = content;

    node.appendChild(paragraph);

    /*
     * MutationObserver callbacks run after the current
     * synchronous DOM mutation. Remove the protection in
     * a microtask after those mutations have been queued.
     */
    queueMicrotask(() => {
        correctingResponseNodes.delete(node);
    });
}

async function evaluateAssistantMessage(node) {
    if (!enabled)
        return;

    /*
     * Prevent concurrent guardrail requests for the same
     * response node.
     */
    if (checkingResponseNodes.has(node))
        return;

    /*
     * A response that has already completed its guardrail
     * check does not need another check unless ChatGPT
     * changes it later.
     */
    if (
        node.dataset.controlplaneChecked === 'true'
    ) {
        return;
    }

    const content = getAssistantText(node);

    if (!content)
        return;

    // Check the persistent cache BEFORE calling the backend at all. This is
    // what actually fixes "refresh re-triggers human review forever": a
    // refresh re-renders every historical message as a brand-new DOM node
    // with no in-memory state, so without this cache every single one would
    // re-run checkOutput from scratch and (previously) create a duplicate
    // review each time.
    const contentHash = hashContent(content);
    const cached = await getCachedReview(contentHash);
    if (cached?.status === 'resolved') {
        applyResponseCorrection(node, cached.finalContent);
        guardBus.emit({ status: 'response-pass' });
        return;
    }
    if (cached?.status === 'pending') {
        // A review is already in flight for this exact content (started
        // before a refresh killed the previous poll, most likely). Resume
        // polling against the same review_id instead of creating another
        // review via a fresh checkOutput call.
        node.style.visibility = 'hidden';
        node.dataset.controlplaneChecked = 'true';
        guardBus.emit({ status: 'checking-response' });
        await waitForReviewResolution(node, cached.reviewId, content, contentHash);
        node.style.visibility = '';
        return;
    }

    checkingResponseNodes.add(node);

    node.dataset.controlplaneChecked =
        'true';

    node.dataset.controlplaneGuarding =
        'true';

    /*
     * Hide the assistant message while the output guardrail
     * is executing so unsafe output is not visibly presented
     * to the user during the check.
     */
    node.style.visibility = 'hidden';

    guardBus.emit({
        status: 'checking-response',
    });

    try {
        const result = await checkOutput(
            lastSentPrompt,
            content,
            currentModel
        );

        guardBus.emit({
            status:
                `response-${result.verdict}`,
            result,
        });

        /*
         * PASS keeps the original response.
         *
         * MASK replaces it with the backend's sanitized
         * response.
         *
         * REVIEW replaces it with the safe review message.
         *
         * BLOCK replaces it with the safe blocked message.
         */
        if (result.verdict !== 'pass') {
            applyResponseCorrection(
                node,
                result.content
            );
        }

        if (result.verdict === 'review' && result.review_id) {
            await setCachedReview(contentHash, { status: 'pending', reviewId: result.review_id });
            await waitForReviewResolution(node, result.review_id, content, contentHash);
        }

        node.style.visibility = '';

    }
    catch (error) {
        /*
         * Fail open visually if the ControlPlane service is
         * temporarily unreachable. The user sees an explicit
         * error state instead of an invisible conversation.
         */
        node.style.visibility = '';

        guardBus.emit({
            status: 'response-error',
            error:
                error instanceof Error
                    ? error.message
                    : String(error),
        });

    }
    finally {
        delete node.dataset.controlplaneGuarding;

        checkingResponseNodes.delete(node);

        /*
         * If ChatGPT changed the response while the check
         * was running, perform another stable check against
         * the final response.
         */
        if (
            node.dataset.controlplaneChecked ===
            'false'
        ) {
            scheduleResponseCheck(node);
        }
    }
}

function scheduleResponseCheck(node) {
    const existingTimer =
        pendingResponseTimers.get(node);

    if (existingTimer) {
        clearTimeout(existingTimer);
    }

    const timer = setTimeout(() => {
        pendingResponseTimers.delete(node);
        void evaluateAssistantMessage(node);
    }, provider.responseStableMs);
    pendingResponseTimers.set(node, timer);
}

function collectAssistantNodes(root) {
    if (!(root instanceof HTMLElement))
        return [];
    const nodes = root.matches(provider.assistantMessageSelector) ? [root] : [];
    return nodes.concat(Array.from(root.querySelectorAll(provider.assistantMessageSelector)));
}

function installResponseObserver() {
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            mutation.addedNodes.forEach((added) => {
                collectAssistantNodes(added).forEach((node) => {
                    // Skip nodes we are actively rewriting ourselves —
                    // otherwise applyResponseCorrection's own DOM write
                    // would re-trigger a check in an endless loop.
                    if (correctingResponseNodes.has(node))
                        return;
                    scheduleResponseCheck(node);
                });
            });
            // Most of these chat UIs stream by mutating text inside the
            // existing message node rather than adding new ones — catch
            // that case too.
            const changedElement = mutation.target instanceof HTMLElement
                ? mutation.target
                : mutation.target.parentElement;
            const assistantAncestor = changedElement?.closest?.(provider.assistantMessageSelector);
            if (assistantAncestor && !correctingResponseNodes.has(assistantAncestor)) {
                assistantAncestor.dataset.controlplaneChecked = 'false';
                scheduleResponseCheck(assistantAncestor);
            }
        }
    });

    observer.observe(
        document.body,
        {
            childList: true,
            subtree: true,
            characterData: true,
        }
    );
}

export function installInterceptor() {
    document.addEventListener('click', (event) => {
        const target = event.target;
        if (!target.closest(provider.sendSelector))
            return;
        void interceptSend(event);
    }, true);
    document.addEventListener('keydown', (event) => {
        const keyboardEvent = event;
        if (keyboardEvent.key !== 'Enter' || keyboardEvent.shiftKey)
            return;
        const target = event.target;
        if (!target.closest(provider.promptSelector))
            return;
        if (!getPrompt())
            return;
        void interceptSend(event);
    }, true);
    getState().then((state) => {
        enabled = state.enabled;
    });

    /*
     * React immediately to popup setting changes.
     */
    onStateChanged((state) => {
        enabled = state.enabled;
    });

    /*
     * Start watching ChatGPT's rendered assistant
     * messages for output guardrail checks.
     */
    installResponseObserver();
}

async function waitForReviewResolution(node, reviewId, originalContent, contentHash) {
    for (let attempt = 0; attempt < 60; attempt += 1) {
        await wait(2000);
        const review = await getReviewStatus(reviewId);
        if (review.resolved) {
            const finalContent = review.final_response || originalContent;
            await setCachedReview(contentHash, { status: 'resolved', finalContent });
            // The page's own SPA may have replaced this exact DOM node
            // during the (up to 2-minute) wait — e.g. a re-render, a scroll
            // recycling a virtualized list item, or the user navigating
            // away and back. Guard against writing into a detached node;
            // the cache write above still ensures the NEXT time this
            // content is evaluated (even against a brand-new node) it
            // resolves instantly rather than re-triggering a review.
            if (node.isConnected) {
                applyResponseCorrection(node, finalContent);
                node.style.visibility = '';
            }
            guardBus.emit({ status: 'response-pass' });
            return;
        }
    }
}