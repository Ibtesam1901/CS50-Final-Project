// NeighborGrid Client-side Interactivity (Filter & Search)

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const typeFilter = document.getElementById('typeFilter');
    const categoryFilter = document.getElementById('categoryFilter');
    const postsContainer = document.getElementById('postsContainer');
    const feedCount = document.getElementById('feedCount');

    if (!searchInput || !typeFilter || !categoryFilter || !postsContainer) {
        return;
    }

    let debounceTimer = null;

    function filterPostsLocally() {
        const query = searchInput.value.trim().toLowerCase();
        const selectedType = typeFilter.value;
        const selectedCategory = categoryFilter.value;

        const postItems = postsContainer.querySelectorAll('.post-grid-item');
        let visibleCount = 0;

        postItems.forEach(item => {
            const title = item.getAttribute('data-title') || '';
            const desc = item.innerText.toLowerCase();
            const type = item.getAttribute('data-type');
            const categoryId = item.getAttribute('data-category-id');

            const matchesQuery = query === '' || title.includes(query) || desc.includes(query);
            const matchesType = selectedType === 'all' || type === selectedType;
            const matchesCat = selectedCategory === 'all' || categoryId === selectedCategory;

            if (matchesQuery && matchesType && matchesCat) {
                item.style.display = '';
                visibleCount++;
            } else {
                item.style.display = 'none';
            }
        });

        if (feedCount) {
            feedCount.textContent = `Showing ${visibleCount} post${visibleCount !== 1 ? 's' : ''}`;
        }

        // Show/hide no-results message dynamically
        let noResultsNotice = document.getElementById('noFilterResults');
        if (visibleCount === 0) {
            if (!noResultsNotice) {
                noResultsNotice = document.createElement('div');
                noResultsNotice.id = 'noFilterResults';
                noResultsNotice.className = 'col-12 text-center py-5 text-muted';
                noResultsNotice.innerHTML = `
                    <i class="fa-solid fa-filter-circle-xmark display-6 mb-2"></i>
                    <h5>No posts match your filters</h5>
                    <p class="small">Try adjusting your search keyword or clearing the filters.</p>
                `;
                postsContainer.appendChild(noResultsNotice);
            }
            noResultsNotice.style.display = '';
        } else if (noResultsNotice) {
            noResultsNotice.style.display = 'none';
        }
    }

    // Debounce search typing
    searchInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(filterPostsLocally, 180);
    });

    typeFilter.addEventListener('change', filterPostsLocally);
    categoryFilter.addEventListener('change', filterPostsLocally);
});
