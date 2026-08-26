export const DEFAULT_STATE = {
    enabled: true,
    optimizationEnabled: true,
    showTokens: true,
    apiKey: '',
    principalId: null,
};
export function getState() {
    return new Promise((resolve) => {
        chrome.storage.local.get(DEFAULT_STATE, (items) => resolve(items));
    });
}
export function setState(patch) {
    return new Promise((resolve) => {
        chrome.storage.local.set(patch, () => resolve());
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
