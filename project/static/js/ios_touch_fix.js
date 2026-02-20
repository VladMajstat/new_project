(function() {
    'use strict';
    if (!('ontouchstart' in window)) return;
    
    document.addEventListener('DOMContentLoaded', function() {
        var modalTriggers = document.querySelectorAll('[data-bs-toggle="modal"]');
        modalTriggers.forEach(function(trigger) {
            trigger.addEventListener('touchend', function(e) {
                e.preventDefault();
                var targetModal = this.getAttribute('data-bs-target');
                if (targetModal) {
                    var modal = document.querySelector(targetModal);
                    if (modal && typeof bootstrap !== 'undefined') {
                        var bsModal = new bootstrap.Modal(modal);
                        bsModal.show();
                    }
                }
            }, { passive: false });
        });
        
        var btnIcons = document.querySelectorAll('.btn-icon, .btn-icon-warning, .btn-icon-success, .btn-icon-secondary, .btn-icon-info');
        btnIcons.forEach(function(btn) {
            btn.addEventListener('touchend', function(e) {
                if (this.tagName === 'A' && this.href) {
                    e.preventDefault();
                    window.location.href = this.href;
                }
            }, { passive: false });
        });
        console.log('iOS touch fix applied');
    });
})();
