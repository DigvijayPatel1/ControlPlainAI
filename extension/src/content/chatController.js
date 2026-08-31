import { checkInput, checkOutput } from '../lib/api';
import { getState, onStateChanged } from '../lib/storage';
import { guardBus } from './guardBus.js';

const PROMPT_SELECTOR = '#prompt-textarea';
const SEND_SELECTOR = '#composer-submit-button';

const ASSISTANT_MESSAGE_SELECTOR =
    '[data-message-author-role="assistant"]';

const RESPONSE_STABLE_MS = 1200;

let enabled = true;
let bypassNextSend = false;
let currentModel = 'gpt-4o-mini';
let lastSentPrompt = '';

const pendingResponseTimers = new WeakMap();
const checkingResponseNodes = new WeakSet();
const correctingResponseNodes = new WeakSet();

function getPromptElement() {
    return document.querySelector(
        PROMPT_SELECTOR
    );
}

export function getPrompt() {
    return (
        getPromptElement()
            ?.innerText
            .trim()
        ?? ''
    );
}

export function setPrompt(text) {
    const element = getPromptElement();

    if (!element)
        return false;

    element.focus();
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
    return document.querySelector(
        SEND_SELECTOR
    );
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
        const result = await checkInput(
            prompt,
            currentModel
        );

        guardBus.emit({
            status: result.verdict,
            result,
        });
    }
    catch (error) {
        guardBus.emit({
            status: 'error',
            error:
                error instanceof Error
                    ? error.message
                    : String(error),
        });
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

        void evaluateAssistantMessage(
            node
        );
    }, RESPONSE_STABLE_MS);

    pendingResponseTimers.set(
        node,
        timer
    );
}

function collectAssistantNodes(root) {
    if (!(root instanceof HTMLElement))
        return [];

    const nodes =
        root.matches(
            ASSISTANT_MESSAGE_SELECTOR
        )
            ? [root]
            : [];

    return nodes.concat(
        Array.from(
            root.querySelectorAll(
                ASSISTANT_MESSAGE_SELECTOR
            )
        )
    );
}

function installResponseObserver() {
    const observer =
        new MutationObserver(
            (mutations) => {
                for (const mutation of mutations) {

                    /*
                     * Detect newly-added assistant messages.
                     */
                    mutation.addedNodes.forEach(
                        (added) => {
                            collectAssistantNodes(
                                added
                            ).forEach(
                                scheduleResponseCheck
                            );
                        }
                    );

                    /*
                     * ChatGPT commonly streams by modifying
                     * text inside an existing assistant node.
                     */
                    const changedElement =
                        mutation.target instanceof
                        HTMLElement
                            ? mutation.target
                            : mutation.target
                                  .parentElement;

                    const assistantAncestor =
                        changedElement?.closest?.(
                            ASSISTANT_MESSAGE_SELECTOR
                        );

                    if (!assistantAncestor)
                        continue;

                    /*
                     * Ignore DOM changes produced by our own
                     * response replacement.
                     */
                    if (
                        correctingResponseNodes.has(
                            assistantAncestor
                        )
                    ) {
                        continue;
                    }

                    /*
                     * Mark it dirty and wait for the text to
                     * become stable before checking.
                     */
                    assistantAncestor.dataset.controlplaneChecked =
                        'false';

                    scheduleResponseCheck(
                        assistantAncestor
                    );
                }
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
    /*
     * Mouse/click send interception.
     */
    document.addEventListener(
        'click',
        (event) => {
            const target =
                event.target;

            if (
                !target?.closest?.(
                    SEND_SELECTOR
                )
            ) {
                return;
            }

            void interceptSend(event);
        },
        true
    );

    /*
     * Enter-key send interception.
     */
    document.addEventListener(
        'keydown',
        (event) => {
            const keyboardEvent = event;

            if (
                keyboardEvent.key !== 'Enter'
                || keyboardEvent.shiftKey
            ) {
                return;
            }

            const target =
                event.target;

            if (
                !target?.closest?.(
                    PROMPT_SELECTOR
                )
            ) {
                return;
            }

            if (!getPrompt())
                return;

            void interceptSend(event);
        },
        true
    );

    /*
     * Load the current extension protection state.
     */
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

