/**
 * Toast Notification System
 * Reusable across all pages for consistent user feedback
 */

class ToastNotification {
    constructor() {
        this.container = null;
        this.toasts = [];
        this.init();
    }

    init() {
        // Create toast container if it doesn't exist
        if (!document.getElementById('toast-container')) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'toast-container';
            this.container.setAttribute('aria-live', 'polite');
            this.container.setAttribute('aria-atomic', 'false');
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('toast-container');
        }
    }

    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - Type of toast: 'success', 'error', 'warning', 'info'
     * @param {number} duration - Duration in milliseconds (default: 3000)
     */
    show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.setAttribute('role', 'alert');

        // Icon based on type
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };

        const icon = icons[type] || icons.info;

        toast.innerHTML = `
            <span class="toast-icon">${icon}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close" aria-label="Close notification">×</button>
        `;

        // Close button functionality
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => this.remove(toast));

        // Add to container
        this.container.appendChild(toast);
        this.toasts.push(toast);

        // Trigger animation
        setTimeout(() => toast.classList.add('toast-show'), 10);

        // Auto-dismiss
        if (duration > 0) {
            setTimeout(() => this.remove(toast), duration);
        }

        return toast;
    }

    remove(toast) {
        toast.classList.add('toast-hide');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
            const index = this.toasts.indexOf(toast);
            if (index > -1) {
                this.toasts.splice(index, 1);
            }
        }, 300);
    }

    // Convenience methods
    success(message, duration = 3000) {
        return this.show(message, 'success', duration);
    }

    error(message, duration = 4000) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration = 3500) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration = 3000) {
        return this.show(message, 'info', duration);
    }

    // Clear all toasts
    clearAll() {
        this.toasts.forEach(toast => this.remove(toast));
    }
}

// Create global instance
window.Toast = new ToastNotification();

// Add CSS dynamically
const style = document.createElement('style');
style.textContent = `
    .toast-container {
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        z-index: 10000;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        max-width: 400px;
        pointer-events: none;
    }

    .toast {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        background-color: #1E293B;
        color: #FFFFFF;
        padding: 1rem 1.25rem;
        border-radius: 8px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        opacity: 0;
        transform: translateX(400px);
        transition: all 0.3s ease;
        pointer-events: auto;
        min-width: 300px;
    }

    .toast-show {
        opacity: 1;
        transform: translateX(0);
    }

    .toast-hide {
        opacity: 0;
        transform: translateX(400px);
    }

    .toast-success {
        background-color: #10B981;
        border-left: 4px solid #059669;
    }

    .toast-error {
        background-color: #EF4444;
        border-left: 4px solid #DC2626;
    }

    .toast-warning {
        background-color: #F59E0B;
        border-left: 4px solid #D97706;
    }

    .toast-info {
        background-color: #3B82F6;
        border-left: 4px solid #2563EB;
    }

    .toast-icon {
        font-size: 1.25rem;
        flex-shrink: 0;
    }

    .toast-message {
        flex: 1;
        font-size: 0.95rem;
        line-height: 1.4;
    }

    .toast-close {
        background: none;
        border: none;
        color: currentColor;
        font-size: 1.5rem;
        cursor: pointer;
        opacity: 0.7;
        transition: opacity 0.2s;
        padding: 0;
        min-width: 24px;
        min-height: 24px;
        line-height: 1;
    }

    .toast-close:hover {
        opacity: 1;
    }

    .toast-close:focus-visible {
        outline: 2px solid #FFFFFF;
        outline-offset: 2px;
        opacity: 1;
    }

    /* Mobile responsive */
    @media (max-width: 768px) {
        .toast-container {
            left: 1rem;
            right: 1rem;
            bottom: 1rem;
            max-width: none;
        }

        .toast {
            min-width: 0;
            width: 100%;
        }
    }

    @media (max-width: 480px) {
        .toast {
            padding: 0.875rem 1rem;
            font-size: 0.9rem;
        }

        .toast-icon {
            font-size: 1.1rem;
        }

        .toast-message {
            font-size: 0.875rem;
        }
    }
`;
document.head.appendChild(style);
