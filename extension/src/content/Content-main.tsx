import { createRoot } from 'react-dom/client'
import GuardOverlay from './GuardOverlay'
import { installInterceptor } from './chatController'

function mount() {
    if (document.getElementById('controlplane-ai-root')) return

    const host = document.createElement('div')
    host.id = 'controlplane-ai-root'
    document.body.appendChild(host)

    // Shadow DOM keeps ChatGPT's page styles from leaking into our card
    // (and vice versa) — the same isolation trick Grammarly's overlay uses.
    const shadowRoot = host.attachShadow({ mode: 'open' })
    const mountPoint = document.createElement('div')
    shadowRoot.appendChild(mountPoint)

    createRoot(mountPoint).render(<GuardOverlay />)
}

installInterceptor()

if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(mount, 500)
} else {
    document.addEventListener('DOMContentLoaded', () => setTimeout(mount, 500))
}
