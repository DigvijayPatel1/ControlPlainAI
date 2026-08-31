"use strict";
/// <reference types="chrome" />
// The web dashboard's URL — where "Open dashboard" and connect-flow point to.
// Swap to your deployed frontend origin in production.
const DASHBOARD_URL = 'http://localhost:5173';
const API = 'http://127.0.0.1:8000';
const MONITORED_SITES_KEY = 'monitoredSites';
// A stable, discoverable id prefix so registered scripts from a previous
// session can be found and removed by origin without tracking extra state.
const DYNAMIC_SCRIPT_ID_PREFIX = 'controlplane-dynamic-';

// ============================================================
// EXTERNAL MESSAGES — dashboard "Connect extension" button and
// "Add monitored site" flow
// ============================================================
// Only origins listed under "externally_connectable" in the manifest
// configuration may call this.
chrome.runtime.onMessageExternal.addListener((message, _sender, sendResponse) => {
    if (message?.type === 'SET_API_KEY') {
        const apiKey = typeof message.apiKey === 'string' ? message.apiKey.trim() : '';
        if (!apiKey) {
            sendResponse({ ok: false, error: 'Missing apiKey.' });
            return;
        }

        chrome.storage.local.remove('openaiApiKey', () => {
            chrome.storage.local.set({ apiKey, principalId: message.principalId ?? null, enabled: true }, () => sendResponse({ ok: true }));
        });
        return true; // keep the channel open for the async storage callback
    }
    if (message?.type === 'ADD_MONITORED_SITE') {
        addMonitoredSite(message.url)
            .then((site) => sendResponse({ ok: true, site }))
            .catch((error) => sendResponse({ ok: false, error: error.message }));
        return true;
    }
    if (message?.type === 'REMOVE_MONITORED_SITE') {
        removeMonitoredSite(message.origin)
            .then(() => sendResponse({ ok: true }))
            .catch((error) => sendResponse({ ok: false, error: error.message }));
        return true;
    }
    if (message?.type === 'LIST_MONITORED_SITES') {
        listMonitoredSites()
            .then((sites) => sendResponse({ ok: true, sites }))
            .catch((error) => sendResponse({ ok: false, error: error.message }));
        return true;
    }
});
// ============================================================
// INTERNAL MESSAGES — popup + content script
// ============================================================
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'OPEN_DASHBOARD') {
        chrome.tabs.create({ url: DASHBOARD_URL });
        return;
    }
    if (message.type === 'GET_STATE') {
        chrome.storage.local.get({ enabled: true, optimizationEnabled: true, showTokens: true }, (state) => {
            if (sender.tab?.id) {
                chrome.tabs.sendMessage(sender.tab.id, { type: 'STATE', state });
            }
        });
        return;
    }
    if (message.type === 'CHECK_INPUT') {
        checkInput(message.prompt, message.model || 'gpt-4o-mini')
            .then((data) => sendResponse({ ok: true, data }))
            .catch((error) => {
            console.error('ControlPlane backend error:', error);
            sendResponse({ ok: false, error: error.message });
        });
        return true; // keep the channel open for the async fetch
    }
    if (message.type === 'CHECK_OUTPUT') {
        checkOutput(message.prompt, message.response, message.model || 'gpt-4o-mini')
            .then((data) => sendResponse({ ok: true, data }))
            .catch((error) => {
            console.error('ControlPlane backend error:', error);
            sendResponse({ ok: false, error: error.message });
        });
        return true; // keep the channel open for the async fetch
    }
    if (message.type === 'GET_REVIEW_STATUS') {
        getReviewStatus(message.reviewId)
            .then((data) => sendResponse({ ok: true, data }))
            .catch((error) => sendResponse({ ok: false, error: error.message }));
        return true;
    }
});
async function checkInput(prompt, model) {
    const state = await chrome.storage.local.get({ apiKey: '' });
    const apiKey = state.apiKey?.trim();
    if (!apiKey) {
        throw new Error('ControlPlane API key is not configured. Connect the extension from the dashboard.');
    }
    const response = await fetch(`${API}/guardrails/input`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({ prompt, model }),
    });
    if (!response.ok) {
        const text = await response.text();
        throw new Error(`ControlPlane API ${response.status}: ${text}`);
    }
    return await response.json();
}
async function checkOutput(prompt, response, model) {
    const state = await chrome.storage.local.get({ apiKey: '' });
    const apiKey = state.apiKey?.trim();
    if (!apiKey) {
        throw new Error('ControlPlane API key is not configured. Connect the extension from the dashboard.');
    }
    const res = await fetch(`${API}/guardrails/output`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({ prompt, response, model }),
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`ControlPlane API ${res.status}: ${text}`);
    }
    return await res.json();
}

// ============================================================
// DYNAMIC SITE REGISTRATION — lets the dashboard's "paste a URL"
// flow work for sites not baked into manifest.json at build time.
//
// Chrome (Manifest V3) can't append to the static content_scripts
// list at runtime, so an arbitrary URL is handled differently from
// the three built-in providers (ChatGPT/Claude/Gemini): we request
// a one-off host permission for that exact origin, then register a
// content script for it with chrome.scripting.registerContentScripts.
// It uses the same content-main.js bundle — providers.js falls back
// to a generic, unverified selector heuristic for unknown hostnames.
// ============================================================

function scriptIdFor(origin) {
    return `${DYNAMIC_SCRIPT_ID_PREFIX}${origin}`;
}

async function addMonitoredSite(rawUrl) {
    let url;
    try {
        url = new URL(rawUrl);
    } catch {
        throw new Error('That doesn\'t look like a valid URL.');
    }
    if (url.protocol !== 'https:') {
        throw new Error('Only https:// URLs are supported.');
    }
    const origin = url.origin;
    const matchPattern = `${origin}/*`;

    const granted = await chrome.permissions.request({ origins: [matchPattern] });
    if (!granted) {
        throw new Error('Permission was not granted for that site.');
    }

    const existing = await chrome.scripting.getRegisteredContentScripts({ ids: [scriptIdFor(origin)] });
    if (existing.length === 0) {
        await chrome.scripting.registerContentScripts([
            {
                id: scriptIdFor(origin),
                js: ['content-main.js'],
                matches: [matchPattern],
                runAt: 'document_idle',
            },
        ]);
    }

    const site = { origin, hostname: url.hostname, addedAt: Date.now() };
    const { [MONITORED_SITES_KEY]: sites = [] } = await chrome.storage.local.get(MONITORED_SITES_KEY);
    const next = [...sites.filter((s) => s.origin !== origin), site];
    await chrome.storage.local.set({ [MONITORED_SITES_KEY]: next });
    return site;
}

async function removeMonitoredSite(origin) {
    await chrome.scripting.unregisterContentScripts({ ids: [scriptIdFor(origin)] }).catch(() => {
        // Not registered — nothing to remove, not an error.
    });
    await chrome.permissions.remove({ origins: [`${origin}/*`] }).catch(() => {});
    const { [MONITORED_SITES_KEY]: sites = [] } = await chrome.storage.local.get(MONITORED_SITES_KEY);
    await chrome.storage.local.set({ [MONITORED_SITES_KEY]: sites.filter((s) => s.origin !== origin) });
}

async function listMonitoredSites() {
    const { [MONITORED_SITES_KEY]: sites = [] } = await chrome.storage.local.get(MONITORED_SITES_KEY);
    return sites;
}

async function getReviewStatus(reviewId) {
    const state = await chrome.storage.local.get({ apiKey: '' });
    const apiKey = state.apiKey?.trim();
    if (!apiKey) {
        throw new Error('ControlPlane API key is not configured.');
    }
    const response = await fetch(`${API}/guardrails/reviews/${reviewId}`, {
        headers: { 'X-API-Key': apiKey },
    });
    if (!response.ok) {
        throw new Error(`ControlPlane API ${response.status}: ${await response.text()}`);
    }
    return response.json();
}