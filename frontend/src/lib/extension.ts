export const EXTENSION_ID: string = import.meta.env.VITE_EXTENSION_ID ?? ''

interface MinimalChromeRuntime {
    sendMessage: (
        extensionId: string,
        message: unknown,
        responseCallback?: (response: unknown) => void,
    ) => void
    lastError?: { message?: string }
}

declare global {
    interface Window {
        chrome?: { runtime?: MinimalChromeRuntime }
    }
}

export type ConnectResult =
    | { ok: true }
    | { ok: false; reason: 'no-extension-id' | 'no-runtime' | 'no-response' | string }

/**
 * Pushes a freshly-issued API key straight into the extension's local
 * storage via chrome.runtime.sendMessage's "external message" channel, so
 * the user never has to copy/paste the key into the popup by hand.
 *
 * Requires the extension's manifest.json to list this site's origin under
 * "externally_connectable", and a matching onMessageExternal handler in the
 * background service worker (see extension/background/service_worker.js).
 */
export function connectExtension(apiKey: string, principalId: string): Promise<ConnectResult> {
    return new Promise((resolve) => {
        if (!EXTENSION_ID) {
            resolve({ ok: false, reason: 'no-extension-id' })
            return
        }
        const runtime = window.chrome?.runtime
        if (!runtime?.sendMessage) {
            resolve({ ok: false, reason: 'no-runtime' })
            return
        }
        try {
            runtime.sendMessage(
                EXTENSION_ID,
                { type: 'SET_API_KEY', apiKey, principalId },
                (response: unknown) => {
                    const ok = (response as { ok?: boolean } | undefined)?.ok
                    if (runtime.lastError || !ok) {
                        resolve({ ok: false, reason: runtime.lastError?.message ?? 'no-response' })
                        return
                    }
                    resolve({ ok: true })
                },
            )
        } catch (error) {
            resolve({ ok: false, reason: error instanceof Error ? error.message : 'unknown-error' })
        }
    })
}

export const isExtensionConfigured = (): boolean => Boolean(EXTENSION_ID) && Boolean(window.chrome?.runtime)
