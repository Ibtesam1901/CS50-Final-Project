// NeighborGrid Client-side Interactivity
// Features: Local filtering/sorting, Relative time updates (Part B4),
// Feed live polling with Sticky Pill (Part A1), and Notification summary polling (Part A3).

document.addEventListener('DOMContentLoaded', () => {
    // ==============================================================================
    // 1. RELATIVE TIME ENGINE (PART B4)
    // ==============================================================================
    function timeAgo(dateString) {
        if (!dateString) return '';
        // Parse SQL timestamp format YYYY-MM-DD HH:MM:SS (assume UTC if bare)
        let normalized = dateString.replace(' ', 'T');
        if (!normalized.endsWith('Z') && !normalized.includes('+')) {
            normalized += 'Z';
        }
        const date = new Date(normalized);
        if (isNaN(date.getTime())) return dateString;

        const now = new Date();
        const diffSecs = Math.floor((now - date) / 1000);

        if (diffSecs < 45) return 'just now';
        if (diffSecs < 90) return '1 min ago';
        const diffMins = Math.floor(diffSecs / 60);
        if (diffMins < 60) return `${diffMins} min ago`;

        const diffHours = Math.floor(diffMins / 60);
        if (diffHours === 1) return '1 hour ago';
        if (diffHours < 24) return `${diffHours} hours ago`;

        const diffDays = Math.floor(diffHours / 24);
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
        if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;

        return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
    }

    function updateAllRelativeTimes() {
        document.querySelectorAll('.timeago, time[datetime]').forEach(el => {
            const dt = el.getAttribute('datetime') || el.getAttribute('title');
            if (dt) {
                el.textContent = timeAgo(dt);
            }
        });
    }

    updateAllRelativeTimes();
    // Update relative timestamps live on the page every 60 seconds without refetching
    setInterval(updateAllRelativeTimes, 60000);


    // ==============================================================================
    // 2. FEED FILTERING & SORTING ENGINE
    // ==============================================================================
    const searchInput = document.getElementById('searchInput');
    const typeFilter = document.getElementById('typeFilter');
    const categoryFilter = document.getElementById('categoryFilter');
    const radiusFilter = document.getElementById('radiusFilter');
    const sortFilter = document.getElementById('sortFilter');
    const postsContainer = document.getElementById('postsContainer');
    const feedCount = document.getElementById('feedCount');
    const activeFilterBadge = document.getElementById('activeFilterBadge');
    const newPostsPill = document.getElementById('newPostsPill');
    const newPostsPillText = document.getElementById('newPostsPillText');

    let debounceTimer = null;

    function filterAndSortPosts() {
        if (!postsContainer) return;
        const query = searchInput ? searchInput.value.trim().toLowerCase() : '';
        const selectedType = typeFilter ? typeFilter.value : 'all';
        const selectedCategory = categoryFilter ? categoryFilter.value : 'all';
        const selectedRadius = (radiusFilter && radiusFilter.value !== 'all') ? parseFloat(radiusFilter.value) : null;
        const selectedSort = sortFilter ? sortFilter.value : 'nearest';

        const postItems = Array.from(postsContainer.querySelectorAll('.post-grid-item'));
        let visibleCount = 0;

        // Filter items
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

        // Sort visible items
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

        visibleItems.forEach(item => postsContainer.appendChild(item));

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


    // ==============================================================================
    // 3. LIVE FEED UPDATES VIA SHORT POLLING & STICKY PILL (PART A1)
    // ==============================================================================
    let lastPollCursor = new Date().toISOString().replace('T', ' ').substring(0, 19);
    let queuedNewPosts = [];
    let isPollingFeed = false;
    let feedPollBackoff = 10000; // 10s default, max 60s

    async function pollFeedUpdates() {
        if (!postsContainer || isPollingFeed) return;
        isPollingFeed = true;

        try {
            const res = await fetch(`/api/posts/updates?since=${encodeURIComponent(lastPollCursor)}`, { credentials: 'same-origin' });
            if (res.ok) {
                feedPollBackoff = 10000; // Reset backoff on success
                const data = await res.json();
                if (data.cursor) lastPollCursor = data.cursor;

                // 1. Remove deleted or expired post cards
                if (data.removed_ids && data.removed_ids.length > 0) {
                    data.removed_ids.forEach(pid => {
                        const existing = document.querySelector(`.post-grid-item a[href="/post/${pid}"]`);
                        if (existing) {
                            const card = existing.closest('.post-grid-item');
                            if (card) card.remove();
                        }
                    });
                    filterAndSortPosts();
                }

                // 2. Update Impact Count badge if changed
                if (data.impact_count !== undefined) {
                    const impactEl = document.getElementById('impactCount');
                    if (impactEl) impactEl.textContent = data.impact_count;
                }

                // 3. Check for new or updated posts
                if (data.posts && data.posts.length > 0) {
                    const brandNew = [];
                    data.posts.forEach(p => {
                        const existingLink = document.querySelector(`.post-grid-item a[href="/post/${p.id}"]`);
                        if (existingLink) {
                            // Update existing card's badges or status inline
                            const card = existingLink.closest('.post-grid-item');
                            if (card) {
                                card.setAttribute('data-title', p.title.toLowerCase());
                                card.setAttribute('data-urgency', p.urgency);
                            }
                        } else {
                            brandNew.push(p);
                        }
                    });

                    if (brandNew.length > 0) {
                        queuedNewPosts.push(...brandNew);
                        if (newPostsPill && newPostsPillText) {
                            newPostsPillText.textContent = `${queuedNewPosts.length} new post${queuedNewPosts.length > 1 ? 's' : ''}`;
                            newPostsPill.classList.remove('d-none');
                        }
                    }
                }
            } else {
                feedPollBackoff = Math.min(feedPollBackoff * 1.5, 60000);
            }
        } catch (err) {
            feedPollBackoff = Math.min(feedPollBackoff * 1.5, 60000);
        } finally {
            isPollingFeed = false;
        }
    }

    function renderPostCard(post) {
        const col = document.createElement('div');
        col.className = 'col-md-6 col-lg-4 post-grid-item';
        col.setAttribute('data-title', post.title.toLowerCase());
        col.setAttribute('data-desc', post.description.toLowerCase());
        col.setAttribute('data-type', post.post_type);
        col.setAttribute('data-category-id', post.category_id);
        col.setAttribute('data-distance', post.distance_km !== null ? post.distance_km : '');
        col.setAttribute('data-urgency', post.urgency);
        col.setAttribute('data-created', post.created_at);

        const badgeClass = post.post_type === 'request' ? 'badge-request' : 'badge-offer';
        const typeIcon = post.post_type === 'request' ? 'fa-hand-holding-hand' : 'fa-gift';
        const distHtml = post.distance_km !== null 
            ? `<span class="badge bg-success-subtle text-success border border-success-subtle px-2 py-1"><i class="fa-solid fa-person-walking me-1"></i> ${post.distance_km} km away</span>`
            : `<span><i class="fa-solid fa-location-dot text-danger me-1"></i> ${escapeHtml(post.neighborhood)}</span>`;

        col.innerHTML = `
            <div class="card h-100 shadow-sm border-0 post-card ${post.urgency === 'urgent' ? 'border-urgent' : ''}">
                <div class="card-body d-flex flex-column p-4">
                    <div class="d-flex justify-content-between align-items-start gap-2 mb-2">
                        <span class="badge ${badgeClass} text-uppercase">
                            <i class="fa-solid ${typeIcon} me-1"></i> ${post.post_type}
                        </span>
                        <span class="badge bg-light text-secondary border small">
                            <i class="fa-solid ${post.category_icon || 'fa-tag'} me-1 text-success"></i> ${escapeHtml(post.category)}
                        </span>
                    </div>
                    ${post.urgency === 'urgent' ? '<div class="mb-2"><span class="badge bg-danger small animate-pulse"><i class="fa-solid fa-triangle-exclamation me-1"></i> URGENT / ZAROORI</span></div>' : ''}
                    <h5 class="card-title fw-bold text-dark mt-1 mb-2">
                        <a href="/post/${post.id}" class="text-dark text-decoration-none stretched-link">
                            ${escapeHtml(post.title)}
                        </a>
                    </h5>
                    <p class="card-text text-secondary small flex-grow-1 text-truncate-3">
                        ${escapeHtml(post.description)}
                    </p>
                    <div class="d-flex justify-content-between align-items-center small text-muted mb-2">
                        <div>${distHtml}</div>
                        ${post.location_details ? `<span class="text-truncate" style="max-width: 140px;" title="${escapeHtml(post.location_details)}">${escapeHtml(post.location_details)}</span>` : ''}
                    </div>
                    <div class="border-top pt-3 mt-2 d-flex justify-content-between align-items-center text-muted small">
                        <span><i class="fa-solid fa-user me-1 text-success"></i> ${escapeHtml(post.username)}</span>
                        <span><i class="fa-regular fa-clock me-1"></i> <time class="timeago" datetime="${post.created_at}" title="${post.created_at}">${timeAgo(post.created_at)}</time></span>
                    </div>
                </div>
            </div>
        `;
        return col;
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // Tap sticky pill to insert queued new posts without disrupting active scroll
    if (newPostsPill) {
        newPostsPill.addEventListener('click', () => {
            if (queuedNewPosts.length > 0 && postsContainer) {
                queuedNewPosts.forEach(p => {
                    const el = renderPostCard(p);
                    postsContainer.prepend(el);
                });
                queuedNewPosts = [];
                newPostsPill.classList.add('d-none');
                filterAndSortPosts();
                updateAllRelativeTimes();

                // Smooth scroll to top of feed
                const feedSect = document.getElementById('feedSection');
                if (feedSect) feedSect.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }

    // Page Visibility API management for Feed polling
    if (postsContainer) {
        let feedPollTimer = setInterval(pollFeedUpdates, feedPollBackoff);
        document.addEventListener('visibilitychange', () => {
            clearInterval(feedPollTimer);
            if (!document.hidden) {
                pollFeedUpdates();
                feedPollTimer = setInterval(pollFeedUpdates, feedPollBackoff);
            }
        });
    }


    // ==============================================================================
    // 4. NOTIFICATIONS SUMMARY POLLING (PART A3)
    // ==============================================================================
    let notifPollTimer = null;
    let originalTitle = document.title;

    async function pollNotificationsSummary() {
        try {
            const res = await fetch('/api/notifications/summary', { credentials: 'same-origin' });
            if (res.status === 401) {
                // User logged out; stop polling
                if (notifPollTimer) clearInterval(notifPollTimer);
                return;
            }
            if (res.ok) {
                const data = await res.json();
                if (data.status === 'ok') {
                    const badge = document.getElementById('navbarNotifBadge');
                    const count = data.total_unread || 0;

                    if (badge) {
                        if (count > 0) {
                            badge.textContent = count;
                            badge.classList.remove('d-none');
                        } else {
                            badge.classList.add('d-none');
                        }
                    }

                    // Dynamic Page Title prefix e.g. "(2) NeighborGrid"
                    if (count > 0) {
                        const cleanTitle = document.title.replace(/^\(\d+\)\s*/, '');
                        document.title = `(${count}) ${cleanTitle}`;
                    } else {
                        document.title = document.title.replace(/^\(\d+\)\s*/, '');
                    }

                    // Non-intrusive toast notification for newly arrived chat message
                    if (data.toast && !window.location.pathname.startsWith(`/post/${data.toast.post_id}`)) {
                        showToast(`New message from ${data.toast.sender}`, data.toast.content, `/post/${data.toast.post_id}#chatSection`);
                    }
                }
            }
        } catch (e) {
            // Silently ignore background network errors
        }
    }

    function showToast(title, body, linkUrl) {
        let toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
            toastContainer.style.zIndex = '1090';
            document.body.appendChild(toastContainer);
        }

        const toastId = 'toast_' + Date.now();
        const toastEl = document.createElement('div');
        toastEl.id = toastId;
        toastEl.className = 'toast show border-primary shadow';
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'polite');
        toastEl.setAttribute('aria-atomic', 'true');
        toastEl.innerHTML = `
            <div class="toast-header bg-primary text-white">
                <i class="fa-solid fa-comment-dots me-2"></i>
                <strong class="me-auto">${escapeHtml(title)}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close" onclick="this.closest('.toast').remove()"></button>
            </div>
            <div class="toast-body bg-white text-dark">
                <p class="small mb-1">${escapeHtml(body)}</p>
                <a href="${linkUrl}" class="btn btn-sm btn-outline-primary py-0" style="font-size: 11px;">View Chat</a>
            </div>
        `;
        toastContainer.appendChild(toastEl);
        setTimeout(() => { if (toastEl) toastEl.remove(); }, 6000);
    }

    // Start notification summary polling every 18 seconds
    notifPollTimer = setInterval(pollNotificationsSummary, 18000);
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            pollNotificationsSummary();
        }
    });
});
