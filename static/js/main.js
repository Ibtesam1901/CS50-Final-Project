// NeighborGrid Client-side Interactivity (Filter, Search, Sort & Radius)

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const typeFilter = document.getElementById('typeFilter');
    const categoryFilter = document.getElementById('categoryFilter');
    const radiusFilter = document.getElementById('radiusFilter');
    const sortFilter = document.getElementById('sortFilter');
    const postsContainer = document.getElementById('postsContainer');
    const feedCount = document.getElementById('feedCount');
    const activeFilterBadge = document.getElementById('activeFilterBadge');

    if (!postsContainer) {
        return;
    }

    let debounceTimer = null;

    function filterAndSortPosts() {
        const query = searchInput ? searchInput.value.trim().toLowerCase() : '';
        const selectedType = typeFilter ? typeFilter.value : 'all';
        const selectedCategory = categoryFilter ? categoryFilter.value : 'all';
        const selectedRadius = (radiusFilter && radiusFilter.value !== 'all') ? parseFloat(radiusFilter.value) : null;
        const selectedSort = sortFilter ? sortFilter.value : 'nearest';

        const postItems = Array.from(postsContainer.querySelectorAll('.post-grid-item'));
        let visibleCount = 0;

        // 1. Filter items
        postItems.forEach(item => {
            const title = (item.getAttribute('data-title') || '').toLowerCase();
            const desc = item.innerText.toLowerCase();
            const type = item.getAttribute('data-type');
            const categoryId = item.getAttribute('data-category-id');
            const distanceAttr = item.getAttribute('data-distance');
            const distance = distanceAttr !== null && distanceAttr !== '' ? parseFloat(distanceAttr) : null;

            const matchesQuery = query === '' || title.includes(query) || desc.includes(query);
            const matchesType = selectedType === 'all' || type === selectedType;
            const matchesCat = selectedCategory === 'all' || categoryId === selectedCategory;
            const matchesRadius = selectedRadius === null || (distance !== null && distance <= selectedRadius);

            if (matchesQuery && matchesType && matchesCat && matchesRadius) {
                item.style.display = '';
                visibleCount++;
            } else {
                item.style.display = 'none';
            }
        });

        // 2. Sort visible items
        const visibleItems = postItems.filter(item => item.style.display !== 'none');
        visibleItems.sort((a, b) => {
            const distA = a.getAttribute('data-distance') ? parseFloat(a.getAttribute('data-distance')) : 999999;
            const distB = b.getAttribute('data-distance') ? parseFloat(b.getAttribute('data-distance')) : 999999;
            const dateA = a.getAttribute('data-created') || '';
            const dateB = b.getAttribute('data-created') || '';
            const urgA = a.getAttribute('data-urgency') === 'urgent' ? 1 : 0;
            const urgB = b.getAttribute('data-urgency') === 'urgent' ? 1 : 0;

            if (selectedSort === 'nearest') {
                return distA - distB;
            } else if (selectedSort === 'urgent') {
                if (urgA !== urgB) return urgB - urgA; // urgent first
                return distA - distB;
            } else if (selectedSort === 'newest') {
                return dateB.localeCompare(dateA);
            }
            return 0;
        });

        // Re-append sorted elements
        visibleItems.forEach(item => postsContainer.appendChild(item));

        // Update counts
        if (feedCount) {
            feedCount.textContent = `Showing ${visibleCount} post${visibleCount !== 1 ? 's' : ''}`;
        }

        if (activeFilterBadge) {
            const filtersApplied = [];
            if (selectedType !== 'all') filtersApplied.push(selectedType);
            if (selectedRadius !== null) filtersApplied.push(`≤ ${selectedRadius} km`);
            if (selectedSort !== 'nearest') filtersApplied.push(selectedSort);
            
            if (filtersApplied.length > 0) {
                activeFilterBadge.innerHTML = `<i class="fa-solid fa-filter me-1 text-primary"></i> Active: ${filtersApplied.join(' · ')}`;
            } else {
                activeFilterBadge.innerHTML = `<i class="fa-solid fa-filter me-1"></i> Real-time proximity feed`;
            }
        }

        // Show/hide no-results message
        let noResultsNotice = document.getElementById('noFilterResults');
        if (visibleCount === 0) {
            if (!noResultsNotice) {
                noResultsNotice = document.createElement('div');
                noResultsNotice.id = 'noFilterResults';
                noResultsNotice.className = 'col-12 text-center py-5 text-muted';
                noResultsNotice.innerHTML = `
                    <i class="fa-solid fa-filter-circle-xmark display-6 mb-2"></i>
                    <h5>No posts match your filters</h5>
                    <p class="small">Try expanding your search radius or selecting a different category.</p>
                `;
                postsContainer.appendChild(noResultsNotice);
            }
            noResultsNotice.style.display = '';
        } else if (noResultsNotice) {
            noResultsNotice.style.display = 'none';
        }
    }

    if (searchInput) {
        searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(filterAndSortPosts, 180);
        });
    }

    if (typeFilter) typeFilter.addEventListener('change', filterAndSortPosts);
    if (categoryFilter) categoryFilter.addEventListener('change', filterAndSortPosts);
    if (radiusFilter) radiusFilter.addEventListener('change', filterAndSortPosts);
    if (sortFilter) sortFilter.addEventListener('change', filterAndSortPosts);
});
