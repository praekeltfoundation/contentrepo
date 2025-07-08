document.addEventListener('DOMContentLoaded', function() {
    console.log('Template explorer script loaded');
    
    // Make rows with children clickable
    document.querySelectorAll('.template-row.has-children').forEach(row => {
        const toggle = row.querySelector('.toggle-children');
        const depth = parseInt(row.dataset.depth);
        const templateId = row.dataset.templateId;
        
        // Function to toggle children
        const toggleChildren = (e) => {
            if (e && (e.target.tagName === 'A' || e.target.closest('a'))) {
                return;  // Don't toggle if clicking a link
            }
            
            const isCollapsed = row.classList.toggle('collapsed');
            
            // Find and toggle all direct children
            let nextRow = row.nextElementSibling;
            while (nextRow) {
                const nextDepth = parseInt(nextRow.dataset.depth);
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
