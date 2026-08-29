export const DEFAULT_STATE = {
    enabled: true,
    optimizationEnabled: true,
    showTokens: true,
    apiKey: '',
    principalId: null,
};

function sanitizeState(items = {}) {
    const next = {
        ...DEFAULT_STATE,
        ...items,
    };

    delete next.openaiApiKey;

    return {
        enabled: Boolean(next.enabled),
        optimizationEnabled: Boolean(next.optimizationEnabled),
        showTokens: Boolean(next.showTokens),
        apiKey: typeof next.apiKey === 'string' ? next.apiKey.trim() : '',
        principalId: next.principalId ?? null,
    };
}

export function getState() {
    return new Promise((resolve) => {
        chrome.storage.local.get(DEFAULT_STATE, (items) => {
            const cleanState = sanitizeState(items);
            const hasLegacyOpenAiKey = Object.prototype.hasOwnProperty.call(items, 'openaiApiKey');

            if (hasLegacyOpenAiKey || JSON.stringify(cleanState) !== JSON.stringify(items)) {
                chrome.storage.local.set(cleanState, () => resolve(cleanState));
                return;
            }

            resolve(cleanState);
        });
    });
}

export function setState(patch) {
    return new Promise((resolve) => {
        const safePatch = sanitizeState(patch);
        chrome.storage.local.set(safePatch, () => resolve());
    });
}
export function onStateChanged(callback) {
    const listener = (_changes, area) => {
        if (area !== 'local')
            return;
        getState().then(callback);
    };
    chrome.storage.onChanged.addListener(listener);
    return () => chrome.storage.onChanged.removeListener(listener);
}
