// Real-time floating review notification cards for Admin
(function () {
    let shownIds = new Set();
    let container = null;

    function getContainer() {
        if (!container) {
            container = document.getElementById('admin-notif-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'admin-notif-container';
                container.className = 'admin-notif-container';
                document.body.appendChild(container);
            }
        }
        return container;
    }

    function createStars(rating) {
        let stars = '';
        const r = Math.round(Number(rating) || 5);
        for (let i = 0; i < r; i++) stars += '★';
        for (let i = r; i < 5; i++) stars += '☆';
        return stars;
    }

    function dismissNotification(reviewId, cardEl) {
        if (cardEl) {
            cardEl.classList.add('fade-out');
            setTimeout(() => {
                if (cardEl.parentNode) cardEl.parentNode.removeChild(cardEl);
            }, 300);
        }
        fetch(`/api/admin/notifications/dismiss/${reviewId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        }).catch(err => console.error('Error dismissing review notification:', err));
    }

    function renderCard(review) {
        if (shownIds.has(review.id)) return;
        shownIds.add(review.id);

        const c = getContainer();
        const card = document.createElement('div');
        card.className = 'admin-notif-card';
        card.id = `admin-notif-${review.id}`;

        const starsStr = createStars(review.rating);
        const reviewText = review.review_text ? review.review_text : 'No written comments.';
        const author = review.user_name || 'Verified User';
        const prodName = review.product_name || 'Skincare Formulation';

        card.innerHTML = `
            <div class="admin-notif-header">
                <span class="admin-notif-tag">✦ New Product Review</span>
                <button type="button" class="admin-notif-close" title="Dismiss">×</button>
            </div>
            <p class="admin-notif-product">${escapeHtml(prodName)}</p>
            <div class="admin-notif-meta">
                <span class="admin-notif-stars">${starsStr}</span>
                <span class="admin-notif-author">by ${escapeHtml(author)}</span>
            </div>
            <div class="admin-notif-body">“${escapeHtml(reviewText)}”</div>
            <div class="admin-notif-actions">
                <button type="button" class="admin-notif-btn admin-notif-dismiss">Dismiss</button>
                <a href="/admin/dashboard?tab=reviews#review-${review.id}" class="admin-notif-btn admin-notif-view">Review</a>
            </div>
        `;

        card.querySelector('.admin-notif-close').addEventListener('click', () => {
            dismissNotification(review.id, card);
        });
        card.querySelector('.admin-notif-dismiss').addEventListener('click', () => {
            dismissNotification(review.id, card);
        });
        card.querySelector('.admin-notif-view').addEventListener('click', () => {
            dismissNotification(review.id, card);
        });

        c.appendChild(card);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function checkUnseenReviews() {
        fetch('/api/admin/notifications/unseen')
            .then(res => {
                if (!res.ok) throw new Error('Status ' + res.status);
                return res.json();
            })
            .then(data => {
                if (data && data.unseen_reviews && Array.isArray(data.unseen_reviews)) {
                    data.unseen_reviews.forEach(renderCard);
                    
                    // Update badge counter if present on page
                    const badge = document.getElementById('admin-unseen-badge');
                    if (badge) {
                        if (data.unseen_reviews.length > 0) {
                            badge.textContent = data.unseen_reviews.length;
                            badge.style.display = 'inline-block';
                        } else {
                            badge.style.display = 'none';
                        }
                    }
                }
            })
            .catch(err => {
                // Silently ignore network aborts or non-admin responses
            });
    }

    // Initialize once DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            checkUnseenReviews();
            setInterval(checkUnseenReviews, 15000);
        });
    } else {
        checkUnseenReviews();
        setInterval(checkUnseenReviews, 15000);
    }
})();
