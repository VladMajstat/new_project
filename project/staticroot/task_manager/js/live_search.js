// task_manager/js/live_search.js

document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search_input');
    const rows = document.querySelectorAll('.tasks-list tbody tr');

    if (searchInput && rows.length > 0) {
        searchInput.addEventListener('input', function(event) {
            const searchTerm = event.target.value.toLowerCase().trim();

            rows.forEach(row => {
                const customerNameCell = row.querySelector('td:nth-child(2)');
                if (customerNameCell) {
                    const customerName = customerNameCell.textContent.toLowerCase();
                    if (customerName.includes(searchTerm)) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                }
            });
        });
    }
});