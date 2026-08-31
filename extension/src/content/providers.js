/**
 * Per-site DOM selectors. Each supported AI chat product structures its
 * page differently, so the guard needs to know, per hostname, where the
 * prompt box, send button, and assistant messages live.
 *
 * Adding a new *known* provider: add an entry here, add its host to
 * manifest.json's `content_scripts.matches` and `host_permissions`, and
 * ship a new extension build.
 *
 * Adding an *arbitrary* URL from the dashboard (no code change, no rebuild):
 * the background service worker registers a dynamic content script for
 * that origin (see background/service-worker.js), and this file's
 * GENERIC_FALLBACK is used since we have no verified selectors for an
 * unknown site. The fallback is a best-effort heuristic and will be less
 * reliable than a maintained provider entry — surfaced to the user in the
 * dashboard when they add a custom URL.
 */

const PROVIDERS = {
    'chatgpt.com': {
        promptSelector: '#prompt-textarea',
        sendSelector: '#composer-submit-button',
        assistantMessageSelector: '[data-message-author-role="assistant"]',
        responseStableMs: 1200,
    },
    'chat.openai.com': {
        promptSelector: '#prompt-textarea',
        sendSelector: '#composer-submit-button',
        assistantMessageSelector: '[data-message-author-role="assistant"]',
        responseStableMs: 1200,
    },
    'claude.ai': {
        // Claude's composer is a contenteditable div, not a textarea, and
        // the send button is identified by its aria-label rather than an id.
        promptSelector: 'div[contenteditable="true"][enterkeyhint="enter"], div.ProseMirror[contenteditable="true"]',
        sendSelector: 'button[aria-label="Send message"]',
        assistantMessageSelector: '[data-testid="assistant-turn"], [data-is-streaming]',
        responseStableMs: 1400,
    },
    'gemini.google.com': {
        promptSelector: 'rich-textarea .ql-editor, div[contenteditable="true"][aria-label*="Prompt"]',
        sendSelector: 'button[aria-label="Send message"], button[aria-label*="Submit"]',
        assistantMessageSelector: 'message-content, .model-response-text',
        responseStableMs: 1400,
    },
};

// Used only for sites added via a pasted custom URL with no dedicated entry
// above. Heuristic and unverified — the dashboard should tell the user this
// is best-effort when they add a site that isn't one of the known three.
const GENERIC_FALLBACK = {
    promptSelector: 'textarea, div[contenteditable="true"]',
    sendSelector: 'button[type="submit"], button[aria-label*="Send" i], button[aria-label*="Submit" i]',
    assistantMessageSelector: '[class*="assistant" i], [data-role="assistant"], [data-message-author-role="assistant"]',
    responseStableMs: 1500,
};

export function getProvider(hostname) {
    return PROVIDERS[hostname] ?? GENERIC_FALLBACK;
}

export function isKnownProvider(hostname) {
    return hostname in PROVIDERS;
}

export function listKnownProviders() {
    return Object.keys(PROVIDERS);
}