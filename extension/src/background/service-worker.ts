/// <reference types="chrome" />

// The web dashboard's URL — where "Open dashboard" and connect-flow point to.
// Swap to your deployed frontend origin in production.
const DASHBOARD_URL = 'http://localhost:5173'
const API = 'http://127.0.0.1:8000'

interface CheckInputMessage {
    type: 'CHECK_INPUT'
    prompt: string
    model?: string
}

interface OpenDashboardMessage {
    type: 'OPEN_DASHBOARD'
}

interface GetStateMessage {
    type: 'GET_STATE'
}

type InboundMessage = CheckInputMessage | OpenDashboardMessage | GetStateMessage

// ============================================================
// EXTERNAL MESSAGES — dashboard "Connect extension" button
// ============================================================
// Only origins listed under "externally_connectable" in manifest.config.ts
// may call this.

chrome.runtime.onMessageExternal.addListener((message, _sender, sendResponse) => {
    if (message?.type === 'SET_API_KEY') {
        const apiKey = typeof message.apiKey === 'string' ? message.apiKey.trim() : ''
        if (!apiKey) {
            sendResponse({ ok: false, error: 'Missing apiKey.' })
            return
        }
        chrome.storage.local.set(
            { apiKey, principalId: message.principalId ?? null, enabled: true },
            () => sendResponse({ ok: true }),
        )
        return true // keep the channel open for the async storage callback
    }
})

// ============================================================
// INTERNAL MESSAGES — popup + content script
// ============================================================

chrome.runtime.onMessage.addListener((message: InboundMessage, sender, sendResponse) => {
    if (message.type === 'OPEN_DASHBOARD') {
        chrome.tabs.create({ url: DASHBOARD_URL })
        return
    }

    if (message.type === 'GET_STATE') {
        chrome.storage.local.get(
            { enabled: true, optimizationEnabled: true, showTokens: true },
            (state) => {
                if (sender.tab?.id) {
                    chrome.tabs.sendMessage(sender.tab.id, { type: 'STATE', state })
                }
            },
        )
        return
    }

    if (message.type === 'CHECK_INPUT') {
        checkInput(message.prompt, message.model || 'gpt-4o-mini')
            .then((data) => sendResponse({ ok: true, data }))
            .catch((error: Error) => {
                console.error('ControlPlane backend error:', error)
                sendResponse({ ok: false, error: error.message })
            })
        return true // keep the channel open for the async fetch
    }
})

async function checkInput(prompt: string, model: string) {
    const state = await chrome.storage.local.get({ apiKey: '' })
    const apiKey = (state.apiKey as string)?.trim()

    if (!apiKey) {
        throw new Error('ControlPlane API key is not configured. Connect the extension from the dashboard.')
    }

    const response = await fetch(`${API}/guardrails/input`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({ prompt, model }),
    })

    if (!response.ok) {
        const text = await response.text()
        throw new Error(`ControlPlane API ${response.status}: ${text}`)
    }

    return await response.json()
}
