document.addEventListener('DOMContentLoaded', function() {
    console.log('Template explorer script loaded');
    
    // Make rows with children clickable
    document.querySelectorAll('.folder-row.has-children').forEach(row => {
        const toggle = row.querySelector('.toggle-children');
        const depth = parseInt(row.dataset.depth);
        const folderId = row.dataset.folderId;
        
        // Function to toggle children
        const toggleChildren = (e) => {
            if (e && (e.target.tagName === 'A' || e.target.closest('a'))) {
                return;  // Don't toggle if clicking a link
            }
            
            const isCollapsed = row.classList.toggle('collapsed');
            let nextRow = row.nextElementSibling;
            
            // Toggle all children until we hit another item at the same or higher level
            while (nextRow) {
                const nextDepth = parseInt(nextRow.dataset.depth || '0');
                if (nextDepth <= depth) break;
                
                if (nextDepth === depth + 1) {
                    nextRow.style.display = isCollapsed ? 'none' : '';
                }
                nextRow = nextRow.nextElementSibling;
            }
        };
        
        // Add click handler to the entire row
        row.addEventListener('click', toggleChildren);
        
        // Also make the toggle button clickable
        if (toggle) {
            toggle.addEventListener('click', function(e) {
                e.stopPropagation();
                toggleChildren(e);
            });
        }
    });
});