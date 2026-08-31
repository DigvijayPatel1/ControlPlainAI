import { checkInput, checkOutput } from '../lib/api';
import { getState, onStateChanged } from '../lib/storage';
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

    guardBus.emit({
        status: 'checking',
    });

    try {
        const result = await checkInput(prompt, currentModel);
        guardBus.emit({ status: result.verdict, result });

        if (result.verdict === 'pass') {
            // Clean content, unmodified — behave like a normal chat client
            // and send it immediately.
            sendNow();
            return;
        }

        if (result.verdict === 'mask' && result.optimized_content) {
            setPrompt(result.optimized_content);
            // Give the page's own editor a moment to process the change,
            // then verify it actually took — do NOT trust the write blindly.
            await wait(120);
            const verifiedPrompt = getPrompt();
            const redactionDidNotStick = verifiedPrompt === prompt || verifiedPrompt !== result.optimized_content;

            if (redactionDidNotStick) {
                // This is the failure mode that let an unredacted email
                // through: our write didn't reach the page's real editor
                // state. Hard stop — never send on unverified content.
                guardBus.emit({
                    status: 'error',
                    error: "Sensitive info was detected, but this page wouldn't let ControlPlane safely replace it in the message box. Nothing was sent — please remove the sensitive info yourself and send again.",
                });
                return;
            }
            sendNow();
            return;
        }

        // 'block' and 'review' fall through here and simply stay stopped —
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
                collectAssistantNodes(added).forEach(scheduleResponseCheck);
            });
            // Most of these chat UIs stream by mutating text inside the
            // existing message node rather than adding new ones — catch
            // that case too.
            const changedElement = mutation.target instanceof HTMLElement
                ? mutation.target
                : mutation.target.parentElement;
            const assistantAncestor = changedElement?.closest?.(provider.assistantMessageSelector);
            if (assistantAncestor) {
                assistantAncestor.dataset.controlplaneChecked = 'false';
                scheduleResponseCheck(assistantAncestor);
            }
        );

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

