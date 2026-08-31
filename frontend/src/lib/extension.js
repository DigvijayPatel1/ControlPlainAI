export const EXTENSION_ID = import.meta.env.VITE_EXTENSION_ID ?? '';
/**
 * Pushes a freshly-issued API key straight into the extension's local
 * storage via chrome.runtime.sendMessage's "external message" channel, so
 * the user never has to copy/paste the key into the popup by hand.
 *
 * Requires the extension's manifest.json to list this site's origin under
 * "externally_connectable", and a matching onMessageExternal handler in the
 * background service worker (see extension/background/service_worker.js).
 */
export function connectExtension(apiKey, principalId) {
    return new Promise((resolve) => {
        if (!EXTENSION_ID) {
            resolve({ ok: false, reason: 'no-extension-id' });
            return;
        }
        const runtime = window.chrome?.runtime;
        if (!runtime?.sendMessage) {
            resolve({ ok: false, reason: 'no-runtime' });
            return;
        }
        try {
            runtime.sendMessage(EXTENSION_ID, { type: 'SET_API_KEY', apiKey, principalId }, (response) => {
                const ok = response?.ok;
                if (runtime.lastError || !ok) {
                    resolve({ ok: false, reason: runtime.lastError?.message ?? 'no-response' });
                    return;
                }
                resolve({ ok: true });
            });
        }
        catch (error) {
            resolve({ ok: false, reason: error instanceof Error ? error.message : 'unknown-error' });
        }
    });
}
export const isExtensionConfigured = () => Boolean(EXTENSION_ID) && Boolean(window.chrome?.runtime);

/**
 * Registers a chat site (ChatGPT, Claude, Gemini, or any https:// URL) for
 * the extension to guard. For the three built-in providers this just
 * confirms the site is already covered by the extension's static manifest.
 * For anything else, the extension requests permission for that origin and
 * dynamically registers a content script for it — see
 * background/service-worker.js's addMonitoredSite.
 */
export function addMonitoredSite(url) {
    return new Promise((resolve) => {
        if (!EXTENSION_ID) {
            resolve({ ok: false, reason: 'no-extension-id' });
            return;
        }
        const runtime = window.chrome?.runtime;
        if (!runtime?.sendMessage) {
            resolve({ ok: false, reason: 'no-runtime' });
            return;
        }
        try {
            runtime.sendMessage(EXTENSION_ID, { type: 'ADD_MONITORED_SITE', url }, (response) => {
                if (runtime.lastError || !response?.ok) {
                    resolve({ ok: false, reason: runtime.lastError?.message ?? response?.error ?? 'no-response' });
                    return;
                }
                resolve({ ok: true, site: response.site });
            });
        }
        catch (error) {
            resolve({ ok: false, reason: error instanceof Error ? error.message : 'unknown-error' });
        }
    });
}

export function listMonitoredSites() {
    return new Promise((resolve) => {
        if (!EXTENSION_ID || !window.chrome?.runtime?.sendMessage) {
            resolve([]);
            return;
        }
        window.chrome.runtime.sendMessage(EXTENSION_ID, { type: 'LIST_MONITORED_SITES' }, (response) => {
            resolve(response?.ok ? response.sites : []);
        });
    });
}

export function removeMonitoredSite(origin) {
    return new Promise((resolve) => {
        if (!EXTENSION_ID || !window.chrome?.runtime?.sendMessage) {
            resolve({ ok: false });
            return;
        }
        window.chrome.runtime.sendMessage(EXTENSION_ID, { type: 'REMOVE_MONITORED_SITE', origin }, (response) => {
            resolve(response ?? { ok: false });
        });
    });
}

// The three providers already baked into the extension's manifest at build
// time — no permission prompt needed for these, they just work out of the box.
export const BUILT_IN_PROVIDERS = [
    { label: 'ChatGPT', origin: 'https://chatgpt.com' },
    { label: 'Claude', origin: 'https://claude.ai' },
    { label: 'Gemini', origin: 'https://gemini.google.com' },
];