/**
 * milkcrate - Admin Dashboard JavaScript
 * Handles toggle (start/stop) and delete button actions.
 */

document.addEventListener('DOMContentLoaded', function() {
    initToggleButtons();
    initDeleteButtons();
    initFormLoadingStates();
});

/**
 * Handle toggle status buttons (start/stop containers).
 */
function initToggleButtons() {
    document.querySelectorAll('button[data-action="toggle"]').forEach(button => {
        button.addEventListener('click', function() {
            const appId = this.getAttribute('data-app-id');
            const csrfToken = this.getAttribute('data-csrf-token');
            
            // Create and submit form
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/admin/toggle_status/${appId}`;
            
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrf_token';
            csrfInput.value = csrfToken;
            form.appendChild(csrfInput);
            
            document.body.appendChild(form);
            form.submit();
        });
    });
}

/**
 * Handle delete buttons with confirmation.
 */
function initDeleteButtons() {
    document.querySelectorAll('button[data-action="delete"]').forEach(button => {
        button.addEventListener('click', function() {
            const appName = this.getAttribute('data-app-name');
            const appId = this.getAttribute('data-app-id');
            const csrfToken = this.getAttribute('data-csrf-token');
            
            if (!confirm(`Are you sure you want to delete "${appName}"? This action cannot be undone.`)) {
                return;
            }
            
            // Create and submit form
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/admin/delete/${appId}`;
            
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrf_token';
            csrfInput.value = csrfToken;
            form.appendChild(csrfInput);
            
            document.body.appendChild(form);
            form.submit();
        });
    });
}

/**
 * Add loading states to form submit buttons.
 */
function initFormLoadingStates() {
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function() {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton && !submitButton.disabled) {
                submitButton.disabled = true;
                submitButton.classList.add('loading');
                
                // Store original content and show loading text
                const originalContent = submitButton.innerHTML;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
                
                // Re-enable after 30s timeout
                setTimeout(() => {
                    submitButton.disabled = false;
                    submitButton.classList.remove('loading');
                    submitButton.innerHTML = originalContent;
                }, 30000);
            }
        });
    });
}
