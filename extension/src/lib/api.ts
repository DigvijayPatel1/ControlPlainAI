export type Verdict = 'pass' | 'mask' | 'review' | 'block'

export interface GuardrailCheckResult {
    verdict: Verdict
    reasons?: string[]
    content?: string
    optimized_content?: string
    original_tokens: number
    optimized_tokens?: number
    tokens_saved: number
    estimated_cost_usd: number
    savings_usd: number
}

/** Sends a prompt to the background service worker, which owns the API key
 * and talks to the ControlPlane backend. Content scripts never call the
 * backend directly. */
export function checkInput(prompt: string, model: string): Promise<GuardrailCheckResult> {
    return new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ type: 'CHECK_INPUT', prompt, model }, (response) => {
            if (chrome.runtime.lastError) {
                reject(new Error(chrome.runtime.lastError.message))
                return
            }
            if (!response) {
                reject(new Error('No response from ControlPlane service worker.'))
                return
            }
            if (!response.ok) {
                reject(new Error(response.error || 'ControlPlane request failed.'))
                return
            }
            resolve(response.data as GuardrailCheckResult)
        })
    })
}
