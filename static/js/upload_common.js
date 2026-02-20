/**
 * Common JavaScript functionality for document upload pages.
 * Implements DRY principle by consolidating shared logic.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Common elements
    const toggleHistory = document.getElementById('toggleHistory');
    const historyCard = document.getElementById('historyCard');
    const logModal = document.getElementById('logModal');
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    
    // Storage key for history visibility (page-specific)
    const storageKey = getStorageKey();
    
    // Initialize common functionality
    initHistoryToggle();
    initLogModal();
    initClearHistory();
    
    /**
     * Get page-specific storage key
     */
    function getStorageKey() {
        const path = window.location.pathname;
        if (path.includes('/photo/')) {
            return 'showPhotoHistory';
        } else if (path.includes('/upload/')) {
            return 'showUploadHistory';
        }
        return 'showHistory';
    }
    
    /**
     * Initialize history toggle functionality
     */
    function initHistoryToggle() {
        if (!toggleHistory || !historyCard) return;
        
        // Restore saved state
        const savedState = localStorage.getItem(storageKey);
        if (savedState === 'false') {
            toggleHistory.checked = false;
            historyCard.classList.add('d-none');
        }

        toggleHistory.addEventListener('change', function() {
            if (this.checked) {
                historyCard.classList.remove('d-none');
                localStorage.setItem(storageKey, 'true');
            } else {
                historyCard.classList.add('d-none');
                localStorage.setItem(storageKey, 'false');
            }
        });
    }
    
    /**
     * Initialize log modal functionality
     */
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
                title.textContent = '✓ Dispolive: Успішно';
                body.textContent = `${now} INFO [documents.dispolive]\nDispolive SUCCESS | upload_id=${id}\nFile: ${name}`;
            } else {
                header.className = 'modal-header bg-danger text-white';
                title.textContent = '✗ Dispolive: Помилка';
                body.textContent = `${now} ERROR [documents.dispolive]\nDispolive FAILED | upload_id=${id}\nFile: ${name}\nError: ${error}`;
            }
        });
    }
    
    /**
     * Initialize clear history functionality
     */
    function initClearHistory() {
        if (!clearHistoryBtn) return;
        
        clearHistoryBtn.addEventListener('click', function() {
            // Modal will be shown by Bootstrap automatically
        });
    }
    
    /**
     * Common upload button state management
     */
    window.setUploadButtonState = function(buttonId, loading, loadingText = 'Processing...') {
        const btn = document.getElementById(buttonId);
        const btnText = document.getElementById(buttonId + 'Text');
        const spinner = document.getElementById(buttonId + 'Spinner');
        const alert = document.getElementById('processingAlert');
        
        if (!btn) return;
        
        if (loading) {
            if (btnText) btnText.classList.add('d-none');
            if (spinner) spinner.classList.remove('d-none');
            btn.disabled = true;
            if (alert) alert.classList.remove('d-none');
        } else {
            if (btnText) btnText.classList.remove('d-none');
            if (spinner) spinner.classList.add('d-none');
            btn.disabled = false;
            if (alert) alert.classList.add('d-none');
        }
    };
    
    /**
     * Common AJAX error handling
     */
    window.handleUploadError = function(buttonId, error) {
        setUploadButtonState(buttonId, false);
        alert('Upload failed: ' + (error || 'Unknown error'));
        console.error('Upload error:', error);
    };
    
    /**
     * Common network error handling
     */
    window.handleNetworkError = function(buttonId, error) {
        setUploadButtonState(buttonId, false);
        alert('Network error: ' + error);
        console.error('Network error:', error);
    };
    
    // Make functions globally available for page-specific scripts
    window.getStorageKey = getStorageKey;
});
