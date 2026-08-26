import { createRoot } from 'react-dom/client';
import GuardOverlay from './GuardOverlay';
import { installInterceptor } from './chatController';
import tailwindStyles from '../index.css?inline';
function mount() {
    if (document.getElementById('controlplane-ai-root'))
        return;
    const host = document.createElement('div');
    host.id = 'controlplane-ai-root';
    document.body.appendChild(host);
    const shadowRoot = host.attachShadow({ mode: 'open' });
    const styleTag = document.createElement('style');
    styleTag.textContent = tailwindStyles;
    shadowRoot.appendChild(styleTag);
    const mountPoint = document.createElement('div');
    shadowRoot.appendChild(mountPoint);
    createRoot(mountPoint).render(<GuardOverlay />);
}
installInterceptor();
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(mount, 500);
}
else {
    document.addEventListener('DOMContentLoaded', () => setTimeout(mount, 500));
}
