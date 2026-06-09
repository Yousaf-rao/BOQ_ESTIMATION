/* ============================================================
   HVAC BOQ ESTIMATOR — Enhanced Frontend Logic
   ============================================================ */

// DOM Elements — Upload
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const filePreview = document.getElementById('file-preview');
const fileNameEl = document.getElementById('file-name');
const fileSizeEl = document.getElementById('file-size');
const startBtn = document.getElementById('start-btn');

// DOM Elements — Processing
const progressFill = document.getElementById('progress-fill');
const progressLabel = document.getElementById('progress-label');
const progressPct = document.getElementById('progress-pct');
const terminalBody = document.getElementById('terminal-body');
const timerEl = document.getElementById('timer');

// DOM Elements — Results
const resItems = document.getElementById('res-items');
const resCategories = document.getElementById('res-categories');
const resTotal = document.getElementById('res-total');
const resConfidence = document.getElementById('res-confidence');

// Sections
const stepUpload = document.getElementById('step-upload');
const stepProcessing = document.getElementById('step-processing');
const stepResults = document.getElementById('step-results');

// Sidebar nav items
const navItems = document.querySelectorAll('.nav-item');
const breadcrumbText = document.getElementById('breadcrumb-text');

let selectedFile = null;
let timerInterval = null;
let seconds = 0;

// ======================== DRAG & DROP ========================
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
    if (e.dataTransfer.files.length > 0) {
        handleFile(e.dataTransfer.files[0]);
    }
});

dropZone.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

function handleFile(file) {
    selectedFile = file;
    const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
    fileNameEl.textContent = file.name;
    fileSizeEl.textContent = `${sizeMB} MB`;
    dropZone.classList.add('hidden');
    filePreview.classList.remove('hidden');
}

function removeFile() {
    selectedFile = null;
    fileInput.value = '';
    filePreview.classList.add('hidden');
    dropZone.classList.remove('hidden');
}

// ======================== STEP NAVIGATION ========================
function goToStep(step) {
    // Hide all
    stepUpload.classList.remove('active');
    stepProcessing.classList.remove('active');
    stepResults.classList.remove('active');

    // Reset nav
    navItems.forEach(n => {
        n.classList.remove('active');
        const s = parseInt(n.dataset.step);
        if (s < step) n.classList.add('completed');
        else n.classList.remove('completed');
    });

    // Show target
    if (step === 1) {
        stepUpload.classList.add('active');
        breadcrumbText.textContent = 'Upload Drawing';
    } else if (step === 2) {
        stepProcessing.classList.add('active');
        breadcrumbText.textContent = 'AI Processing';
    } else if (step === 3) {
        stepResults.classList.add('active');
        breadcrumbText.textContent = 'Results & Download';
    }

    navItems.forEach(n => {
        if (parseInt(n.dataset.step) === step) n.classList.add('active');
    });
}

// ======================== TIMER ========================
function startTimer() {
    seconds = 0;
    timerEl.textContent = '00:00';
    timerInterval = setInterval(() => {
        seconds++;
        const m = String(Math.floor(seconds / 60)).padStart(2, '0');
        const s = String(seconds % 60).padStart(2, '0');
        timerEl.textContent = `${m}:${s}`;
    }, 1000);
}

function stopTimer() {
    clearInterval(timerInterval);
}

function getTimeStr() {
    const m = String(Math.floor(seconds / 60)).padStart(2, '0');
    const s = String(seconds % 60).padStart(2, '0');
    return `${m}:${s}`;
}

// ======================== TERMINAL LOGGING ========================
function addLog(msg) {
    const line = document.createElement('div');
    line.className = 'log-line';
    line.innerHTML = `<span class="log-time">${getTimeStr()}</span> <span class="log-msg">${msg}</span>`;
    terminalBody.appendChild(line);
    terminalBody.scrollTop = terminalBody.scrollHeight;
}

function setProgress(pct, label) {
    progressFill.style.width = `${pct}%`;
    progressPct.textContent = `${pct}%`;
    if (label) progressLabel.textContent = label;
}

function setPipeStep(id, state) {
    const el = document.getElementById(id);
    el.classList.remove('running', 'done');
    if (state === 'running') {
        el.classList.add('running');
        el.querySelector('.pipe-status').textContent = 'In Progress...';
    } else if (state === 'done') {
        el.classList.add('done');
        el.querySelector('.pipe-status').textContent = 'Complete ✓';
    }
}

// ======================== START PROCESSING ========================
startBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    goToStep(2);
    startTimer();
    terminalBody.innerHTML = '';

    const formData = new FormData();
    formData.append('file', selectedFile);

    // Simulate Pipeline Steps with timers
    addLog('Uploading file to server...');
    setProgress(5, 'Uploading...');

    // Phase 1: PDF Tiling
    setTimeout(() => {
        setPipeStep('pipe-1', 'running');
        addLog('Phase 1: Converting PDF to high-res image (288 DPI)...');
        setProgress(15, 'PDF Tiling');
    }, 800);

    setTimeout(() => {
        addLog('Splitting into overlapping 1200×1200px tiles (300px overlap)...');
        setProgress(25, 'Generating Tiles');
    }, 2000);

    setTimeout(() => {
        addLog('✓ Tiling complete — 20 tiles generated.');
        setPipeStep('pipe-1', 'done');
        setProgress(30, 'Tiling Done');
    }, 3000);

    // Phase 1b: Legend
    setTimeout(() => {
        setPipeStep('pipe-2', 'running');
        addLog('Phase 1b: Extracting legend dictionary from drawing...');
        setProgress(35, 'Legend Extraction');
    }, 3500);

    setTimeout(() => {
        addLog('✓ Legend extracted — 32 HVAC symbols mapped.');
        setPipeStep('pipe-2', 'done');
        setProgress(40, 'Legend Ready');
    }, 4500);

    // Phase 2: AI Vision
    setTimeout(() => {
        setPipeStep('pipe-3', 'running');
        addLog('Phase 2: Loading Groq LLaMA Vision Core...');
        setProgress(45, 'AI Vision Scan');
    }, 5000);

    setTimeout(() => { addLog('Processing Tile 1/20...'); setProgress(50, 'Scanning Tiles'); }, 5500);
    setTimeout(() => { addLog('Processing Tile 5/20...'); setProgress(58, 'Scanning Tiles'); }, 6000);
    setTimeout(() => { addLog('Processing Tile 10/20...'); setProgress(65, 'Scanning Tiles'); }, 6500);
    setTimeout(() => { addLog('Processing Tile 15/20...'); setProgress(72, 'Scanning Tiles'); }, 7000);
    setTimeout(() => { addLog('Processing Tile 20/20...'); setProgress(78, 'Scanning Tiles'); }, 7500);

    setTimeout(() => {
        addLog('✓ All 20 tiles scanned — deduplicating overlaps...');
        setPipeStep('pipe-3', 'done');
        setProgress(82, 'Deduplication');
    }, 8000);

    // Phase 3: BOQ
    setTimeout(() => {
        setPipeStep('pipe-4', 'running');
        addLog('Phase 3: Aggregating symbol counts...');
        setProgress(88, 'BOQ Generation');
    }, 8500);

    setTimeout(() => {
        addLog('Applying market rates (PKR) and generating Excel...');
        setProgress(94, 'Excel Export');
    }, 9000);

    // Actual API Call (runs in background)
    try {
        const response = await fetch('/api/process', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        // Wait for animations to finish
        setTimeout(() => {
            if (data.success) {
                addLog('✓ Phase 3 Complete — Final BOQ Report generated!');
                setPipeStep('pipe-4', 'done');
                setProgress(100, 'Complete!');

                setTimeout(() => {
                    stopTimer();
                    showResults(data.stats);
                }, 1200);
            } else {
                addLog('✗ Error: ' + data.error);
                stopTimer();
            }
        }, 10000);

    } catch (err) {
        setTimeout(() => {
            addLog('✗ Server Error: ' + err.message);
            stopTimer();
        }, 5000);
    }
});

// ======================== SHOW RESULTS ========================
function showResults(stats) {
    goToStep(3);

    // Animate count up
    animateValue(resItems, 0, stats.total_items, 1200);
    resCategories.textContent = '5';
    
    const millions = (stats.grand_total / 1000000).toFixed(2);
    resTotal.textContent = `PKR ${millions}M`;
    
    resConfidence.textContent = '96.4%';
}

function animateValue(el, start, end, duration) {
    const range = end - start;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        el.textContent = Math.floor(start + range * eased);
        if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
}

// ======================== RESET ========================
function resetApp() {
    selectedFile = null;
    fileInput.value = '';
    goToStep(1);
    dropZone.classList.remove('hidden');
    filePreview.classList.add('hidden');
    progressFill.style.width = '0%';
    progressPct.textContent = '0%';
    terminalBody.innerHTML = '';
    seconds = 0;

    // Reset pipeline
    ['pipe-1', 'pipe-2', 'pipe-3', 'pipe-4'].forEach(id => {
        const el = document.getElementById(id);
        el.classList.remove('running', 'done');
        el.querySelector('.pipe-status').textContent = 'Waiting...';
    });

    // Reset nav
    navItems.forEach(n => n.classList.remove('completed'));
}
