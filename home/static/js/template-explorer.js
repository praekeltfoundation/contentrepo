document.addEventListener('DOMContentLoaded', function() {
    console.log('Template explorer script loaded');

    // Make templates draggable
    document.querySelectorAll('.template-row').forEach(row => {
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

// Function to get all direct children of a row
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
        
        // For direct children (depth + 1)
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

// Function to set visibility of all children
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
    e.dataTransfer.setData('text/plain', this.dataset.templateId);
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
    
    const templateId = draggedItem.dataset.templateId;
    const targetFolderId = this.closest('[data-folder-id]').dataset.folderId || null;
    
    try {
        const formData = new FormData();
        if (targetFolderId) {
            formData.append('folder', targetFolderId);
        }
        
        const response = await fetch(`/admin/whatsapp-templates/${templateId}/move/`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: formData
        });
        
        if (response.ok) {
            // Update the UI to reflect the move
            const templateRow = document.querySelector(`[data-template-id="${templateId}"]`);
            if (templateRow) {
                // Move the row to the new location in the DOM
                const targetContainer = this.closest('tbody');
                targetContainer.insertBefore(templateRow, this.closest('tr').nextSibling);
                
                // Update the folder ID
                draggedItem.dataset.folderId = targetFolderId;

                // Calculate new depth (parent folder's depth + 1, or 0 if no folder)
                const newDepth = currentDropTarget.closest('tr').dataset.depth ? 
                    parseInt(currentDropTarget.closest('tr').dataset.depth) + 1 : 0;
                draggedItem.dataset.depth = newDepth;
                
                // Update the indentation
                const depth = targetFolderId ? 
                    parseInt(this.closest('[data-depth]').dataset.depth) + 1 : 0;
                const titleDiv = templateRow.querySelector('.title > div');
                if (titleDiv) {
                    titleDiv.style.paddingLeft = `${depth * 20}px`;
                }

                // Find the closest folder row that contains this template
                let currentRow = draggedItem.previousElementSibling;
                let parentFolderRow = null;
                
                // Look backwards to find the parent folder
                while (currentRow) {
                    if (currentRow.classList.contains('folder-row') && 
                        parseInt(currentRow.dataset.depth) < newDepth) {
                        parentFolderRow = currentRow;
                        break;
                    }
                    currentRow = currentRow.previousElementSibling;
                }
                
                // If we found a parent folder, refresh its visibility
                if (parentFolderRow) {
                    const isExpanded = !parentFolderRow.classList.contains('collapsed');
                    setChildrenVisibility(parentFolderRow, isExpanded);
                }
            }
        } else {
            throw new Error('Failed to move template');
        }
    } catch (error) {
        console.error('Error moving template:', error);
        alert('Error moving template. Please try again.');
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