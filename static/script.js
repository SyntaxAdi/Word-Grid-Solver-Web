const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const preview = document.getElementById('preview');
const solveBtn = document.getElementById('solveBtn');
const cluesInput = document.getElementById('cluesInput');
const resultsArea = document.getElementById('resultsArea');
const loading = document.getElementById('loading');
const statusIndicator = document.getElementById('statusIndicator');

let selectedFile = null;

// --- Drag & Drop ---
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        handleFile(e.dataTransfer.files[0]);
    }
});

dropZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleFile(e.target.files[0]);
    }
});

function handleFile(file) {
    if (!file.type.startsWith('image/')) {
        alert('Please upload an image file.');
        return;
    }
    selectedFile = file;

    const reader = new FileReader();
    reader.onload = (e) => {
        preview.src = e.target.result;
        preview.style.display = 'block';

        // Hide the placeholders
        const zoneContent = dropZone.querySelector('.zone-content');
        if (zoneContent) zoneContent.style.display = 'none';
    };
    reader.readAsDataURL(file);
}

// --- Solve Logic ---
solveBtn.addEventListener('click', async () => {
    if (!selectedFile) {
        alert('Please upload an image first.');
        return;
    }

    const clues = cluesInput.value.trim();
    if (!clues) {
        alert('Please paste the challenge text / clues.');
        return;
    }

    // UI Loading State
    solveBtn.disabled = true;
    solveBtn.innerHTML = '<span class="btn-icon">⏳</span> SCANNING...';

    // Reset Results
    resultsArea.innerHTML = '';
    loading.style.display = 'block';

    // Update Status
    if (statusIndicator) {
        statusIndicator.innerHTML = '<span class="dot active"></span> ANALYZING';
    }

    const formData = new FormData();
    formData.append('image', selectedFile);
    formData.append('clues', clues);

    try {
        const response = await fetch('/api/solve', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            renderError(data.error);
            if (statusIndicator) {
                statusIndicator.innerHTML = '<span class="dot" style="background: #ef4444; box-shadow: none;"></span> ERROR';
            }
        } else {
            renderResults(data);
            if (statusIndicator) {
                statusIndicator.innerHTML = '<span class="dot active" style="background: #4ade80; box-shadow: 0 0 10px #4ade80;"></span> COMPLETE';
            }
        }
    } catch (err) {
        renderError("Network or Server Error: " + err.message);
        if (statusIndicator) {
            statusIndicator.innerHTML = '<span class="dot" style="background: #ef4444; box-shadow: none;"></span> ERROR';
        }
    } finally {
        solveBtn.disabled = false;
        solveBtn.innerHTML = '<span class="btn-icon">⚡</span> INITIATE SCAN';
        loading.style.display = 'none';

        // Ensure preview stays visible
        if (selectedFile) {
            const zoneContent = dropZone.querySelector('.zone-content');
            if (zoneContent) zoneContent.style.display = 'none';
        }
    }
});

function renderResults(data) {
    let html = '';

    // Render Grid
    if (data.grid && data.grid.length > 0) {
        html += '<div style="margin-bottom: 2rem; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 1rem;">';
        html += '<div style="font-weight: bold; margin-bottom: 0.5rem; color: var(--text-secondary); letter-spacing: 0.1em; font-size: 0.8rem;">DETECTED MATRIX:</div>';
        html += '<div style="letter-spacing: 0.5em; line-height: 1.5em; font-family: monospace; color: var(--text-primary);">';
        data.grid.forEach(row => {
            html += `<div>${row.join('')}</div>`;
        });
        html += '</div></div>';
    }

    // Render Solutions
    html += '<div style="font-weight: bold; margin-bottom: 1rem; color: var(--text-secondary); letter-spacing: 0.1em; font-size: 0.8rem;">IDENTIFIED PATTERNS:</div>';

    if (data.solutions && data.solutions.length > 0) {
        data.solutions.forEach(item => {
            const hasMatch = item.found && item.found.length > 0;
            const matchClass = hasMatch ? 'matches' : 'no-match';

            let matchHtml = '[Not Found]';
            if (hasMatch) {
                matchHtml = item.found.map(word =>
                    `<span class="found-word" onclick="copyToClipboard('${word}', this)" title="Click to copy">${word}</span>`
                ).join(', ');
            }

            html += `
                <div class="result-item">
                    <span class="pattern">${item.pattern}</span> 
                    <span style="color: #444;">➜</span> 
                    <span class="${matchClass}">${matchHtml}</span>
                </div>
            `;
        });
    } else {
        html += '<div style="color: var(--text-muted);">No patterns found in input text.</div>';
    }

    resultsArea.innerHTML = html;
}

// Clipboard Helper
async function copyToClipboard(text, element) {
    try {
        await navigator.clipboard.writeText(text);

        // Visual feedback
        const originalText = element.innerText;
        element.innerText = 'COPIED!';
        element.classList.add('copied');

        setTimeout(() => {
            element.innerText = originalText;
            element.classList.remove('copied');
        }, 800);

    } catch (err) {
        console.error('Failed to copy:', err);
    }
}

function renderError(msg) {
    resultsArea.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #ef4444;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">⚠️</div>
            <div style="font-weight: 700;">SYSTEM ERROR</div>
            <div style="font-size: 0.9rem; margin-top: 0.2rem; opacity: 0.8;">${msg}</div>
        </div>
    `;
}
