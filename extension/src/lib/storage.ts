export interface ExtensionState {
    enabled: boolean
    optimizationEnabled: boolean
    showTokens: boolean
    apiKey: string
    principalId: string | null
}

export const DEFAULT_STATE: ExtensionState = {
    enabled: true,
    optimizationEnabled: true,
    showTokens: true,
    apiKey: '',
    principalId: null,
}

export function getState(): Promise<ExtensionState> {
    return new Promise((resolve) => {
        chrome.storage.local.get(DEFAULT_STATE, (items) => resolve(items as ExtensionState))
    })
}

export function setState(patch: Partial<ExtensionState>): Promise<void> {
    return new Promise((resolve) => {
        chrome.storage.local.set(patch, () => resolve())
    })
}

export function onStateChanged(callback: (state: ExtensionState) => void): () => void {
    const listener = (_changes: { [key: string]: chrome.storage.StorageChange }, area: string) => {
        if (area !== 'local') return
        getState().then(callback)
    }
    chrome.storage.onChanged.addListener(listener)
    return () => chrome.storage.onChanged.removeListener(listener)
}
