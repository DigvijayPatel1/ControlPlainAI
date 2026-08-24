const BUTTON_ID = "controlplane-ai-button";
const MODAL_ID = "controlplane-approval-modal";
const API = "http://127.0.0.1:8000";

let enabled = true;
let bypassNextSend = false;
let currentPrompt = "";
let currentOptimizedPrompt = "";
let currentModel = "gpt-4o-mini";


// ============================================================
// CONTROLPLANE BUTTON
// ============================================================

function createButton() {
    if (!enabled || document.getElementById(BUTTON_ID)) return;

    const button = document.createElement("button");

    button.id = BUTTON_ID;
    button.type = "button";
    button.title = "Open ControlPlane AI dashboard";
    button.textContent = "CP";

    Object.assign(button.style, {
        position: "fixed",
        right: "20px",
        bottom: "100px",
        zIndex: "2147483647",
        width: "48px",
        height: "48px",
        borderRadius: "50%",
        border: "none",
        background: "#111827",
        color: "white",
        fontWeight: "700",
        cursor: "pointer",
        boxShadow: "0 4px 20px rgba(0,0,0,0.25)"
    });

    button.addEventListener("click", () => {
        chrome.runtime.sendMessage({
            type: "OPEN_DASHBOARD"
        });
    });

    document.body.appendChild(button);
}


function removeButton() {
    document.getElementById(BUTTON_ID)?.remove();
}


// ============================================================
// GET PROMPT
// ============================================================

function getPromptElement() {
    return document.querySelector("#prompt-textarea");
}


function getPrompt() {
    const element = getPromptElement();

    if (!element) {
        return "";
    }

    return element.innerText.trim();
}


// ============================================================
// SET PROMPT
// ============================================================

function setPrompt(text) {
    const element = getPromptElement();

    if (!element) {
        return false;
    }

    element.focus();

    element.innerHTML = "";

    const paragraph = document.createElement("p");
    paragraph.dir = "auto";
    paragraph.textContent = text;

    element.appendChild(paragraph);

    element.dispatchEvent(
        new InputEvent("input", {
            bubbles: true,
            inputType: "insertText",
            data: text
        })
    );

    return true;
}


// ============================================================
// SEND BUTTON
// ============================================================

function getSendButton() {
    return document.querySelector(
        "#composer-submit-button"
    );
}


// ============================================================
// API KEY
// ============================================================

async function getApiKey() {
    const state = await chrome.storage.local.get({
        apiKey: ""
    });

    return state.apiKey?.trim() || "";
}


// ============================================================
// CHECK INPUT WITH CONTROLPLANE
// ============================================================

async function checkInput(prompt) {

    return new Promise((resolve, reject) => {

        chrome.runtime.sendMessage(
            {
                type: "CHECK_INPUT",
                prompt: prompt,
                model: currentModel
            },
            response => {

                if (chrome.runtime.lastError) {

                    reject(
                        new Error(
                            chrome.runtime.lastError.message
                        )
                    );

                    return;
                }


                if (!response) {

                    reject(
                        new Error(
                            "No response from ControlPlane service worker."
                        )
                    );

                    return;
                }


                if (!response.ok) {

                    reject(
                        new Error(
                            response.error ||
                            "ControlPlane request failed."
                        )
                    );

                    return;
                }


                resolve(response.data);
            }
        );
    });
}
// ============================================================
// MODAL
// ============================================================

function removeModal() {
    document.getElementById(MODAL_ID)?.remove();
}


function createModal(data) {

    removeModal();

    const overlay = document.createElement("div");

    overlay.id = MODAL_ID;

    Object.assign(overlay.style, {
        position: "fixed",
        inset: "0",
        zIndex: "2147483646",
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Arial, sans-serif"
    });


    const card = document.createElement("div");

    Object.assign(card.style, {
        width: "420px",
        maxWidth: "calc(100vw - 40px)",
        background: "white",
        color: "#111827",
        borderRadius: "16px",
        padding: "24px",
        boxShadow: "0 20px 60px rgba(0,0,0,0.35)"
    });


    const title = document.createElement("h2");

    title.textContent = "ControlPlane AI";

    Object.assign(title.style, {
        margin: "0 0 8px",
        fontSize: "21px"
    });


    const subtitle = document.createElement("div");

    subtitle.textContent =
        "Your message was checked before sending.";

    Object.assign(subtitle.style, {
        color: "#6b7280",
        marginBottom: "20px",
        fontSize: "14px"
    });


    // --------------------------------------------------------
    // VERDICT
    // --------------------------------------------------------

    const verdict = document.createElement("div");

    verdict.textContent =
        `Safety verdict: ${String(data.verdict).toUpperCase()}`;

    Object.assign(verdict.style, {
        padding: "10px 12px",
        borderRadius: "8px",
        background:
            data.verdict === "pass"
                ? "#ecfdf5"
                : "#fff7ed",
        color:
            data.verdict === "pass"
                ? "#047857"
                : "#c2410c",
        fontWeight: "600",
        marginBottom: "16px"
    });


    // --------------------------------------------------------
    // TOKEN/COST INFORMATION
    // --------------------------------------------------------

    const stats = document.createElement("div");

    Object.assign(stats.style, {
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "10px",
        marginBottom: "18px"
    });


    function stat(label, value) {

        const box = document.createElement("div");

        Object.assign(box.style, {
            background: "#f3f4f6",
            borderRadius: "10px",
            padding: "12px"
        });


        const labelElement =
            document.createElement("div");

        labelElement.textContent = label;

        Object.assign(labelElement.style, {
            fontSize: "12px",
            color: "#6b7280",
            marginBottom: "4px"
        });


        const valueElement =
            document.createElement("strong");

        valueElement.textContent = value;

        valueElement.style.fontSize = "16px";


        box.appendChild(labelElement);
        box.appendChild(valueElement);

        return box;
    }


    stats.appendChild(
        stat(
            "Estimated tokens",
            data.original_tokens
        )
    );

    stats.appendChild(
        stat(
            "Estimated cost",
            `$${Number(
                data.estimated_cost_usd
            ).toFixed(8)}`
        )
    );


    // --------------------------------------------------------
    // OPTIMIZATION
    // --------------------------------------------------------

    const optimization = document.createElement("div");

    Object.assign(optimization.style, {
        border: "1px solid #e5e7eb",
        borderRadius: "10px",
        padding: "14px",
        marginBottom: "18px"
    });


    const optimizationTitle =
        document.createElement("strong");

    optimizationTitle.textContent =
        "Query optimization";


    const optimizationInfo =
        document.createElement("div");

    optimizationInfo.style.marginTop = "6px";
    optimizationInfo.style.fontSize = "13px";
    optimizationInfo.style.color = "#6b7280";


    if (data.tokens_saved > 0) {

        optimizationInfo.textContent =
            `${data.tokens_saved} tokens saved • ` +
            `$${Number(
                data.savings_usd
            ).toFixed(8)} estimated savings`;

    } else {

        optimizationInfo.textContent =
            "No token savings detected for this query.";
    }


    optimization.appendChild(
        optimizationTitle
    );

    optimization.appendChild(
        optimizationInfo
    );


    // --------------------------------------------------------
    // BUTTONS
    // --------------------------------------------------------

    const buttons = document.createElement("div");

    Object.assign(buttons.style, {
        display: "flex",
        gap: "10px",
        justifyContent: "flex-end"
    });


    const cancelButton =
        document.createElement("button");

    cancelButton.textContent = "Cancel";

    Object.assign(cancelButton.style, {
        padding: "10px 15px",
        borderRadius: "8px",
        border: "1px solid #d1d5db",
        background: "white",
        cursor: "pointer"
    });


    const optimizeButton =
        document.createElement("button");

    optimizeButton.textContent =
        data.tokens_saved > 0
            ? `✨ Optimize Query — Save $${Number(
                data.savings_usd
            ).toFixed(8)}`
            : "✨ Optimize Query";


    Object.assign(optimizeButton.style, {
        padding: "10px 15px",
        borderRadius: "8px",
        border: "none",
        background: "#7c3aed",
        color: "white",
        cursor: "pointer",
        fontWeight: "600"
    });


    const sendButton =
        document.createElement("button");

    sendButton.textContent =
        "OK, SEND";


    Object.assign(sendButton.style, {
        padding: "10px 15px",
        borderRadius: "8px",
        border: "none",
        background: "#111827",
        color: "white",
        cursor: "pointer",
        fontWeight: "600"
    });


    // --------------------------------------------------------
    // CANCEL
    // --------------------------------------------------------

    cancelButton.addEventListener(
        "click",
        () => {
            removeModal();
        }
    );


    // --------------------------------------------------------
    // OPTIMIZE
    // --------------------------------------------------------

    optimizeButton.addEventListener(
        "click",
        () => {

            if (
                data.optimized_content &&
                data.optimized_content !== currentPrompt
            ) {

                currentOptimizedPrompt =
                    data.optimized_content;

                setPrompt(
                    currentOptimizedPrompt
                );

                optimizationInfo.textContent =
                    `Optimized to ${data.optimized_tokens} tokens • ` +
                    `${data.tokens_saved} tokens saved • ` +
                    `$${Number(
                        data.savings_usd
                    ).toFixed(8)} estimated savings`;

                optimizeButton.textContent =
                    "✓ Query Optimized";

                optimizeButton.disabled = true;

                optimizeButton.style.opacity = "0.7";
            }
        }
    );


    // --------------------------------------------------------
    // SEND
    // --------------------------------------------------------

    sendButton.addEventListener(
        "click",
        () => {

            removeModal();

            bypassNextSend = true;

            const button =
                getSendButton();

            if (button) {
                button.click();
            }
        }
    );


    buttons.appendChild(cancelButton);
    buttons.appendChild(optimizeButton);
    buttons.appendChild(sendButton);


    card.appendChild(title);
    card.appendChild(subtitle);
    card.appendChild(verdict);
    card.appendChild(stats);
    card.appendChild(optimization);
    card.appendChild(buttons);

    overlay.appendChild(card);

    document.body.appendChild(overlay);
}


// ============================================================
// SEND INTERCEPTION
// ============================================================

async function interceptSend(event) {

    if (!enabled) {
        return;
    }

    if (bypassNextSend) {
        bypassNextSend = false;
        return;
    }

    const prompt = getPrompt();

    if (!prompt) {
        return;
    }

    // Stop ChatGPT from sending immediately.
    event.preventDefault();
    event.stopPropagation();

    if (typeof event.stopImmediatePropagation === "function") {
        event.stopImmediatePropagation();
    }


    try {

        currentPrompt = prompt;
        currentOptimizedPrompt = prompt;

        const data =
            await checkInput(prompt);

        // BLOCK
        if (data.verdict === "block") {

            alert(
                "ControlPlane blocked this message.\n\n" +
                (data.reasons || []).join("\n")
            );

            return;
        }


        // REVIEW
        if (data.verdict === "review") {

            alert(
                "ControlPlane sent this message for review."
            );

            return;
        }


        // MASK
        if (
            data.verdict === "mask" &&
            data.content &&
            data.content !== prompt
        ) {

            currentOptimizedPrompt =
                data.content;
        }


        createModal(data);

    } catch (error) {

        console.error(
            "ControlPlane input check failed:",
            error
        );

        alert(
            "ControlPlane could not check this message.\n\n" +
            error.message
        );
    }
}


// ============================================================
// INSTALL SEND INTERCEPTOR
// ============================================================

function installSendInterceptor() {

    document.addEventListener(
        "click",
        event => {

            const sendButton =
                event.target.closest(
                    "#composer-submit-button"
                );

            if (!sendButton) {
                return;
            }

            interceptSend(event);

        },
        true
    );


    // Also support Enter-to-send.
    document.addEventListener(
        "keydown",
        event => {

            if (event.key !== "Enter") {
                return;
            }

            if (event.shiftKey) {
                return;
            }

            const target =
                event.target.closest(
                    "#prompt-textarea"
                );

            if (!target) {
                return;
            }

            const prompt = getPrompt();

            if (!prompt) {
                return;
            }

            interceptSend(event);

        },
        true
    );
}


// ============================================================
// EXTENSION STATE
// ============================================================

chrome.runtime.onMessage.addListener(
    message => {

        if (message.type === "STATE") {

            enabled =
                message.state.enabled;

            if (enabled) {
                createButton();
            } else {
                removeButton();
            }
        }
    }
);


chrome.runtime.sendMessage({
    type: "GET_STATE"
});


// ============================================================
// START
// ============================================================

installSendInterceptor();

setTimeout(
    createButton,
    1000
);