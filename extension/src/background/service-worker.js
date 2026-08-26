"use strict";
/// <reference types="chrome" />
// The web dashboard's URL — where "Open dashboard" and connect-flow point to.
// Swap to your deployed frontend origin in production.
const DASHBOARD_URL = 'http://localhost:5173';
const API = 'http://127.0.0.1:8000';
// ============================================================
// EXTERNAL MESSAGES — dashboard "Connect extension" button
// ============================================================
// Only origins listed under "externally_connectable" in the manifest configuration.
// may call this.
chrome.runtime.onMessageExternal.addListener((message, _sender, sendResponse) => {
    if (message?.type === 'SET_API_KEY') {
        const apiKey = typeof message.apiKey === 'string' ? message.apiKey.trim() : '';
        if (!apiKey) {
            sendResponse({ ok: false, error: 'Missing apiKey.' });
            return;
        }
        chrome.storage.local.set({ apiKey, principalId: message.principalId ?? null, enabled: true }, () => sendResponse({ ok: true }));
        return true; // keep the channel open for the async storage callback
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
