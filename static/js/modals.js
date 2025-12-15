/**
 * Modal handlers and form submissions
 */

let currentParentId = null;
let currentParentName = null;
let currentEditNodeId = null;

// Add Node Modal
async function openAddNodeModal(parentId, parentName) {
    currentParentId = parentId;
    currentParentName = parentName;
    
    // Load all nodes for parent selection
    await loadParentNodes(parentId);
    
    document.getElementById('addNodeForm').reset();
    
    const modal = new bootstrap.Modal(document.getElementById('addNodeModal'));
    modal.show();
}

async function loadParentNodes(selectedParentId) {
    try {
        // Use search endpoint with empty query to get all nodes
        const response = await fetch(`/api/graph/search?project_id=${PROJECT_ID}&q=`);
        const nodes = await response.json();
        
        const select = document.getElementById('parentNodeSelect');
        select.innerHTML = '';
        
        // Add utility root options
        const utilityRoots = [
            { value: '__electricity__', label: '⚡ Electricity Infrastructure (Root)', utility: 'electricity' },
            { value: '__water__', label: '💧 Water Infrastructure (Root)', utility: 'water' },
            { value: '__heating__', label: '🔥 Heating Infrastructure (Root)', utility: 'heating' }
        ];
        
        utilityRoots.forEach(root => {
            const option = document.createElement('option');
            option.value = root.value;
            option.textContent = root.label;
            option.dataset.utility = root.utility;
            select.appendChild(option);
        });
        
        // Add separator
        const separator = document.createElement('option');
        separator.disabled = true;
        separator.textContent = '──────────────';
        select.appendChild(separator);
        
        // Sort nodes by name
        nodes.sort((a, b) => a.name.localeCompare(b.name));
        
        // Add all nodes (excluding MeteringTree root nodes)
        nodes.filter(n => !n.is_utility_root).forEach(node => {
            const option = document.createElement('option');
            option.value = node.id;
            const nodeType = getNodeType(node.labels);
            const utilityIcon = node.utility_type === 'electricity' ? '⚡' : 
                               node.utility_type === 'water' ? '💧' : 
                               node.utility_type === 'heating' ? '🔥' : '📦';
            option.textContent = `${utilityIcon} ${node.name} (${nodeType})`;
            option.dataset.utility = node.utility_type || '';
            if (node.id === selectedParentId) {
                option.selected = true;
            }
            select.appendChild(option);
        });
        
        // Select appropriate root based on current utility filter or first option
        if (!selectedParentId) {
            const defaultUtility = currentUtilityFilter !== 'all' ? currentUtilityFilter : 'electricity';
            const defaultOption = select.querySelector(`option[data-utility="${defaultUtility}"]`);
            if (defaultOption) {
                defaultOption.selected = true;
            }
        }
        
    } catch (error) {
        console.error('Error loading parent nodes:', error);
        const select = document.getElementById('parentNodeSelect');
        select.innerHTML = '<option value="">Error loading nodes</option>';
    }
}

// Initialize event listeners after DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const nodeTypeSelect = document.getElementById('nodeType');
    if (nodeTypeSelect) {
        nodeTypeSelect.addEventListener('change', async function() {
            const type = this.value;
            const subtypeGroup = document.getElementById('subtypeGroup');
            const categoryGroup = document.getElementById('categoryGroup');
            
            if (type === 'Consumer') {
                subtypeGroup.style.display = 'none';
                categoryGroup.style.display = 'block';
                await loadCategories('Consumer');
            } else if (type === 'Meter' || type === 'Distribution') {
                categoryGroup.style.display = 'none';
                subtypeGroup.style.display = 'block';
                await loadCategories(type);
            }
        });
    }
    
    const nodeSubtype = document.getElementById('nodeSubtype');
    if (nodeSubtype) {
        nodeSubtype.addEventListener('change', function() {
            if (this.value === '__other__') {
                const custom = prompt('Enter new subtype name:');
                if (custom) {
                    const option = document.createElement('option');
                    option.value = custom;
                    option.textContent = custom;
                    option.selected = true;
                    this.insertBefore(option, this.lastElementChild);
                }
            }
        });
    }
    
    const nodeCategory = document.getElementById('nodeCategory');
    if (nodeCategory) {
        nodeCategory.addEventListener('change', function() {
            if (this.value === '__other__') {
                const custom = prompt('Enter new category name:');
                if (custom) {
                    const option = document.createElement('option');
                    option.value = custom;
                    option.textContent = custom;
                    option.selected = true;
                    this.insertBefore(option, this.lastElementChild);
                }
            }
        });
    }
});

async function loadCategories(nodeType) {
    try {
        const select = nodeType === 'Consumer' ? 
            document.getElementById('nodeCategory') : 
            document.getElementById('nodeSubtype');
        
        select.innerHTML = '<option value="">Select...</option>';
        
        if (nodeType === 'Consumer') {
            // Use global consumer categories from settings
            const categories = window.consumerCategories || [];
            categories.filter(cat => cat.is_active).forEach(cat => {
                const option = document.createElement('option');
                option.value = cat.category_name;
                option.textContent = cat.display_name;
                select.appendChild(option);
            });
        } else {
            // Load project-specific categories for other types
            const response = await fetch(`/api/categories?project_id=${PROJECT_ID}&node_type=${nodeType}`);
            const categories = await response.json();
            
            categories.forEach(cat => {
                const option = document.createElement('option');
                option.value = cat.category_name;
                option.textContent = cat.category_name;
                select.appendChild(option);
            });
        }
        
        // Add "Other" option
        const otherOption = document.createElement('option');
        otherOption.value = '__other__';
        otherOption.textContent = '+ Add New...';
        select.appendChild(otherOption);
        
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

async function submitAddNode() {
    const form = document.getElementById('addNodeForm');
    if (!validateForm(form)) return;
    
    const parentSelect = document.getElementById('parentNodeSelect');
    const parentValue = parentSelect.value;
    
    // Handle utility root options
    let parentId = null;
    let autoUtilityType = null;
    
    if (parentValue.startsWith('__') && parentValue.endsWith('__')) {
        // It's a utility root placeholder - set utility type, backend will find root
        autoUtilityType = parentValue.replace(/__/g, '');
        parentId = null;  // Will be resolved by backend
    } else if (parentValue) {
        parentId = parentValue;
    }
    
    const nodeType = document.getElementById('nodeType').value;
    const name = document.getElementById('nodeName').value;
    const description = document.getElementById('nodeDescription').value;
    const utilityType = document.getElementById('nodeUtilityType').value || autoUtilityType || 'electricity';
    
    const properties = {
        name: name,
        description: description,
        utility_type: utilityType
    };
    
    // Add subtype or category
    if (nodeType === 'Consumer') {
        const category = document.getElementById('nodeCategory').value;
        if (category && category !== '__other__') {
            properties.category = category;
        }
    } else {
        const subtype = document.getElementById('nodeSubtype').value;
        if (subtype && subtype !== '__other__') {
            properties.subtype = subtype;
        }
    }
    
    // Optional fields
    const serialNumber = document.getElementById('nodeSerial').value;
    const location = document.getElementById('nodeLocation').value;
    const installDate = document.getElementById('nodeInstallDate').value;
    
    if (serialNumber) properties.serial_number = serialNumber;
    if (location) properties.location = location;
    if (installDate) properties.installation_date = installDate;
    
    try {
        const response = await fetch('/api/nodes', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                project_id: PROJECT_ID,
                type: nodeType,
                parent_id: parentId,
                properties: properties
            })
        });
        
        if (response.ok) {
            showToast('Node created successfully', 'success');
            bootstrap.Modal.getInstance(document.getElementById('addNodeModal')).hide();
            
            // Refresh views
            initializeTreeView();
            if (selectedNodeId) {
                loadGraphContext(selectedNodeId);
            }
        } else {
            const error = await response.json();
            showToast('Error creating node: ' + error.error, 'danger');
        }
    } catch (error) {
        showToast('Error creating node: ' + error.message, 'danger');
    }
}

// Edit Node Modal
async function openEditNodeModal(nodeId) {
    openNodeModal(nodeId, false);  // false = edit mode
}

// View Details Modal (read-only)
async function openViewDetailsModal(nodeId) {
    openNodeModal(nodeId, true);  // true = view-only mode
}

// Common function for edit/view modal
async function openNodeModal(nodeId, viewOnly = false) {
    currentEditNodeId = nodeId;
    
    // Get node data from graph
    const node = cy.getElementById(nodeId);
    if (!node.length) return;
    
    const data = node.data('fullData');
    const nodeType = getNodeType(data.labels || []);
    
    // Update modal title and buttons
    document.getElementById('editNodeModalTitle').textContent = viewOnly ? 'View Node Details' : 'Edit Node';
    document.getElementById('editNodeSaveBtn').style.display = viewOnly ? 'none' : 'block';
    
    // Set form fields
    document.getElementById('editNodeType').value = nodeType;
    document.getElementById('editNodeUtilityType').value = data.utility_type || '-';
    document.getElementById('editNodeName').value = data.name || '';
    document.getElementById('editNodeDescription').value = data.description || '';
    document.getElementById('editNodeSerial').value = data.serial_number || '';
    document.getElementById('editNodeLocation').value = data.location || '';
    document.getElementById('editNodeInstallDate').value = data.installation_date || '';
    document.getElementById('editNodeSubtype').value = data.subtype || '';
    document.getElementById('editNodeDistSubtype').value = data.subtype || '';
    
    // Format dates for display
    document.getElementById('editNodeCreated').textContent = data.created_at ? formatDate(data.created_at) : '-';
    document.getElementById('editNodeUpdated').textContent = data.updated_at ? formatDate(data.updated_at) : '-';
    
    // Populate category dropdown for Consumer nodes
    if (nodeType === 'Consumer') {
        const categorySelect = document.getElementById('editNodeCategory');
        categorySelect.innerHTML = '<option value="">-- Select Category --</option>';
        const categories = window.consumerCategories || [];
        categories.filter(cat => cat.is_active).forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.category_name;
            option.textContent = cat.display_name;
            categorySelect.appendChild(option);
        });
        // Now set the value
        categorySelect.value = data.category || '';
    }
    
    // Show/hide type-specific fields
    document.getElementById('editMeterFields').style.display = nodeType === 'Meter' ? 'block' : 'none';
    document.getElementById('editConsumerFields').style.display = nodeType === 'Consumer' ? 'block' : 'none';
    document.getElementById('editDistributionFields').style.display = nodeType === 'Distribution' ? 'block' : 'none';
    
    // Set read-only state for all form inputs
    const formInputs = document.querySelectorAll('#editNodeForm input:not([readonly]), #editNodeForm textarea, #editNodeForm select:not([disabled])');
    formInputs.forEach(input => {
        if (viewOnly) {
            input.setAttribute('readonly', 'readonly');
            input.setAttribute('disabled', 'disabled');
        } else {
            // Don't remove readonly from type/utility fields
            if (input.id !== 'editNodeType' && input.id !== 'editNodeUtilityType') {
                input.removeAttribute('readonly');
                input.removeAttribute('disabled');
            }
        }
    });
    
    const modal = new bootstrap.Modal(document.getElementById('editNodeModal'));
    modal.show();
}

async function submitEditNode() {
    const form = document.getElementById('editNodeForm');
    if (!validateForm(form)) return;
    
    const nodeType = document.getElementById('editNodeType').value;
    
    const properties = {
        name: document.getElementById('editNodeName').value,
        description: document.getElementById('editNodeDescription').value,
        location: document.getElementById('editNodeLocation').value,
        installation_date: document.getElementById('editNodeInstallDate').value
    };
    
    // Add type-specific properties
    if (nodeType === 'Meter') {
        properties.serial_number = document.getElementById('editNodeSerial').value;
        properties.subtype = document.getElementById('editNodeSubtype').value;
    } else if (nodeType === 'Consumer') {
        properties.category = document.getElementById('editNodeCategory').value;
    } else if (nodeType === 'Distribution') {
        properties.subtype = document.getElementById('editNodeDistSubtype').value;
    }
    
    try {
        const response = await fetch(`/api/nodes/${currentEditNodeId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                project_id: PROJECT_ID,
                properties: properties
            })
        });
        
        if (response.ok) {
            showToast('Node updated successfully', 'success');
            bootstrap.Modal.getInstance(document.getElementById('editNodeModal')).hide();
            
            // Refresh views
            initializeTreeView();
            if (selectedNodeId) {
                loadGraphContext(selectedNodeId);
            }
        } else {
            const error = await response.json();
            showToast('Error updating node: ' + error.error, 'danger');
        }
    } catch (error) {
        showToast('Error updating node: ' + error.message, 'danger');
    }
}

// Bulk Import Modal
async function submitBulkImport() {
    const fileInput = document.getElementById('bulkImportFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showToast('Please select a file', 'warning');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', PROJECT_ID);
    
    try {
        showSpinner();
        
        const response = await fetch('/api/bulk/nodes', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        hideSpinner();
        
        if (response.ok || response.status === 207) {
            let message = `Successfully imported ${result.success} of ${result.total} nodes`;
            if (result.errors && result.errors.length > 0) {
                message += `. ${result.errors.length} errors occurred.`;
                console.error('Import errors:', result.errors);
                
                // Show detailed errors in alert
                let errorDetails = result.errors.slice(0, 10).map(e => `Row ${e.row}: ${e.error}`).join('\n');
                if (result.errors.length > 10) {
                    errorDetails += `\n... and ${result.errors.length - 10} more errors (see console)`;
                }
                alert('Import completed with errors:\n\n' + errorDetails);
            }
            showToast(message, result.errors && result.errors.length > 0 ? 'warning' : 'success');
            
            bootstrap.Modal.getInstance(document.getElementById('bulkImportModal')).hide();
            
            // Refresh views
            initializeTreeView();
            if (selectedNodeId) {
                loadGraphContext(selectedNodeId);
            }
        } else {
            showToast('Import failed: ' + result.error, 'danger');
        }
    } catch (error) {
        hideSpinner();
        showToast('Error during import: ' + error.message, 'danger');
    }
}

// Readings Modal
let readingsChart = null;

async function openReadingsModal(nodeId, nodeName) {
    document.getElementById('readingsNodeName').textContent = nodeName;
    document.getElementById('readingsViewNodeId').value = nodeId;
    
    const modal = new bootstrap.Modal(document.getElementById('readingsModal'));
    modal.show();
    
    // Load readings
    await loadReadings(nodeId);
}

async function loadReadings(nodeId) {
    try {
        const response = await fetch(`/api/readings/${nodeId}?project_id=${PROJECT_ID}&limit=30`);
        const readings = await response.json();
        
        // Update table
        const tbody = document.getElementById('readingsTableBody');
        if (readings.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">No readings yet</td></tr>';
        } else {
            tbody.innerHTML = readings.map(r => `
                <tr>
                    <td>${formatDate(r.time)}</td>
                    <td>${r.value}</td>
                    <td>${r.unit}</td>
                </tr>
            `).join('');
        }
        
        // Update chart
        updateReadingsChart(readings);
        
    } catch (error) {
        showToast('Error loading readings: ' + error.message, 'danger');
    }
}

function updateReadingsChart(readings) {
    const ctx = document.getElementById('readingsChart');
    
    if (readingsChart) {
        readingsChart.destroy();
    }
    
    // Simple labels and data arrays instead of time scale
    const labels = readings.reverse().map(r => {
        const date = new Date(r.time);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    });
    const values = readings.map(r => parseFloat(r.value));
    
    readingsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Value',
                data: values,
                borderColor: getUtilityColor(),
                backgroundColor: getUtilityColor() + '33',
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

async function submitAddReading() {
    const form = document.getElementById('readingsViewForm');
    
    if (!form) {
        showToast('Form not found', 'danger');
        return;
    }
    
    const nodeId = document.getElementById('readingsViewNodeId').value;
    const value = document.getElementById('readingsViewValue').value;
    const unit = document.getElementById('readingsViewUnit').value;
    const timestamp = document.getElementById('readingsViewTimestamp').value;
    
    // Validation
    if (!nodeId) {
        showToast('Node ID not set', 'danger');
        return;
    }
    
    if (!value || value === '') {
        showToast('Please enter a reading value', 'warning');
        document.getElementById('readingsViewValue').focus();
        return;
    }
    
    const numValue = parseFloat(value);
    if (isNaN(numValue) || numValue < 0) {
        showToast('Please enter a valid positive number', 'warning');
        document.getElementById('readingsViewValue').focus();
        return;
    }
    
    if (!unit || unit === '') {
        showToast('Please select a unit', 'warning');
        document.getElementById('readingsViewUnit').focus();
        return;
    }
    
    try {
        showSpinner();
        
        const response = await fetch(`/api/readings/${nodeId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                project_id: PROJECT_ID,
                value: numValue,
                unit: unit,
                timestamp: timestamp || undefined
            })
        });
        
        hideSpinner();
        
        if (response.ok) {
            showToast('Reading added successfully', 'success');
            form.reset();
            form.classList.remove('was-validated');
            await loadReadings(nodeId);
        } else {
            const error = await response.json();
            showToast('Error adding reading: ' + error.error, 'danger');
        }
    } catch (error) {
        hideSpinner();
        showToast('Error adding reading: ' + error.message, 'danger');
    }
}
