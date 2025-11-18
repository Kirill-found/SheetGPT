async function testGetToken() {
    const result = document.getElementById('token-result');
    result.innerHTML = '⏳ Testing...';

    try {
        const token = await new Promise((resolve, reject) => {
            chrome.identity.getAuthToken({ interactive: true }, (token) => {
                if (chrome.runtime.lastError) {
                    reject(chrome.runtime.lastError);
                } else {
                    resolve(token);
                }
            });
        });

        result.innerHTML = `
            <p class="success">✅ Token OK!</p>
            <p>Token (first 20 chars): <code>${token.substring(0, 20)}...</code></p>
            <p><strong>OAuth works! The problem is elsewhere.</strong></p>
        `;
    } catch (error) {
        result.innerHTML = `
            <p class="error">❌ OAuth Error:</p>
            <pre>${error.message}</pre>
            <p><strong>OAuth needs configuration in Google Cloud Console</strong></p>
        `;
    }
}

function checkManifest() {
    const result = document.getElementById('manifest-result');
    const manifest = chrome.runtime.getManifest();

    result.innerHTML = `
        <h3>OAuth Configuration:</h3>
        <pre>${JSON.stringify(manifest.oauth2, null, 2)}</pre>

        <h3>Permissions:</h3>
        <pre>${JSON.stringify(manifest.permissions, null, 2)}</pre>

        <h3>Extension ID:</h3>
        <p><code>${chrome.runtime.id}</code></p>
        <p>Add this to Google Cloud Console Authorized origins:</p>
        <p><code>chrome-extension://${chrome.runtime.id}</code></p>
    `;
}

// Add event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('test-token-btn').addEventListener('click', testGetToken);
    document.getElementById('check-manifest-btn').addEventListener('click', checkManifest);
});
