import { checkInput } from '../lib/api'
import { getState, onStateChanged } from '../lib/storage'
import { guardBus } from './guardBus.ts'

const PROMPT_SELECTOR = '#prompt-textarea'
const SEND_SELECTOR = '#composer-submit-button'

let enabled = true
let bypassNextSend = false
let currentModel = 'gpt-4o-mini'

function getPromptElement(): HTMLElement | null {
    return document.querySelector(PROMPT_SELECTOR)
}

export function getPrompt(): string {
    return getPromptElement()?.innerText.trim() ?? ''
}

export function setPrompt(text: string): boolean {
    const element = getPromptElement()
    if (!element) return false

    element.focus()
    element.innerHTML = ''
    const paragraph = document.createElement('p')
    paragraph.dir = 'auto'
    paragraph.textContent = text
    element.appendChild(paragraph)

    element.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: text }))
    return true
}

function getSendButton(): HTMLElement | null {
    return document.querySelector(SEND_SELECTOR)
}

export function sendNow() {
    bypassNextSend = true
    getSendButton()?.click()
}

async function interceptSend(event: Event) {
    if (!enabled || bypassNextSend) {
        bypassNextSend = false
        return
    }

    const prompt = getPrompt()
    if (!prompt) return

    event.preventDefault()
    event.stopPropagation()
    if ('stopImmediatePropagation' in event) (event as Event).stopImmediatePropagation()

    guardBus.emit({ status: 'checking' })

    try {
        const result = await checkInput(prompt, currentModel)
        guardBus.emit({ status: result.verdict, result })
    } catch (error) {
        guardBus.emit({ status: 'error', error: error instanceof Error ? error.message : String(error) })
    }
}

export function installInterceptor() {
    document.addEventListener(
        'click',
        (event) => {
            const target = event.target as HTMLElement
            if (!target.closest(SEND_SELECTOR)) return
            void interceptSend(event)
        },
        true,
    )

    document.addEventListener(
        'keydown',
        (event) => {
            const keyboardEvent = event as KeyboardEvent
            if (keyboardEvent.key !== 'Enter' || keyboardEvent.shiftKey) return
            const target = event.target as HTMLElement
            if (!target.closest(PROMPT_SELECTOR)) return
            if (!getPrompt()) return
            void interceptSend(event)
        },
        true,
    )

    getState().then((state) => {
        enabled = state.enabled
    })
    onStateChanged((state) => {
        enabled = state.enabled
    })
}
