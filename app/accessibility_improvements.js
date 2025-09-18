
    <script>
    // Add ARIA labels and roles for better accessibility
    document.addEventListener('DOMContentLoaded', function() {
        // Add ARIA labels to buttons
        const buttons = document.querySelectorAll('button');
        buttons.forEach(button => {
            if (!button.getAttribute('aria-label') && button.textContent) {
                button.setAttribute('aria-label', button.textContent.trim());
            }
        });
        
        // Add ARIA labels to input fields
        const inputs = document.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            if (!input.getAttribute('aria-label') && input.placeholder) {
                input.setAttribute('aria-label', input.placeholder);
            }
        });
        
        // Add keyboard navigation support
        document.addEventListener('keydown', function(e) {
            // Escape key to close modals or clear focus
            if (e.key === 'Escape') {
                const activeElement = document.activeElement;
                if (activeElement && activeElement.blur) {
                    activeElement.blur();
                }
            }
            
            // Enter key on history items
            if (e.key === 'Enter' && e.target.classList.contains('history-item')) {
                e.target.click();
            }
        });
        
        // Add focus indicators
        const focusableElements = document.querySelectorAll('button, input, textarea, select, [tabindex]');
        focusableElements.forEach(element => {
            element.addEventListener('focus', function() {
                this.style.outline = '2px solid #007bff';
                this.style.outlineOffset = '2px';
            });
            
            element.addEventListener('blur', function() {
                this.style.outline = '';
                this.style.outlineOffset = '';
            });
        });
    });
    
    // Add smooth scrolling for better UX
    function smoothScrollTo(element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });
    }
    
    // Add loading state management
    function showLoadingState(element, message = 'Loading...') {
        element.innerHTML = `
            <div class="loading-indicator">
                <div class="loading-spinner"></div>
                <span>${message}</span>
            </div>
        `;
    }
    
    function hideLoadingState(element, originalContent) {
        element.innerHTML = originalContent;
    }
    
    // Add notification system
    function showNotification(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, duration);
    }
    
    // Add progress tracking
    function updateProgress(percentage, message = '') {
        const progressBars = document.querySelectorAll('.progress-fill');
        progressBars.forEach(bar => {
            bar.style.width = `${percentage}%`;
        });
        
        const progressMessages = document.querySelectorAll('.progress-message');
        progressMessages.forEach(msg => {
            msg.textContent = message;
        });
    }
    
    // Add error boundary for JavaScript errors
    window.addEventListener('error', function(e) {
        console.error('JavaScript error:', e.error);
        showNotification('An unexpected error occurred. Please refresh the page.', 'error');
    });
    
    // Add performance monitoring
    if ('performance' in window) {
        window.addEventListener('load', function() {
            const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
            console.log(`Page load time: ${loadTime}ms`);
            
            if (loadTime > 3000) {
                showNotification('Page loaded slowly. Consider checking your connection.', 'warning');
            }
        });
    }
    </script>
    