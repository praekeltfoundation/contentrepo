document.addEventListener('DOMContentLoaded', function() {
    console.log('Template explorer script loaded');

    // Make templates and folders draggable
    document.querySelectorAll('.template-row, .folder-row').forEach(row => {
        row.addEventListener('dragstart', handleDragStart);
    });

    // Make folder titles drop targets
    document.querySelectorAll('[data-drop-target="true"]').forEach(dropTarget => {
        dropTarget.addEventListener('dragover', handleDragOver);
        dropTarget.addEventListener('drop', handleDrop);
        dropTarget.addEventListener('dragenter', handleDragEnter);
        dropTarget.addEventListener('dragleave', handleDragLeave);
    });

    // Initialize all folders
    document.querySelectorAll('.folder-row').forEach(folderRow => {
        const toggle = folderRow.querySelector('.toggle-children');
        const isCollapsed = folderRow.classList.contains('collapsed');
        
        console.log(`Initializing folder ${folderRow.dataset.folderId}, collapsed: ${isCollapsed}`);
        setChildrenVisibility(folderRow, !isCollapsed);

        // Toggle handler
        const toggleHandler = (e) => {
            if (e && e.target.closest('a')) {
                return;  // Don't toggle if clicking a link
            }
            
            const isNowCollapsed = !folderRow.classList.contains('collapsed');
            console.log(`Toggling folder ${folderRow.dataset.folderId}, new state: ${isNowCollapsed ? 'collapsed' : 'expanded'}`);
            
            folderRow.classList.toggle('collapsed');
            setChildrenVisibility(folderRow, !isNowCollapsed);
        };

        // Add click handler to the entire row
        folderRow.addEventListener('click', function(e) {
            if (!e.target.closest('a') && e.target !== toggle) {
                toggleHandler(e);
            }
        });

        if (toggle) {
            toggle.addEventListener('click', function(e) {
                e.stopPropagation();
                toggleHandler(e);
            });
        }
    });
    
    // Show all root level items
    document.querySelectorAll('tr[data-depth="0"]').forEach(row => {
        console.log(`Showing root level item: ${row.dataset.folderId || row.dataset.templateId}`);
        row.style.display = 'table-row';
    });
});

function getDirectChildren(parentRow) {
    const children = [];
    if (!parentRow) return children;
    
    const parentDepth = parseInt(parentRow.dataset.depth || '0');
    const parentId = parentRow.dataset.folderId || null;
    let nextRow = parentRow.nextElementSibling;
    
    console.log(`Getting children for folder: ${parentId} at depth ${parentDepth}`);
    
    while (nextRow) {
        const nextDepth = parseInt(nextRow.dataset.depth || '0');
        if (nextDepth <= parentDepth) break;
        
        if (nextDepth === parentDepth + 1) {
            // If this is a template, check if it belongs to this folder
            if (nextRow.classList.contains('template-row')) {
                const templateFolderId = nextRow.dataset.folderId || null;
                if ((!parentId && !templateFolderId) || (parentId === templateFolderId)) {
                    console.log(`  Found direct child template: ${nextRow.dataset.templateId}`);
                    children.push(nextRow);
                }
            } 
            // If it's a folder, it's a direct child
            else if (nextRow.classList.contains('folder-row')) {
                console.log(`  Found direct child folder: ${nextRow.dataset.folderId}`);
                children.push(nextRow);
            }
        }
        
        nextRow = nextRow.nextElementSibling;
    }
    
    console.log(`  Total direct children: ${children.length}`);
    return children;
}

function setChildrenVisibility(parentRow, isVisible) {
    const children = getDirectChildren(parentRow);
    console.log(`Setting visibility for ${children.length} children of folder ${parentRow.dataset.folderId} to ${isVisible ? 'visible' : 'hidden'}`);
    
    children.forEach(child => {
        console.log(`  ${isVisible ? 'Showing' : 'Hiding'} ${child.classList.contains('folder-row') ? 'folder' : 'template'} ${child.classList.contains('folder-row') ? child.dataset.folderId : child.dataset.templateId}`);
        child.style.display = isVisible ? '' : 'none';
        
        // If we're hiding, also hide all descendants
        if (!isVisible && child.classList.contains('folder-row')) {
            child.classList.add('collapsed');
            setChildrenVisibility(child, false);
        }
    });
}

let draggedItem = null;
let currentDropTarget = null;

function handleDragStart(e) {
    draggedItem = this;
    e.dataTransfer.effectAllowed = 'move';
    // Store both the type and ID of the dragged item
    const type = this.classList.contains('folder-row') ? 'folder' : 'template';
    const id = this.dataset.folderId || this.dataset.templateId;
    e.dataTransfer.setData('application/json', JSON.stringify({ type, id }));
    this.classList.add('dragging');
}

function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = 'move';
    
    // Remove highlight from previous target
    if (currentDropTarget && currentDropTarget !== this) {
        currentDropTarget.classList.remove('drag-over');
    }
    
    // Add highlight to current target
    if (currentDropTarget !== this) {
        this.classList.add('drag-over');
        currentDropTarget = this;
    }
    return false;
}

function handleDragEnter(e) {
    e.preventDefault();
    e.stopPropagation();
    return false;
}

function handleDragLeave(e) {
    // Only remove highlight if leaving the drop target (not just moving to a child)
    if (!this.contains(e.relatedTarget)) {
        this.classList.remove('drag-over');
        if (currentDropTarget === this) {
            currentDropTarget = null;
        }
    }
}

async function handleDrop(e) {
    e.stopPropagation();
    e.preventDefault();
    
    if (!draggedItem) return;

    // Remove highlight from all drop targets
    document.querySelectorAll('[data-drop-target]').forEach(el => {
        el.classList.remove('drag-over');
    });
    
    // Get the dragged item's data
    const dragData = JSON.parse(e.dataTransfer.getData('application/json'));
    const targetFolderId = this.closest('[data-folder-id]').dataset.folderId || null;
    
    // Prevent dropping a folder into itself or its own children
    if (dragData.type === 'folder' && targetFolderId) {
        const targetFolder = document.querySelector(`[data-folder-id="${targetFolderId}"]`);
        if (targetFolder && (targetFolder === draggedItem || targetFolder.closest(`[data-folder-id="${dragData.id}"]`))) {
            console.error('Cannot move a folder into itself or its children');
            return;
        }
    }
    
    try {
        const formData = new FormData();
        if (targetFolderId) {
            formData.append('folder', targetFolderId);
        }
        
        const endpoint = dragData.type === 'folder' 
            ? `/admin/whatsapp-template-folders/${dragData.id}/move/`
            : `/admin/whatsapp-templates/${dragData.id}/move/`;
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: formData
        });
        
        if (response.ok) {
            // Get the moved item (in case it was re-rendered)
            const movedItem = document.querySelector(`[data-${dragData.type}-id="${dragData.id}"]`);
            if (!movedItem) {
                // If the item was re-rendered, reload the page
                window.location.reload();
                return;
            }
            
            // Move the row to the new location in the DOM
            const targetContainer = this.closest('tbody');
            const targetSibling = this.closest('tr').nextSibling;
            
            // If moving a folder, we need to move all its children as well
            if (dragData.type === 'folder') {
                const folderAndChildren = [movedItem];
                let nextSibling = movedItem.nextElementSibling;
                const startDepth = parseInt(movedItem.dataset.depth);
                
                // Find all children of the moved folder
                while (nextSibling) {
                    const depth = parseInt(nextSibling.dataset.depth || '0');
                    if (depth <= startDepth) break;
                    folderAndChildren.push(nextSibling);
                    nextSibling = nextSibling.nextElementSibling;
                }
                
                // Move all elements
                folderAndChildren.reverse().forEach(el => {
                    if (targetSibling) {
                        targetContainer.insertBefore(el, targetSibling);
                    } else {
                        targetContainer.appendChild(el);
                    }
                });
            } else {
                // For templates, just move the single row
                if (targetSibling) {
                    targetContainer.insertBefore(movedItem, targetSibling);
                } else {
                    targetContainer.appendChild(movedItem);
                }
            }
            
            // Update the folder ID and depth for the moved item and its children
            const newDepth = targetFolderId ? 
                parseInt(this.closest('[data-depth]').dataset.depth) + 1 : 0;
                
            const updateDepth = (element, depth, parentFolderId) => {
                // Only update depth for the folder itself, not its children yet
                element.dataset.depth = depth;
                
                // For templates, set the folder ID to the parent folder's ID
                if (element.classList.contains('template-row')) {
                    element.dataset.folderId = parentFolderId;
                }
                
                // Update indentation
                const titleDiv = element.querySelector('.title > div');
                if (titleDiv) {
                    titleDiv.style.paddingLeft = `${depth * 20}px`;
                }
                
                // If this is a folder, update all its children
                if (element.classList.contains('folder-row')) {
                    const folderId = element.dataset.folderId;
                    const children = getDirectChildren(element);
                    children.forEach(child => {
                        // For direct children of this folder, use this folder's ID
                        updateDepth(child, depth + 1, folderId);
                    });
                }
            };
            
            // For the moved folder, use the target folder ID as parent
            updateDepth(movedItem, newDepth, targetFolderId);
            
            // If we moved a folder, update all its children's folder IDs and ensure proper ordering
            if (dragData.type === 'folder') {
                const folderId = movedItem.dataset.folderId;
                const folderChildren = [];
                let nextSibling = movedItem.nextElementSibling;
                const startDepth = parseInt(movedItem.dataset.depth);
                
                // First pass: collect all children and update their folder IDs
                while (nextSibling) {
                    const depth = parseInt(nextSibling.dataset.depth || '0');
                    if (depth <= startDepth) break;
                    
                    folderChildren.push(nextSibling);
                    if (nextSibling.classList.contains('template-row')) {
                        nextSibling.dataset.folderId = folderId;
                    }
                    nextSibling = nextSibling.nextElementSibling;
                }
                
                // Remove the folder and its children from DOM
                const targetContainer = movedItem.parentNode;
                const insertAfter = this.closest('tr').nextElementSibling;
                
                // Create a document fragment to hold the folder and its children
                const fragment = document.createDocumentFragment();
                fragment.appendChild(movedItem);
                folderChildren.forEach(child => {
                    fragment.appendChild(child);
                });
                
                // Insert the entire fragment at the target position
                if (insertAfter) {
                    targetContainer.insertBefore(fragment, insertAfter);
                } else {
                    targetContainer.appendChild(fragment);
                }
            }
            
            // Update parent folder's visibility if needed
            const parentFolderRow = this.closest('.folder-row');
            if (parentFolderRow) {
                const isExpanded = !parentFolderRow.classList.contains('collapsed');
                setChildrenVisibility(parentFolderRow, isExpanded);
            }
            
        } else {
            throw new Error(`Failed to move ${dragData.type}`);
        }
    } catch (error) {
        console.error(`Error moving ${dragData.type}:`, error);
        alert(`Error moving ${dragData.type}. Please try again.`);
    } finally {
        if (draggedItem) {
            draggedItem.classList.remove('dragging');
            draggedItem = null;
        }
        currentDropTarget = null;
    }
}

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}