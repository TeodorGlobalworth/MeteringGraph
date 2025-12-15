/**
 * Utility functions for the Metering Graph application
 */

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - Bootstrap color type (success, danger, warning, info)
 */
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    const toastId = 'toast-' + Date.now();
    
    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 5000
    });
    
    toast.show();
    
    // Remove toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

/**
 * Show a loading spinner overlay
 */
function showSpinner() {
    const spinner = document.createElement('div');
    spinner.id = 'spinnerOverlay';
    spinner.className = 'spinner-overlay';
    spinner.innerHTML = `
        <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
            <span class="visually-hidden">Loading...</span>
        </div>
    `;
    document.body.appendChild(spinner);
}

/**
 * Hide the loading spinner overlay
 */
function hideSpinner() {
    const spinner = document.getElementById('spinnerOverlay');
    if (spinner) {
        spinner.remove();
    }
}

/**
 * Debounce function to limit function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function}
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Format date to local string
 * @param {string} dateString - ISO date string
 * @returns {string}
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

/**
 * Get icon HTML for utility type (for root nodes)
 * @param {string} utilityType - Utility type (electricity, water, heating)
 * @returns {string}
 */
function getUtilityIcon(utilityType) {
    const icons = {
        'electricity': '<i class="bi bi-lightning-charge-fill node-icon" style="color: #ffc107;"></i>',
        'water': '<i class="bi bi-droplet-fill node-icon" style="color: #0dcaf0;"></i>',
        'heating': '<i class="bi bi-fire node-icon" style="color: #dc3545;"></i>'
    };
    return icons[utilityType] || '<i class="bi bi-tree node-icon"></i>';
}

/**
 * Get icon HTML for node type
 * @param {string} type - Node type
 * @param {string} utilityType - Optional utility type for MeteringTree nodes
 * @returns {string}
 */
function getNodeIcon(type, utilityType = null) {
    // For MeteringTree (utility roots), use utility-specific icons
    if (type === 'MeteringTree' && utilityType) {
        return getUtilityIcon(utilityType);
    }
    
    const icons = {
        'Meter': '<i class="bi bi-speedometer2 node-icon meter"></i>',
        'Distribution': '<i class="bi bi-diagram-3 node-icon distribution"></i>',
        'Consumer': '<i class="bi bi-outlet node-icon consumer"></i>',
        'MeteringTree': '<i class="bi bi-tree node-icon"></i>'
    };
    return icons[type] || '<i class="bi bi-circle node-icon"></i>';
}

/**
 * Get node type from labels array
 * @param {Array} labels - Array of node labels
 * @returns {string}
 */
function getNodeType(labels) {
    if (!labels || labels.length === 0) return 'Unknown';
    
    const types = ['MeteringTree', 'Meter', 'Distribution', 'Consumer'];
    for (const type of types) {
        if (labels.includes(type)) {
            return type;
        }
    }
    return labels[0];
}

/**
 * Truncate text to specified length
 * @param {string} text - Text to truncate
 * @param {number} length - Max length
 * @returns {string}
 */
function truncateText(text, length = 50) {
    if (!text) return '';
    if (text.length <= length) return text;
    return text.substring(0, length) + '...';
}

/**
 * Download data as JSON file
 * @param {Object} data - Data to download
 * @param {string} filename - Filename
 */
function downloadJSON(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

/**
 * Download data as CSV file
 * @param {Array} data - Array of objects
 * @param {string} filename - Filename
 */
function downloadCSV(data, filename) {
    if (data.length === 0) {
        showToast('No data to export', 'warning');
        return;
    }
    
    // Get headers
    const headers = Object.keys(data[0]);
    
    // Build CSV
    let csv = headers.join(',') + '\n';
    data.forEach(row => {
        const values = headers.map(header => {
            const value = row[header];
            // Escape commas and quotes
            if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                return '"' + value.replace(/"/g, '""') + '"';
            }
            return value;
        });
        csv += values.join(',') + '\n';
    });
    
    const blob = new Blob([csv], {type: 'text/csv'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

/**
 * Parse error response
 * @param {Response} response - Fetch response
 * @returns {Promise<string>}
 */
async function parseError(response) {
    try {
        const error = await response.json();
        return error.error || error.message || 'Unknown error';
    } catch {
        return response.statusText || 'Unknown error';
    }
}

/**
 * Validate form inputs
 * @param {HTMLFormElement} form - Form element
 * @returns {boolean}
 */
function validateForm(form) {
    if (!form.checkValidity()) {
        form.classList.add('was-validated');
        return false;
    }
    return true;
}

/**
 * Clear form validation
 * @param {HTMLFormElement} form - Form element
 */
function clearFormValidation(form) {
    form.classList.remove('was-validated');
    form.querySelectorAll('.is-invalid').forEach(el => {
        el.classList.remove('is-invalid');
    });
}

/**
 * Get current project ID from URL
 * @returns {number|null}
 */
function getCurrentProjectId() {
    const match = window.location.pathname.match(/\/projects\/(\d+)/);
    return match ? parseInt(match[1]) : null;
}

/**
 * Format file size
 * @param {number} bytes - Size in bytes
 * @returns {string}
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
