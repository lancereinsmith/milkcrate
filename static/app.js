/**
 * milkcrate - Main JavaScript file
 * Minimal version: form validation, delete confirmations, flash toasts
 */

document.addEventListener('DOMContentLoaded', function() {
    initFormValidation();
    initDeleteConfirmations();
    initFlashToasts();
    initTooltips();
});

/**
 * Re-initialize components after HTMX swaps in new content.
 */
document.addEventListener('htmx:afterSwap', function(event) {
    initTooltips();
    initDeleteConfirmations();
    // Re-init toggle/delete buttons from admin.js if available
    if (typeof initToggleButtons === 'function') {
        initToggleButtons();
    }
    if (typeof initDeleteButtons === 'function') {
        initDeleteButtons();
    }
});

/**
 * Basic form validation with loading state on submit.
 */
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                submitBtn.classList.add('loading');
                submitBtn.disabled = true;
                
                // Re-enable after 30s in case of network issues
                setTimeout(() => {
                    submitBtn.classList.remove('loading');
                    submitBtn.disabled = false;
                }, 30000);
            }
        });
    });
}

/**
 * Confirm before deleting applications.
 */
function initDeleteConfirmations() {
    const deleteButtons = document.querySelectorAll('.btn-delete');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const appName = this.dataset.appName || 'this application';
            if (!confirm(`Are you sure you want to delete ${appName}? This action cannot be undone.`)) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    });
}

/**
 * Initialize Bootstrap toasts for flash messages.
 */
function initFlashToasts() {
    if (typeof bootstrap === 'undefined' || !bootstrap.Toast) return;
    
    const container = document.getElementById('flash-toast-container');
    if (!container) return;
    
    const toastEls = container.querySelectorAll('.toast');
    toastEls.forEach(el => {
        try {
            const toast = new bootstrap.Toast(el);
            toast.show();
        } catch (err) {
            // Ignore toast initialization errors
        }
    });
}

/**
 * Initialize Bootstrap tooltips.
 */
function initTooltips() {
    if (typeof bootstrap === 'undefined' || !bootstrap.Tooltip) return;
    
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach(el => {
        new bootstrap.Tooltip(el);
    });
}
