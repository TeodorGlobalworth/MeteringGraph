/**
 * Graph visualization with Cytoscape.js
 */

let cy = null;
let loadedNodes = new Set();
let currentUtilityFilter = 'all';  // all, electricity, water, heating
let sidebarCollapsed = false;

/**
 * Update sidebar toggle position based on tree panel width
 */
function updateTogglePosition() {
    const treePanel = document.getElementById('treePanel');
    const toggleBtn = document.getElementById('sidebarToggle');
    
    if (!treePanel || !toggleBtn) return;
    
    if (sidebarCollapsed) {
        toggleBtn.style.left = '0';
    } else {
        const panelWidth = treePanel.offsetWidth;
        toggleBtn.style.left = panelWidth + 'px';
    }
}

/**
 * Toggle sidebar visibility
 */
function toggleSidebar() {
    const treePanel = document.getElementById('treePanel');
    const toggleBtn = document.getElementById('sidebarToggle');
    
    sidebarCollapsed = !sidebarCollapsed;
    
    if (sidebarCollapsed) {
        treePanel.classList.add('collapsed');
        toggleBtn.classList.add('collapsed');
    } else {
        treePanel.classList.remove('collapsed');
        toggleBtn.classList.remove('collapsed');
    }
    
    // Update toggle position
    updateTogglePosition();
    
    // Resize graph after sidebar animation
    setTimeout(() => {
        if (cy) {
            cy.resize();
            cy.fit(50);
        }
        // Update position after animation completes
        updateTogglePosition();
    }, 350);
}

/**
 * Get utility type color
 * @param {string} utility - Utility type
 * @returns {string} - Color code for utility type
 */
function getUtilityColorByType(utility) {
    const colors = {
        'electricity': '#ffc107',
        'water': '#0dcaf0',
        'heating': '#dc3545',
        'gas': '#fd7e14',
        'multi': '#6c757d',
        'consumer': '#e0e0e0'
    };
    return colors[utility] || '#999';
}

const BOOTSTRAP_ICONS_CDN = 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/icons';
const DEFAULT_CATEGORY = { color: '#4a5568', icon_name: 'box-fill' };
const METER_ICON = 'speedometer2';
const DISTRIBUTION_ICON = 'diagram-3';

/**
 * Find category config by name from cached categories
 */
function getCategoryConfig(categoryName) {
    return window.consumerCategories?.find(c => c.category_name === categoryName) || DEFAULT_CATEGORY;
}

/**
 * Get consumer category color
 */
function getConsumerCategoryColor(category) {
    return getCategoryConfig(category).color;
}

/**
 * Get consumer category icon URL
 */
function getConsumerCategoryIcon(category) {
    const iconName = getCategoryConfig(category).icon_name;
    return `url(${BOOTSTRAP_ICONS_CDN}/${iconName}.svg)`;
}

/**
 * Load consumer categories from API and cache them
 */
async function loadConsumerCategories() {
    try {
        const response = await fetch('/api/settings/consumer-categories');
        window.consumerCategories = await response.json();
        return window.consumerCategories;
    } catch (error) {
        console.error('Failed to load consumer categories:', error);
        window.consumerCategories = [];
        return [];
    }
}

function getUtilityColor() {
    return getUtilityColorByType(UTILITY_TYPE || 'electricity');
}

async function initializeGraph() {
    // Load consumer categories first
    await loadConsumerCategories();
    
    // Populate category legend from loaded data
    populateCategoryLegend();
    
    // Initialize Cytoscape
    cy = cytoscape({
        container: document.getElementById('cy'),
        
        style: [
            // Node styles
            {
                selector: 'node',
                style: {
                    'label': 'data(name)',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'font-size': '12px',
                    'width': '60px',
                    'height': '60px',
                    'background-color': '#4a5568',
                    'background-opacity': 1,
                    'border-width': 2,
                    'border-color': '#718096',
                    'color': '#ffffff',
                    'text-wrap': 'wrap',
                    'text-max-width': '80px',
                    'text-outline-color': '#000000',
                    'text-outline-width': 2
                }
            },
            
            // Meter nodes - color by utility with meter icon
            {
                selector: 'node[type="Meter"]',
                style: {
                    'shape': 'round-rectangle',
                    'background-color': function(ele) {
                        return getUtilityColorByType(ele.data('fullData')?.utility_type || 'electricity');
                    },
                    'background-image': `${BOOTSTRAP_ICONS_CDN}/${METER_ICON}.svg`,
                    'background-fit': 'contain',
                    'background-clip': 'none',
                    'background-width': '60%',
                    'background-height': '60%',
                    'color': '#ffffff'
                }
            },
            
            // Distribution nodes - color by utility with distribution icon
            {
                selector: 'node[type="Distribution"]',
                style: {
                    'shape': 'diamond',
                    'background-color': function(ele) {
                        return getUtilityColorByType(ele.data('fullData')?.utility_type || 'electricity');
                    },
                    'background-image': `${BOOTSTRAP_ICONS_CDN}/${DISTRIBUTION_ICON}.svg`,
                    'background-fit': 'contain',
                    'background-clip': 'none',
                    'background-width': '55%',
                    'background-height': '55%',
                    'color': '#ffffff'
                }
            },
            
            // Consumer nodes - different colors/shapes by category
            {
                selector: 'node[type="Consumer"]',
                style: {
                    'shape': 'round-rectangle',
                    'background-color': function(ele) {
                        return getConsumerCategoryColor(ele.data('fullData')?.category);
                    },
                    'background-image': function(ele) {
                        return getConsumerCategoryIcon(ele.data('fullData')?.category);
                    },
                    'background-fit': 'contain',
                    'background-clip': 'none',
                    'background-width': '60%',
                    'background-height': '60%',
                    'border-color': '#718096',
                    'border-width': 2,
                    'color': '#ffffff',
                    'text-margin-y': 5
                }
            },
            
            // Root node - color by utility
            {
                selector: 'node[type="MeteringTree"]',
                style: {
                    'shape': 'round-rectangle',
                    'background-color': function(ele) {
                        return getUtilityColorByType(ele.data('fullData')?.utility_type || 'electricity');
                    },
                    'width': '80px',
                    'height': '80px',
                    'font-weight': 'bold',
                    'color': '#ffffff'
                }
            },
            
            // Current/selected node
            {
                selector: 'node.current',
                style: {
                    'border-width': 4,
                    'border-color': '#4dabf7'
                }
            },
            
            // Ancestor nodes (subtle border change instead of dimming)
            {
                selector: 'node.ancestor',
                style: {
                    'border-color': '#4a5568',
                    'border-width': 1
                }
            },
            
            // Expanded nodes (subtle border change instead of dimming)
            {
                selector: 'node.expanded',
                style: {
                    'border-color': '#718096',
                    'border-width': 2
                }
            },
            
            // Category highlight (when clicking legend)
            {
                selector: 'node.category-highlight',
                style: {
                    'border-width': 5,
                    'border-color': '#ffd43b',
                    'border-style': 'double',
                    'z-index': 999
                }
            },
            
            // Edge styles
            {
                selector: 'edge',
                style: {
                    'width': 2,
                    'line-color': '#4a5568',
                    'target-arrow-color': '#4a5568',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'arrow-scale': 1.5
                }
            },
            
            // Selected edge
            {
                selector: 'edge:selected',
                style: {
                    'line-color': '#4dabf7',
                    'target-arrow-color': '#4dabf7',
                    'width': 3
                }
            }
        ],
        
        layout: {
            name: 'dagre',
            rankDir: 'TB',
            nodeSep: 50,
            rankSep: 100,
            animate: true,
            animationDuration: 500
        },
        
        minZoom: 0.3,
        maxZoom: 2,
        wheelSensitivity: 0.2
    });
    
    // Setup custom context menu
    setupCustomContextMenu();
    
    // Event handlers
    cy.on('tap', 'node', function(event) {
        const node = event.target;
        highlightNode(node);
    });
    
    cy.on('dbltap', 'node', function(event) {
        const node = event.target;
        expandNode(node.id());
    });
    
    // Edge click - insert node between
    cy.on('tap', 'edge', function(event) {
        const edge = event.target;
        const sourceId = edge.source().id();
        const targetId = edge.target().id();
        
        if (confirm('Insert node between these two nodes?')) {
            insertNodeBetween(sourceId, targetId);
        }
    });
    
    // Utility filter listener
    const utilityFilter = document.getElementById('utilityFilter');
    if (utilityFilter) {
        utilityFilter.addEventListener('change', function() {
            applyUtilityFilter(this.value);
        });
    }
    
    // Load initial view (root)
    loadRootContext();
}

// Custom Context Menu
let contextMenuNode = null;

function setupCustomContextMenu() {
    const menu = document.getElementById('customContextMenu');
    
    // Right click on nodes
    cy.on('cxttap', 'node', function(event) {
        event.preventDefault();
        const node = event.target;
        contextMenuNode = node;
        
        // Position menu at cursor
        const renderedPos = event.renderedPosition || event.cyRenderedPosition;
        menu.style.left = renderedPos.x + 'px';
        menu.style.top = renderedPos.y + 'px';
        menu.classList.add('show');
    });
    
    // Hide menu on click elsewhere
    document.addEventListener('click', function() {
        menu.classList.remove('show');
    });
    
    cy.on('tap', function() {
        menu.classList.remove('show');
    });
    
    // Menu item handlers
    document.getElementById('contextExpand').onclick = function() {
        if (contextMenuNode) {
            expandNode(contextMenuNode.id());
        }
        menu.classList.remove('show');
    };
    
    document.getElementById('contextAddChild').onclick = function() {
        if (contextMenuNode) {
            openAddNodeModal(contextMenuNode.id(), contextMenuNode.data('name'));
        }
        menu.classList.remove('show');
    };
    
    document.getElementById('contextConnect').onclick = async function() {
        if (contextMenuNode) {
            menu.classList.remove('show');
            openConnectionModal(contextMenuNode.id(), contextMenuNode.data('name'));
        }
    };
    
    document.getElementById('contextEdit').onclick = function() {
        if (contextMenuNode) {
            openEditNodeModal(contextMenuNode.id());
        }
        menu.classList.remove('show');
    };
    
    document.getElementById('contextViewDetails').onclick = function() {
        if (contextMenuNode) {
            openViewDetailsModal(contextMenuNode.id());
        }
        menu.classList.remove('show');
    };
    
    document.getElementById('contextReadings').onclick = function() {
        if (contextMenuNode) {
            openReadingsModal(contextMenuNode.id(), contextMenuNode.data('name'));
        }
        menu.classList.remove('show');
    };
    
    document.getElementById('contextDelete').onclick = function() {
        if (contextMenuNode) {
            deleteNode(contextMenuNode.id(), contextMenuNode.data('name'));
        }
        menu.classList.remove('show');
    };
    
    // Connection modal search handler
    const connectionSearchInput = document.getElementById('connectionSearchInput');
    if (connectionSearchInput) {
        connectionSearchInput.addEventListener('input', function() {
            clearTimeout(connectionSearchTimeout);
            connectionSearchTimeout = setTimeout(() => {
                searchNodesForConnection(this.value.trim());
            }, 300);
        });
    }
    
    // Connection modal create button handler
    const btnCreateConnection = document.getElementById('btnCreateConnection');
    if (btnCreateConnection) {
        btnCreateConnection.addEventListener('click', async function() {
            const sourceId = document.getElementById('connectionSourceId').value;
            if (sourceId && selectedTargetId) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('addConnectionModal'));
                modal.hide();
                await createConnectionBetweenNodes(sourceId, selectedTargetId);
            }
        });
    }
}

async function loadRootContext() {
    try {
        // Load all 3 utility roots
        const response = await fetch(`/api/graph/utility-roots/${PROJECT_ID}`);
        const roots = await response.json();
        
        if (roots && roots.length > 0) {
            // Clear graph
            cy.elements().remove();
            loadedNodes.clear();
            
            // Load context for each root
            for (const root of roots) {
                await loadGraphContext(root.id, false);  // false = don't clear graph
            }
            
            // Re-layout after all loaded
            cy.layout({
                name: 'dagre',
                rankDir: 'TB',
                nodeSep: 50,
                rankSep: 100,
                animate: true
            }).run();
        } else {
            showToast('No utility roots found. Please create a project first.', 'warning');
        }
    } catch (error) {
        showToast('Error loading graph: ' + error.message, 'danger');
    }
}

async function loadGraphContext(nodeId, clearGraph = true) {
    try {
        showSpinner();
        
        const response = await fetch(`/api/graph/context/${nodeId}?project_id=${PROJECT_ID}&depth=1`);
        const data = await response.json();
        
        // Clear existing graph if requested
        if (clearGraph) {
            cy.elements().remove();
            loadedNodes.clear();
        }
        
        // Add nodes
        data.nodes.forEach(node => {
            if (loadedNodes.has(node.id)) return;  // Skip if already loaded
            
            const nodeType = getNodeType(node.labels);
            const classes = [];
            
            if (node.is_current) {
                classes.push('current');
            }
            if (node.id !== nodeId) {
                classes.push('ancestor');
            }
            
            cy.add({
                group: 'nodes',
                data: {
                    id: node.id,
                    name: truncateText(node.name, 30),
                    type: nodeType,
                    category: node.category || '',  // For Consumer category-based styling
                    fullData: node
                },
                classes: classes.join(' ')
            });
            
            loadedNodes.add(node.id);
        });
        
        // Add edges
        data.relationships.forEach(rel => {
            const edgeId = `${rel.start_node}-${rel.end_node}`;
            if (loadedNodes.has(rel.start_node) && loadedNodes.has(rel.end_node) && !cy.getElementById(edgeId).length) {
                cy.add({
                    group: 'edges',
                    data: {
                        id: edgeId,
                        source: rel.start_node,
                        target: rel.end_node,
                        type: rel.type
                    }
                });
            }
        });
        
        // Apply layout
        cy.layout({
            name: 'dagre',
            rankDir: 'TB',
            nodeSep: 50,
            rankSep: 100,
            animate: true
        }).run();
        
        hideSpinner();
        
    } catch (error) {
        hideSpinner();
        showToast('Error loading context: ' + error.message, 'danger');
    }
}

async function expandNode(nodeId) {
    try {
        const response = await fetch(`/api/graph/expand/${nodeId}?project_id=${PROJECT_ID}`);
        const data = await response.json();
        
        // Add new nodes
        data.nodes.forEach(node => {
            if (!loadedNodes.has(node.id)) {
                const nodeType = getNodeType(node.labels);
                
                cy.add({
                    group: 'nodes',
                    data: {
                        id: node.id,
                        name: truncateText(node.name, 30),
                        type: nodeType,
                        category: node.category || '',  // For Consumer category-based styling
                        fullData: node
                    },
                    classes: 'expanded'
                });
                
                loadedNodes.add(node.id);
            }
        });
        
        // Add new edges
        data.relationships.forEach(rel => {
            const edgeId = `${rel.start_node}-${rel.end_node}`;
            if (!cy.getElementById(edgeId).length && loadedNodes.has(rel.start_node) && loadedNodes.has(rel.end_node)) {
                cy.add({
                    group: 'edges',
                    data: {
                        id: edgeId,
                        source: rel.start_node,
                        target: rel.end_node,
                        type: rel.type
                    }
                });
            }
        });
        
        // Re-layout
        cy.layout({
            name: 'dagre',
            rankDir: 'TB',
            nodeSep: 50,
            rankSep: 100,
            animate: true
        }).run();
        
        showToast('Node expanded', 'info');
        
    } catch (error) {
        showToast('Error expanding node: ' + error.message, 'danger');
    }
}

function highlightNode(node) {
    cy.nodes().removeClass('current');
    node.addClass('current');
}

function resetGraphView() {
    if (selectedNodeId) {
        loadGraphContext(selectedNodeId);
    } else {
        loadRootContext();
    }
}

function fitGraph() {
    cy.fit(null, 50);
}

function zoomIn() {
    cy.zoom(cy.zoom() * 1.2);
    cy.center();
}

function zoomOut() {
    cy.zoom(cy.zoom() * 0.8);
    cy.center();
}

async function deleteNode(nodeId, nodeName) {
    if (!confirm(`Are you sure you want to delete "${nodeName}"? This will also delete all connected child nodes.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/nodes/${nodeId}?project_id=${PROJECT_ID}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showToast('Node deleted successfully', 'success');
            // Refresh view
            if (selectedNodeId === nodeId) {
                selectedNodeId = null;
                loadRootContext();
            } else {
                loadGraphContext(selectedNodeId);
            }
            initializeTreeView();
        } else {
            const error = await response.json();
            showToast('Error deleting node: ' + error.error, 'danger');
        }
    } catch (error) {
        showToast('Error deleting node: ' + error.message, 'danger');
    }
}

// Utility filter
function applyUtilityFilter(utility) {
    currentUtilityFilter = utility;
    
    if (utility === 'all') {
        // Show all nodes
        cy.nodes().style('display', 'element');
        cy.edges().style('display', 'element');
    } else {
        // Hide nodes not matching utility (except Consumers)
        cy.nodes().forEach(node => {
            const nodeUtility = node.data('fullData')?.utility_type;
            const nodeType = node.data('type');
            
            if (nodeType === 'Consumer') {
                // Check if consumer has any meter of this utility
                const connectedMeters = node.connectedEdges().connectedNodes().filter(n => {
                    return n.data('type') === 'Meter' && n.data('fullData')?.utility_type === utility;
                });
                node.style('display', connectedMeters.length > 0 ? 'element' : 'none');
            } else {
                node.style('display', nodeUtility === utility ? 'element' : 'none');
            }
        });
        
        // Show only edges between visible nodes
        cy.edges().forEach(edge => {
            const sourceVisible = edge.source().style('display') === 'element';
            const targetVisible = edge.target().style('display') === 'element';
            edge.style('display', sourceVisible && targetVisible ? 'element' : 'none');
        });
    }
    
    cy.layout({name: 'dagre', rankDir: 'TB', nodeSep: 50, rankSep: 100, animate: true}).run();
}

// Insert node between
async function insertNodeBetween(sourceId, targetId) {
    const nodeName = prompt('Enter name for new node:');
    if (!nodeName) return;
    
    const nodeType = prompt('Enter node type (Meter/Distribution/Building):', 'Distribution');
    if (!nodeType) return;
    
    try {
        showSpinner();
        
        const response = await fetch('/api/graph/insert-between', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                project_id: PROJECT_ID,
                source_id: sourceId,
                target_id: targetId,
                node_type: nodeType,
                properties: {
                    name: nodeName,
                    utility_type: currentUtilityFilter !== 'all' ? currentUtilityFilter : 'electricity'
                }
            })
        });
        
        hideSpinner();
        
        if (response.ok) {
            showToast('Node inserted successfully', 'success');
            loadGraphContext(selectedNodeId);
        } else {
            const error = await response.json();
            showToast('Error inserting node: ' + error.error, 'danger');
        }
    } catch (error) {
        hideSpinner();
        showToast('Error inserting node: ' + error.message, 'danger');
    }
}

// Connection Modal functionality
let connectionSearchTimeout = null;
let selectedTargetId = null;

function openConnectionModal(sourceId, sourceName) {
    document.getElementById('connectionSourceId').value = sourceId;
    document.getElementById('connectionSourceName').value = sourceName;
    document.getElementById('connectionSearchInput').value = '';
    document.getElementById('connectionSearchResults').innerHTML = '';
    clearConnectionTarget();
    
    const modal = new bootstrap.Modal(document.getElementById('addConnectionModal'));
    modal.show();
    
    // Focus search input after modal opens
    document.getElementById('addConnectionModal').addEventListener('shown.bs.modal', function() {
        document.getElementById('connectionSearchInput').focus();
    }, { once: true });
}

function clearConnectionTarget() {
    selectedTargetId = null;
    document.getElementById('connectionTargetInfo').classList.add('d-none');
    document.getElementById('btnCreateConnection').disabled = true;
}

function selectConnectionTarget(node) {
    selectedTargetId = node.id;
    document.getElementById('connectionTargetName').textContent = node.name;
    document.getElementById('connectionTargetType').textContent = node.labels.filter(l => l !== 'MeteringTree').join(', ');
    document.getElementById('connectionTargetId').textContent = node.id;
    document.getElementById('connectionTargetInfo').classList.remove('d-none');
    document.getElementById('btnCreateConnection').disabled = false;
    document.getElementById('connectionSearchResults').innerHTML = '';
    document.getElementById('connectionSearchInput').value = '';
}

async function searchNodesForConnection(query) {
    if (query.length < 2) {
        document.getElementById('connectionSearchResults').innerHTML = '<div class="list-group-item text-muted">Type at least 2 characters...</div>';
        return;
    }
    
    try {
        const response = await fetch(`/api/graph/search-global?q=${encodeURIComponent(query)}`);
        const nodes = await response.json();
        
        const resultsContainer = document.getElementById('connectionSearchResults');
        const sourceId = document.getElementById('connectionSourceId').value;
        
        // Filter out the source node
        const filteredNodes = nodes.filter(n => n.id !== sourceId);
        
        if (filteredNodes.length === 0) {
            resultsContainer.innerHTML = '<div class="list-group-item text-muted">No nodes found</div>';
            return;
        }
        
        resultsContainer.innerHTML = filteredNodes.map(renderConnectionSearchResult).join('');
    } catch (error) {
        document.getElementById('connectionSearchResults').innerHTML = 
            `<div class="list-group-item text-danger">Error searching: ${error.message}</div>`;
    }
}

/**
 * Render a single search result item for connection modal
 * @param {Object} node - Node data
 * @returns {string} - HTML string for list item
 */
function renderConnectionSearchResult(node) {
    const nodeType = node.labels.filter(l => l !== 'MeteringTree').join(', ');
    const utilityType = node.utility_type || '';
    const serialNumber = node.serial_number ? `SN: ${node.serial_number}` : '';
    const description = node.description ? node.description.substring(0, 50) + '...' : '';
    
    return `
        <button type="button" class="list-group-item list-group-item-action" 
                onclick='selectConnectionTarget(${JSON.stringify(node).replace(/'/g, "&#39;")})'>
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <strong>${node.name}</strong>
                    <span class="badge bg-secondary ms-2">${nodeType}</span>
                    ${utilityType ? `<span class="badge bg-info ms-1">${utilityType}</span>` : ''}
                </div>
            </div>
            <small class="text-muted">
                ${serialNumber ? serialNumber + ' | ' : ''}${description}
            </small>
        </button>
    `;
}

// Create connection between nodes
async function createConnectionBetweenNodes(sourceId, targetId) {
    try {
        showSpinner();
        
        const response = await fetch('/api/graph/connect', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                source_id: sourceId,
                target_id: targetId
            })
        });
        
        hideSpinner();
        
        if (response.ok) {
            showToast('Connection created successfully', 'success');
            loadGraphContext(selectedNodeId);
        } else {
            const error = await response.json();
            showToast('Error creating connection: ' + error.error, 'danger');
        }
    } catch (error) {
        hideSpinner();
        showToast('Error creating connection: ' + error.message, 'danger');
    }
}

/**
 * Populate the category legend dynamically from cached categories
 */
function populateCategoryLegend() {
    const legendGrid = document.getElementById('categoryLegend');
    if (!legendGrid || !window.consumerCategories) return;
    
    legendGrid.innerHTML = '';
    
    window.consumerCategories.filter(cat => cat.is_active).forEach(cat => {
        const item = document.createElement('div');
        item.className = 'legend-item clickable';
        item.setAttribute('data-category', cat.category_name);
        item.innerHTML = `<span class="legend-color" style="background: ${cat.color};">` +
                         `<i class="bi bi-${cat.icon_name}"></i></span> ${cat.display_name}`;
        
        // Add click handler to highlight nodes of this category
        item.addEventListener('click', () => highlightCategoryNodes(cat.category_name));
        
        legendGrid.appendChild(item);
    });
}

/**
 * Highlight all Consumer nodes of a specific category
 * Searches entire project (not just current view) and expands tree to show them
 * @param {string} categoryName - Category to highlight
 */
function highlightCategoryNodes(categoryName) {
    // Call tree.js function to search and expand
    if (typeof searchAndExpandCategory === 'function') {
        searchAndExpandCategory(categoryName);
    }
}

/**
 * Load tree structure showing paths to all nodes of a category
 * Shows: root -> ... -> parent -> category_node for each found node
 * @param {Array} nodes - Array of node objects from search (to highlight)
 * @param {string} categoryName - Category name for display
 */
async function loadCategoryNodesOnGraph(nodes, categoryName) {
    if (!cy || nodes.length === 0) return;
    
    const nodeIdsToHighlight = new Set(nodes.map(n => n.id));
    
    try {
        // Get paths to all category nodes (includes all ancestors)
        const nodeIds = nodes.map(n => n.id).join(',');
        const response = await fetch(`/api/graph/category-tree?project_id=${PROJECT_ID}&node_ids=${nodeIds}`);
        const data = await response.json();
        
        // Clear current graph
        cy.elements().remove();
        
        // Add all nodes from the paths
        if (data.nodes) {
            data.nodes.forEach(n => {
                const nodeType = getNodeType(n.labels);
                cy.add({
                    group: 'nodes',
                    data: {
                        id: n.id,
                        name: n.name || n.id,
                        type: nodeType,
                        fullData: n
                    }
                });
            });
        }
        
        // Add all edges
        if (data.relationships) {
            data.relationships.forEach(rel => {
                cy.add({
                    group: 'edges',
                    data: {
                        id: `${rel.start}-${rel.end}`,
                        source: rel.start,
                        target: rel.end,
                        type: rel.type
                    }
                });
            });
        }
        
        // Highlight the category nodes
        const matchingNodes = cy.nodes().filter(node => nodeIdsToHighlight.has(node.id()));
        matchingNodes.addClass('category-highlight');
        
        // Apply layout
        cy.layout({
            name: 'dagre',
            rankDir: 'TB',
            nodeSep: 40,
            rankSep: 60,
            animate: false
        }).run();
        
        // Fit to view all
        cy.fit(50);
        
        // Remove highlight after delay
        setTimeout(() => {
            matchingNodes.removeClass('category-highlight');
        }, 5000);
        
    } catch (error) {
        console.error('Error loading category tree:', error);
        showToast('Error loading graph: ' + error.message, 'danger');
    }
}
