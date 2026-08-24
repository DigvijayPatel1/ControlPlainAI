const defaults = { enabled: true, optimizationEnabled: true, showTokens: true, apiKey: '' };
chrome.storage.local.get(defaults, state => { for (const id of ['enabled', 'optimizationEnabled', 'showTokens']) document.getElementById(id).checked = state[id]; document.getElementById('apiKey').value = state.apiKey; });
for (const id of ['enabled', 'optimizationEnabled', 'showTokens']) document.getElementById(id).addEventListener('change', event => chrome.storage.local.set({ [id]: event.target.checked }));
document.getElementById('apiKey').addEventListener('change', event => chrome.storage.local.set({ apiKey: event.target.value.trim() }));
document.getElementById('dashboard').addEventListener('click', () => { chrome.runtime.sendMessage({ type: 'OPEN_DASHBOARD' }); window.close(); });
