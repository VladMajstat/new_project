/**
 * Common JavaScript functionality for document upload pages.
 * Implements DRY principle by consolidating shared logic.
 * Includes 180-second timeout to prevent infinite spinner.
 */

const UPLOAD_TIMEOUT_MS = 180000; // 3 minutes
let uploadTimeoutId = null;

document.addEventListener('DOMContentLoaded', function() {
    const toggleHistory = document.getElementById('toggleHistory');
    const historyCard = document.getElementById('historyCard');
    const logModal = document.getElementById('logModal');
    const storageKey = getStorageKey();
    
    initHistoryToggle();
    initLogModal();
    
    function getStorageKey() {
        const path = window.location.pathname;
        if (path.includes('/photo/')) return 'showPhotoHistory';
        if (path.includes('/upload/')) return 'showUploadHistory';
        return 'showHistory';
    }
    
    function initHistoryToggle() {
        if (!toggleHistory || !historyCard) return;
        const savedState = localStorage.getItem(storageKey);
        if (savedState === 'false') {
            toggleHistory.checked = false;
            historyCard.classList.add('d-none');
        }
        toggleHistory.addEventListener('change', function() {
            historyCard.classList.toggle('d-none', !this.checked);
            localStorage.setItem(storageKey, this.checked ? 'true' : 'false');
        });
    }
    
    function initLogModal() {
        if (!logModal) return;
        logModal.addEventListener('show.bs.modal', function(event) {
            const btn = event.relatedTarget;
            const status = btn.getAttribute('data-log-status');
            const id = btn.getAttribute('data-log-id');
            const name = btn.getAttribute('data-log-name');
            const error = btn.getAttribute('data-log-error') || '';
            const header = document.getElementById('logModalHeader');
            const title = document.getElementById('logModalTitle');
            const body = document.getElementById('logModalBody');
            const now = new Date().toISOString().replace('T', ' ').substring(0, 19);
            if (status === 'success') {
                header.className = 'modal-header bg-success text-white';
                title.textContent = 'Dispolive: Success';
                body.textContent = now + ' INFO [documents.dispolive]\nDispolive SUCCESS | upload_id=' + id + '\nFile: ' + name;
            } else {
                header.className = 'modal-header bg-danger text-white';
                title.textContent = 'Dispolive: Error';
                body.textContent = now + ' ERROR [documents.dispolive]\nDispolive FAILED | upload_id=' + id + '\nFile: ' + name + '\nError: ' + error;
            }
        });
    }
    
    window.getStorageKey = getStorageKey;
});

window.setUploadButtonState = function(buttonId, loading) {
    var btn = document.getElementById(buttonId);
    var btnText = document.getElementById(buttonId + 'Text');
    var spinner = document.getElementById(buttonId + 'Spinner');
    var alert = document.getElementById('processingAlert');
    
    if (!btn) return;
    
    if (uploadTimeoutId) {
        clearTimeout(uploadTimeoutId);
        uploadTimeoutId = null;
    }
    
    if (loading) {
        if (btnText) btnText.classList.add('d-none');
        if (spinner) spinner.classList.remove('d-none');
        btn.disabled = true;
        if (alert) alert.classList.remove('d-none');
        
        uploadTimeoutId = setTimeout(function() {
            console.warn('Upload timeout - resetting button state');
            window.handleUploadError(buttonId, 'Request timeout (180s). Please try again or check server logs.');
        }, UPLOAD_TIMEOUT_MS);
    } else {
        if (btnText) btnText.classList.remove('d-none');
        if (spinner) spinner.classList.add('d-none');
        btn.disabled = false;
        if (alert) alert.classList.add('d-none');
    }
};

window.handleUploadError = function(buttonId, error) {
    if (uploadTimeoutId) {
        clearTimeout(uploadTimeoutId);
        uploadTimeoutId = null;
    }
    window.setUploadButtonState(buttonId, false);
    alert('Upload failed: ' + (error || 'Unknown error'));
    console.error('Upload error:', error);
};

window.handleNetworkError = function(buttonId, error) {
    if (uploadTimeoutId) {
        clearTimeout(uploadTimeoutId);
        uploadTimeoutId = null;
    }
    window.setUploadButtonState(buttonId, false);
    alert('Network error: ' + error);
    console.error('Network error:', error);
};

window.clearUploadTimeout = function() {
    if (uploadTimeoutId) {
        clearTimeout(uploadTimeoutId);
        uploadTimeoutId = null;
    }
};
