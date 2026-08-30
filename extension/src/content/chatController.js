import { checkInput, checkOutput } from '../lib/api';
import { getState, onStateChanged } from '../lib/storage';
import { guardBus } from './guardBus.js';
const PROMPT_SELECTOR = '#prompt-textarea';
const SEND_SELECTOR = '#composer-submit-button';
// ChatGPT tags each conversation turn with this attribute — more stable
// than styling classes, but still page markup we don't control, so this
// may need updating if OpenAI changes it.
const ASSISTANT_MESSAGE_SELECTOR = '[data-message-author-role="assistant"]';
// How long an assistant message's text must stop changing before we treat
// it as "finished streaming" and send it for a guardrail check.
const RESPONSE_STABLE_MS = 1200;
let enabled = true;
let bypassNextSend = false;
let currentModel = 'gpt-4o-mini';
// The prompt actually sent (after any masking/optimization), so the output
// check has the right grounding context.
let lastSentPrompt = '';
const pendingResponseTimers = new WeakMap();
function getPromptElement() {
    return document.querySelector(PROMPT_SELECTOR);
}
export function getPrompt() {
    return getPromptElement()?.innerText.trim() ?? '';
}
export function setPrompt(text) {
    const element = getPromptElement();
    if (!element)
        return false;
    element.focus();
    element.innerHTML = '';
    const paragraph = document.createElement('p');
    paragraph.dir = 'auto';
    paragraph.textContent = text;
    element.appendChild(paragraph);
    element.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: text }));
    return true;
}
function getSendButton() {
    return document.querySelector(SEND_SELECTOR);
}
export function sendNow() {
    const sendButton = getSendButton();
    if (!sendButton)
        return false;
    lastSentPrompt = getPrompt();
    bypassNextSend = true;
    sendButton.click();
    return true;
}
async function interceptSend(event) {
    if (!enabled || bypassNextSend) {
        bypassNextSend = false;
        return;
    }
    const prompt = getPrompt();
    if (!prompt)
        return;
    event.preventDefault();
    event.stopPropagation();
    if ('stopImmediatePropagation' in event)
        event.stopImmediatePropagation();
    guardBus.emit({ status: 'checking' });
    try {
        const result = await checkInput(prompt, currentModel);
        guardBus.emit({ status: result.verdict, result });
    }
    catch (error) {
        guardBus.emit({ status: 'error', error: error instanceof Error ? error.message : String(error) });
    }
}
function getAssistantText(node) {
    return node?.innerText?.trim() ?? '';
}
function applyResponseCorrection(node, content) {
    node.innerHTML = '';
    const paragraph = document.createElement('p');
    paragraph.dir = 'auto';
    paragraph.textContent = content;
    node.appendChild(paragraph);
}
async function evaluateAssistantMessage(node) {
    if (!enabled)
        return;
    if (node.dataset.controlplaneChecked === 'true')
        return;
    const content = getAssistantText(node);
    if (!content)
        return;
    // Mark before awaiting so a second mutation firing mid-check doesn't
    // schedule a duplicate evaluation of the same message.
    node.dataset.controlplaneChecked = 'true';
    guardBus.emit({ status: 'checking-response' });
    try {
        const result = await checkOutput(lastSentPrompt, content, currentModel);
        guardBus.emit({ status: `response-${result.verdict}`, result });
        if (result.verdict === 'block' || result.verdict === 'mask') {
            applyResponseCorrection(node, result.content);
        }
    }
    catch (error) {
        guardBus.emit({ status: 'response-error', error: error instanceof Error ? error.message : String(error) });
    }
}
function scheduleResponseCheck(node) {
    const existingTimer = pendingResponseTimers.get(node);
    if (existingTimer)
        clearTimeout(existingTimer);
    const timer = setTimeout(() => {
        pendingResponseTimers.delete(node);
        void evaluateAssistantMessage(node);
    }, RESPONSE_STABLE_MS);
    pendingResponseTimers.set(node, timer);
}
function collectAssistantNodes(root) {
    if (!(root instanceof HTMLElement))
        return [];
    const nodes = root.matches(ASSISTANT_MESSAGE_SELECTOR) ? [root] : [];
    return nodes.concat(Array.from(root.querySelectorAll(ASSISTANT_MESSAGE_SELECTOR)));
}
function installResponseObserver() {
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            mutation.addedNodes.forEach((added) => {
                collectAssistantNodes(added).forEach(scheduleResponseCheck);
            });
            // ChatGPT streams by mutating text inside the existing message
            // node rather than adding new ones — catch that case too.
            const changedElement = mutation.target instanceof HTMLElement
                ? mutation.target
                : mutation.target.parentElement;
            const assistantAncestor = changedElement?.closest?.(ASSISTANT_MESSAGE_SELECTOR);
            if (assistantAncestor) {
                assistantAncestor.dataset.controlplaneChecked = 'false';
                scheduleResponseCheck(assistantAncestor);
            }
        }
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
}
export function installInterceptor() {
    document.addEventListener('click', (event) => {
        const target = event.target;
        if (!target.closest(SEND_SELECTOR))
            return;
        void interceptSend(event);
    }, true);
    document.addEventListener('keydown', (event) => {
        const keyboardEvent = event;
        if (keyboardEvent.key !== 'Enter' || keyboardEvent.shiftKey)
            return;
        const target = event.target;
        if (!target.closest(PROMPT_SELECTOR))
            return;
        if (!getPrompt())
            return;
        void interceptSend(event);
    }, true);
    getState().then((state) => {
        enabled = state.enabled;
    });
    onStateChanged((state) => {
        enabled = state.enabled;
    });
    installResponseObserver();
}