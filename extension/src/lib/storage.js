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

// ---------------------------------------------------------------------
// Review cache — tracks the status of output-guardrail reviews by a hash
// of the response content, so it survives a page refresh (which kills any
// in-memory polling loop outright) and so a refresh re-scanning the same
// historical message doesn't spam duplicate checks against the backend
// while a review is still pending. Entries expire after 24h so this never
// grows unbounded across a long browsing session.
// ---------------------------------------------------------------------
const REVIEW_CACHE_KEY = 'reviewCache';
const REVIEW_CACHE_TTL_MS = 24 * 60 * 60 * 1000;

function readReviewCache() {
    return new Promise((resolve) => {
        chrome.storage.local.get({ [REVIEW_CACHE_KEY]: {} }, (items) => {
            resolve(items[REVIEW_CACHE_KEY] || {});
        });
    });
}

function writeReviewCache(cache) {
    return new Promise((resolve) => {
        chrome.storage.local.set({ [REVIEW_CACHE_KEY]: cache }, resolve);
    });
}

function pruneExpiredReviews(cache) {
    const now = Date.now();
    const next = {};
    for (const [hash, entry] of Object.entries(cache)) {
        if (now - (entry.updatedAt || 0) < REVIEW_CACHE_TTL_MS) {
            next[hash] = entry;
        }
    }
    return next;
}

/** Returns { status: 'pending' | 'resolved', reviewId, finalContent } or null. */
export async function getCachedReview(contentHash) {
    const cache = await readReviewCache();
    return cache[contentHash] ?? null;
}

export async function setCachedReview(contentHash, entry) {
    const cache = pruneExpiredReviews(await readReviewCache());
    cache[contentHash] = { ...entry, updatedAt: Date.now() };
    await writeReviewCache(cache);
}