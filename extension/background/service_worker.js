const DASHBOARD_URL = chrome.runtime.getURL(
    "dashboard/dashboard.html"
);

const API = "http://127.0.0.1:8000";


// ============================================================
// OPEN DASHBOARD
// ============================================================

chrome.runtime.onMessage.addListener(
    (message, sender, sendResponse) => {

        if (message.type === "OPEN_DASHBOARD") {
            chrome.tabs.create({
                url: DASHBOARD_URL
            });

            return;
        }


        // ====================================================
        // GET EXTENSION STATE
        // ====================================================

        if (message.type === "GET_STATE") {

            chrome.storage.local.get(
                {
                    enabled: true,
                    optimizationEnabled: true,
                    showCost: true,
                    showTokens: true
                },
                state => {

                    if (sender.tab?.id) {

                        chrome.tabs.sendMessage(
                            sender.tab.id,
                            {
                                type: "STATE",
                                state
                            }
                        );
                    }
                }
            );

            return;
        }


        // ====================================================
        // CHECK INPUT THROUGH BACKEND
        // ====================================================

        if (message.type === "CHECK_INPUT") {

            checkInput(message.prompt, message.model)
                .then(result => {

                    sendResponse({
                        ok: true,
                        data: result
                    });

                })
                .catch(error => {

                    console.error(
                        "ControlPlane backend error:",
                        error
                    );

                    sendResponse({
                        ok: false,
                        error: error.message
                    });
                });

            // IMPORTANT:
            // Keep the message channel open for async response.
            return true;
        }
    }
);


// ============================================================
// BACKEND INPUT REQUEST
// ============================================================

async function checkInput(prompt, model) {

    const state = await chrome.storage.local.get({
        apiKey: ""
    });

    const apiKey = state.apiKey?.trim();

    if (!apiKey) {
        throw new Error(
            "ControlPlane API key is not configured."
        );
    }


    const response = await fetch(
        `${API}/guardrails/input`,
        {
            method: "POST",

            headers: {
                "Content-Type": "application/json",
                "X-API-Key": apiKey
            },

            body: JSON.stringify({
                prompt: prompt,
                model: model || "gpt-4o-mini"
            })
        }
    );


    if (!response.ok) {

        const text = await response.text();

        throw new Error(
            `ControlPlane API ${response.status}: ${text}`
        );
    }


    return await response.json();
}