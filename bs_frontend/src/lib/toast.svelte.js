/**
 * Blackshot POS - Toast Notification State System
 * ---------------------------------------------
 * A robust, minimalist system for handling user feedback.
 */

export const toastState = $state({
    toasts: []
});

const defaultToastConfig = {
    position: 'bottom-right',
    shape: 'bean', // 'bean' or 'square'
    fontSize: '0.9rem',
    backgroundColor: '#4a332a', // Blackshot Brown
    backgroundOpacity: 100,
    textColor: '#f5f5dc', // Coffee Cream
    hasShadow: true,
    blur: 5
};

// --- Initialization & Clean Reset Logic ---
let initialConfig = { ...defaultToastConfig };

if (typeof window !== 'undefined') {
    const stored = localStorage.getItem('toast_config');
    if (stored) {
        try {
            const parsed = JSON.parse(stored);
            
            // Check for deprecated/ghost keys from previous experiments
            const hasDirtyKeys = ['customSVG', 'stackIcon', 'shapes', 'verticalOffset'].some(key => key in parsed);
            
            if (hasDirtyKeys) {
                console.log("Blackshot: Cleaning up legacy toast configuration...");
                localStorage.removeItem('toast_config');
                // stay with defaults
            } else {
                // Merge safely
                initialConfig = { ...defaultToastConfig, ...parsed };
            }
        } catch (e) {
            console.error("Blackshot: Error restoring toast config", e);
        }
    }
}

export const toastConfig = $state(initialConfig);

/** Saves current configuration to local storage */
export function saveToastConfig() {
    if (typeof window !== 'undefined') {
        localStorage.setItem('toast_config', JSON.stringify(toastConfig));
    }
}

let toastId = 0;

/**
 * Adds a new toast to the queue.
 * @param {string} message - The message to display.
 * @param {'success'|'error'|'info'} type - The visual style.
 * @param {number} duration - ms to show the toast (0 for permanent).
 */
export function addToast(message, type = 'success', duration = 3000) {
    const id = ++toastId;
    toastState.toasts.push({ id, message, type });
    
    if (duration > 0) {
        setTimeout(() => {
            removeToast(id);
        }, duration);
    }
}

/** Removes a toast by its unique ID */
export function removeToast(id) {
    toastState.toasts = toastState.toasts.filter(t => t.id !== id);
}

/** Convenient object for calling addToast with specific types */
export const toast = {
    success: (msg, duration) => addToast(msg, 'success', duration),
    error: (msg, duration) => addToast(msg, 'error', duration),
    info: (msg, duration) => addToast(msg, 'info', duration)
};
