/** Sends a prompt to the background service worker, which owns the API key
 * and talks to the ControlPlane backend. Content scripts never call the
 * backend directly. */
export function checkInput(prompt, model) {
    return new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ type: 'CHECK_INPUT', prompt, model }, (response) => {
            if (chrome.runtime.lastError) {
                reject(new Error(chrome.runtime.lastError.message));
                return;
            }
            if (!response) {
                reject(new Error('No response from ControlPlane service worker.'));
                return;
            }
            if (!response.ok) {
                reject(new Error(response.error || 'ControlPlane request failed.'));
                return;
            }
            resolve(response.data);
        });
    });
}

/** Sends ChatGPT's rendered response (plus the prompt that produced it) to
 * the background service worker for a post-generation guardrail check. */
export function checkOutput(prompt, response, model) {
    return new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ type: 'CHECK_OUTPUT', prompt, response, model }, (result) => {
            if (chrome.runtime.lastError) {
                reject(new Error(chrome.runtime.lastError.message));
                return;
            }
            if (!result) {
                reject(new Error('No response from ControlPlane service worker.'));
                return;
            }
            if (!result.ok) {
                reject(new Error(result.error || 'ControlPlane request failed.'));
                return;
            }
            resolve(result.data);
        });
    });
}

export function getReviewStatus(reviewId) {
    return new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ type: 'GET_REVIEW_STATUS', reviewId }, (result) => {
            if (chrome.runtime.lastError) {
                reject(new Error(chrome.runtime.lastError.message));
                return;
            }
            if (!result?.ok) {
                reject(new Error(result?.error || 'ControlPlane request failed.'));
                return;
            }
            resolve(result.data);
        });
    });
}