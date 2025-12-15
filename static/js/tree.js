/**
 * Tree View functionality
 */

let treeCache = {};
let selectedNodeId = null;

async function initializeTreeView() {
    try {
        const treeView = document.getElementById('treeView');
        treeView.innerHTML = '';
        
        const response = await fetch(`/api/graph/tree?project_id=${PROJECT_ID}`);
        const nodes = await response.json();
        renderTree(nodes, treeView);
    } catch (error) {
        showToast('Error loading tree: ' + error.message, 'danger');
    }
}

/**
 * Create a tree node DOM element
 * @param {Object} node - Node data
 * @returns {HTMLElement} - LI element with tree node
 */
function createTreeNodeElement(node) {
    const nodeType = getNodeType(node.labels);
    const li = document.createElement('li');
    li.dataset.nodeId = node.id;
    li.dataset.nodeType = nodeType;
    
    const nodeDiv = document.createElement('div');
    nodeDiv.className = 'tree-node';
    if (selectedNodeId === node.id) {
        nodeDiv.classList.add('active');
    }
    
    // Expand arrow
    const arrow = document.createElement('span');
    arrow.className = 'expand-arrow';
    if (node.has_children) {
        arrow.textContent = '▶';
        arrow.onclick = (e) => {
            e.stopPropagation();
            toggleNode(node.id, li);
        };
    } else {
        arrow.style.visibility = 'hidden';
    }
    
    // Node icon and name
    const icon = document.createElement('span');
    icon.innerHTML = getNodeIcon(nodeType, node.utility_type);
    
    const name = document.createElement('span');
    name.textContent = node.name;
    name.className = 'flex-grow-1';
    
    nodeDiv.append(arrow, icon, name);
    nodeDiv.onclick = () => selectNode(node.id, node.name);
    
    li.appendChild(nodeDiv);
    return { li, arrow };
}

function renderTree(nodes, container, level = 0) {
    if (!nodes || nodes.length === 0) {
        if (level === 0) {
            container.innerHTML = '<li class="text-muted small">No nodes yet</li>';
        }
        return;
    }
    
    nodes.forEach(node => {
        const { li } = createTreeNodeElement(node);
        container.appendChild(li);
    });
}

async function toggleNode(nodeId, liElement) {
    const arrow = liElement.querySelector('.expand-arrow');
    const isExpanded = arrow.classList.contains('expanded');
    
    if (isExpanded) {
        // Collapse
        const childUl = liElement.querySelector('ul');
        if (childUl) {
            childUl.remove();
        }
        arrow.classList.remove('expanded');
    } else {
        // Expand
        arrow.classList.add('expanded');
        
        // Check cache
        if (treeCache[nodeId]) {
            const ul = document.createElement('ul');
            renderTree(treeCache[nodeId], ul, 1);
            liElement.appendChild(ul);
        } else {
            // Load from API
            try {
                const response = await fetch(`/api/graph/tree?project_id=${PROJECT_ID}&parent_id=${nodeId}`);
                const children = await response.json();
                treeCache[nodeId] = children;
                
                const ul = document.createElement('ul');
                renderTree(children, ul, 1);
                liElement.appendChild(ul);
            } catch (error) {
                showToast('Error loading children: ' + error.message, 'danger');
            }
        }
    }
}

function selectNode(nodeId, nodeName) {
    selectedNodeId = nodeId;
    
    // Update UI
    document.querySelectorAll('.tree-node').forEach(el => {
        el.classList.remove('active');
    });
    const selectedDiv = document.querySelector(`[data-node-id="${nodeId}"] .tree-node`);
    if (selectedDiv) {
        selectedDiv.classList.add('active');
    }
    
    // Update breadcrumb (simplified)
    updateBreadcrumb(nodeName);
    
    // Load graph context
    if (typeof loadGraphContext === 'function') {
        loadGraphContext(nodeId);
    }
}

function updateBreadcrumb(nodeName) {
    const breadcrumb = document.getElementById('breadcrumb');
    breadcrumb.innerHTML = `
        <li class="breadcrumb-item"><a href="#" onclick="event.preventDefault(); selectedNodeId = null; initializeTreeView();">Root</a></li>
        <li class="breadcrumb-item active">${nodeName}</li>
    `;
}

// Search functionality
function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    const dropdown = document.getElementById('autocompleteDropdown');
    
    if (!searchInput || !dropdown) return;
    
    searchInput.addEventListener('input', debounce(async function(e) {
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            dropdown.style.display = 'none';
            return;
        }
        
        try {
            const response = await fetch(`/api/graph/search?project_id=${PROJECT_ID}&q=${encodeURIComponent(query)}`);
            const results = await response.json();
            
            if (results.length === 0) {
                dropdown.innerHTML = '<div class="autocomplete-item text-muted">No results found</div>';
            } else {
                dropdown.innerHTML = results.map(node => {
                    const type = getNodeType(node.labels);
                    const category = node.category || node.subtype || '';
                    // Escape special characters in name for safe onclick attribute
                    const safeName = (node.name || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
                    return `
                        <div class="autocomplete-item" onclick="selectSearchResult('${node.id}', '${safeName}')">
                            ${getNodeIcon(type)}
                            <strong>${node.name}</strong>
                            <small class="text-muted d-block">${type}${category ? ' - ' + category : ''}</small>
                        </div>
                    `;
                }).join('');
            }
            
            dropdown.style.display = 'block';
        } catch (error) {
            showToast('Search error: ' + error.message, 'danger');
        }
    }, 300));
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
}

function selectSearchResult(nodeId, nodeName) {
    document.getElementById('autocompleteDropdown').style.display = 'none';
    document.getElementById('searchInput').value = '';
    selectNode(nodeId, nodeName);
}

/**
 * Search and expand all nodes of a specific Consumer category
 * @param {string} categoryName - Category to search for
 */
async function searchAndExpandCategory(categoryName) {
    try {
        showSpinner();
        
        // Search for all nodes with this category using API
        const response = await fetch(`/api/graph/search?project_id=${PROJECT_ID}&q=&category=${encodeURIComponent(categoryName)}`);
        const results = await response.json();
        
        if (results.length === 0) {
            hideSpinner();
            showToast(`No ${categoryName} nodes found in project`, 'info');
            return;
        }
        
        // Clear tree and rebuild with expanded paths
        const treeView = document.getElementById('treeView');
        treeView.innerHTML = '';
        
        // Get all node IDs to expand
        const nodeIds = results.map(n => n.id);
        
        // Reload tree and expand paths to matching nodes
        await expandTreeToNodes(nodeIds);
        
        // Highlight matching nodes in tree
        highlightTreeNodes(nodeIds);
        
        // Load graph showing all found nodes
        if (typeof loadCategoryNodesOnGraph === 'function') {
            await loadCategoryNodesOnGraph(results, categoryName);
        }
        
        hideSpinner();
        showToast(`Found and expanded ${results.length} ${categoryName} node(s)`, 'success');
        
    } catch (error) {
        hideSpinner();
        showToast('Error searching category: ' + error.message, 'danger');
    }
}

/**
 * Expand tree to show specific nodes
 * @param {Array} nodeIds - Array of node IDs to expand to
 */
async function expandTreeToNodes(nodeIds) {
    // First, get paths for all target nodes
    const pathsResponse = await fetch(`/api/graph/paths?project_id=${PROJECT_ID}&node_ids=${nodeIds.join(',')}`);
    const pathsData = await pathsResponse.json();
    
    // Collect all ancestor IDs that need to be expanded
    const ancestorIds = new Set();
    pathsData.forEach(path => {
        if (path.ancestors) {
            path.ancestors.forEach(a => ancestorIds.add(a.id));
        }
    });
    
    // Reload tree from root
    const response = await fetch(`/api/graph/tree?project_id=${PROJECT_ID}`);
    const nodes = await response.json();
    
    const treeView = document.getElementById('treeView');
    treeView.innerHTML = '';
    
    // Render tree with auto-expansion
    await renderTreeWithExpansion(nodes, treeView, 0, ancestorIds, new Set(nodeIds));
}

/**
 * Render tree and automatically expand nodes in ancestorIds
 */
async function renderTreeWithExpansion(nodes, container, level, ancestorIds, targetIds) {
    if (!nodes || nodes.length === 0) return;
    
    for (const node of nodes) {
        const { li, arrow } = createTreeNodeElement(node);
        container.appendChild(li);
        
        // Auto-expand if this node is an ancestor of target nodes
        if (ancestorIds.has(node.id) && node.has_children) {
            arrow.textContent = '▼';
            arrow.classList.add('expanded');
            
            const childrenResponse = await fetch(`/api/graph/tree?project_id=${PROJECT_ID}&parent_id=${node.id}`);
            const children = await childrenResponse.json();
            
            const ul = document.createElement('ul');
            ul.className = 'tree-children';
            await renderTreeWithExpansion(children, ul, level + 1, ancestorIds, targetIds);
            li.appendChild(ul);
            
            treeCache[node.id] = children;
        }
    }
}

/**
 * Highlight specific nodes in the tree view
 * @param {Array} nodeIds - Array of node IDs to highlight
 */
function highlightTreeNodes(nodeIds) {
    // Remove previous highlights
    document.querySelectorAll('.tree-node.category-match').forEach(el => {
        el.classList.remove('category-match');
    });
    
    // Add highlight to matching nodes
    nodeIds.forEach(nodeId => {
        const li = document.querySelector(`li[data-node-id="${nodeId}"]`);
        if (li) {
            const nodeDiv = li.querySelector('.tree-node');
            if (nodeDiv) {
                nodeDiv.classList.add('category-match');
            }
        }
    });
    
    // Scroll to first match
    const firstMatch = document.querySelector('.tree-node.category-match');
    if (firstMatch) {
        firstMatch.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// Filters functionality
function initializeFilters() {
    const checkboxes = document.querySelectorAll('.filter-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', applyFilters);
    });
}

function applyFilters() {
    const activeFilters = Array.from(document.querySelectorAll('.filter-checkbox:checked'))
        .map(cb => cb.value);
    
    document.querySelectorAll('.tree-node').forEach(nodeDiv => {
        const li = nodeDiv.parentElement;
        const nodeType = li.dataset.nodeType;
        
        if (activeFilters.includes(nodeType) || !nodeType) {
            nodeDiv.classList.remove('dimmed');
            nodeDiv.classList.add('highlighted');
        } else {
            nodeDiv.classList.remove('highlighted');
            nodeDiv.classList.add('dimmed');
        }
    });
}
