/**
 * Floating Feedback Widget & Direct Submission
 * Skincare AI
 *
 * Provides a fixed bottom-right feedback button, direct in-card submission,
 * and live community feedback review stats.
 */

(function () {
    if (window.__floatingFeedbackInitialized) return;
    window.__floatingFeedbackInitialized = true;

    let summaryData = {
        total_count: 0,
        avg_rating: 0.0,
        positive_percent: 0,
        star_counts: { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 },
        star_percents: { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 },
        recent_reviews: []
    };

    let activeTab = 'submit'; // 'submit' or 'reviews'
    let selectedRating = 5;
    let currentSlideIndex = 0;
    let autoPlayTimer = null;
    let isCardOpen = false;

    // Retrieve open/collapse preference from localStorage
    const storedState = localStorage.getItem('skincare_floating_feedback_open');
    isCardOpen = storedState === 'true';

    async function fetchSummary() {
        try {
            const res = await fetch('/api/feedback/summary');
            if (!res.ok) throw new Error('API error');
            const data = await res.json();
            if (data.status === 'success' && data.summary) {
                summaryData = data.summary;
                renderWidget();
            }
        } catch (err) {
            console.warn('Could not fetch feedback summary:', err);
        }
    }

    function renderWidget() {
        let container = document.getElementById('floating-feedback-root');
        if (!container) {
            container = document.createElement('div');
            container.id = 'floating-feedback-root';
            container.className = 'floating-feedback-root';
            document.body.appendChild(container);
        }

        container.innerHTML = '';
        const count = summaryData.total_count || 0;
        const avg = summaryData.avg_rating || 0;

        if (!isCardOpen) {
            // RENDER FLOATING PILL
            const pill = document.createElement('div');
            pill.className = 'floating-feedback-pill';
            pill.title = 'Click to share feedback or view reviews';
            pill.setAttribute('role', 'button');
            pill.setAttribute('tabindex', '0');

            if (count > 0) {
                pill.innerHTML = `
                    <div class="pill-pulse-dot"></div>
                    <div class="pill-star-badge">
                        <span class="pill-star-icon">★</span>
                        <span>${avg.toFixed(1)}</span>
                    </div>
                    <span class="pill-text">Feedback (${count})</span>
                `;
            } else {
                pill.innerHTML = `
                    <div class="pill-pulse-dot"></div>
                    <div class="pill-star-badge">
                        <span class="pill-star-icon">✦</span>
                        <span>Feedback</span>
                    </div>
                    <span class="pill-text">Share Feedback</span>
                `;
            }

            pill.addEventListener('click', toggleCard);
            pill.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggleCard();
                }
            });

            container.appendChild(pill);
            stopCarousel();
        } else {
            // RENDER EXPANDED CARD
            const card = document.createElement('div');
            card.className = 'floating-feedback-card';
            card.setAttribute('role', 'dialog');
            card.setAttribute('aria-label', 'Feedback Widget');

            card.innerHTML = `
                <div class="floating-card-header">
                    <div class="floating-header-title">
                        <span class="floating-header-icon">✦</span>
                        <h4>Skincare AI Feedback</h4>
                    </div>
                    <button class="floating-close-btn" id="floatingCloseBtn" title="Close" aria-label="Close widget">✕</button>
                </div>

                <div class="floating-tab-bar">
                    <button class="floating-tab-btn ${activeTab === 'submit' ? 'active' : ''}" id="tabBtnSubmit">
                        ✍ Send Feedback
                    </button>
                    <button class="floating-tab-btn ${activeTab === 'reviews' ? 'active' : ''}" id="tabBtnReviews">
                        ★ Community Reviews (${count})
                    </button>
                </div>

                <div id="floatingCardBody">
                    ${activeTab === 'submit' ? renderSubmitPaneHtml() : renderReviewsPaneHtml()}
                </div>

                <div class="floating-card-footer">
                    <a href="/feedback" class="footer-link-full">Full Feedback Page →</a>
                    <span style="font-size: 11px; color: #9e8e8b;">Your voice matters</span>
                </div>
            `;

            container.appendChild(card);

            // Close button
            const closeBtn = card.querySelector('#floatingCloseBtn');
            if (closeBtn) closeBtn.addEventListener('click', toggleCard);

            // Tab buttons
            const tabSubmit = card.querySelector('#tabBtnSubmit');
            const tabReviews = card.querySelector('#tabBtnReviews');
            if (tabSubmit) {
                tabSubmit.addEventListener('click', () => {
                    activeTab = 'submit';
                    renderWidget();
                });
            }
            if (tabReviews) {
                tabReviews.addEventListener('click', () => {
                    activeTab = 'reviews';
                    renderWidget();
                });
            }

            if (activeTab === 'submit') {
                bindSubmitPaneEvents(card);
            } else {
                bindReviewsPaneEvents(card);
            }
        }
    }

    function toggleCard() {
        isCardOpen = !isCardOpen;
        localStorage.setItem('skincare_floating_feedback_open', isCardOpen ? 'true' : 'false');
        renderWidget();
    }

    /* ========================================================
       INLINE SUBMIT PANE
    ======================================================== */

    function renderSubmitPaneHtml() {
        return `
            <div class="floating-form-pane" id="floatingFormPane">
                <form id="floatingFeedbackForm">
                    <div class="floating-form-group">
                        <label>1. Rate Your Experience</label>
                        <div class="floating-star-picker" id="starPicker">
                            ${[1, 2, 3, 4, 5].map(val => `
                                <button type="button" class="star-pick-btn ${val <= selectedRating ? 'active' : ''}" data-value="${val}">
                                    ★
                                </button>
                            `).join('')}
                            <span class="floating-star-hint" id="starHint">${getStarLabel(selectedRating)}</span>
                        </div>
                    </div>

                    <div class="floating-form-group">
                        <label for="floatingCategory">2. Category</label>
                        <select id="floatingCategory" name="category">
                            <option value="general">General Feedback</option>
                            <option value="ai_answers">Ask AI answers</option>
                            <option value="product_finder">Product finder & recommendations</option>
                            <option value="ingredients">Ingredient information</option>
                            <option value="skin_analysis">Skin analysis</option>
                            <option value="website_design">Website design & usability</option>
                            <option value="suggestion">General suggestion</option>
                            <option value="bug">Bug / Issue</option>
                        </select>
                    </div>

                    <div class="floating-form-group">
                        <label for="floatingUserInfo">3. Name or Email (Optional)</label>
                        <input type="text" id="floatingUserInfo" name="user_info" placeholder="e.g. Alex or alex@example.com" maxlength="150">
                    </div>

                    <div class="floating-form-group">
                        <label for="floatingMessage">4. Message <span style="color:#e74c3c;">*</span></label>
                        <textarea id="floatingMessage" name="message" rows="3" minlength="3" maxlength="2000" placeholder="Share your experience or suggestions..." required></textarea>
                    </div>

                    <div id="floatingFormMsg" style="display:none; font-size:12px; margin-bottom:10px;"></div>

                    <button type="submit" class="floating-submit-btn" id="floatingSubmitBtn">
                        <span>Send Feedback</span>
                        <span aria-hidden="true">→</span>
                    </button>
                </form>
            </div>
        `;
    }

    function bindSubmitPaneEvents(card) {
        // Star picker buttons
        const starButtons = card.querySelectorAll('.star-pick-btn');
        const starHint = card.querySelector('#starHint');

        starButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                selectedRating = parseInt(btn.dataset.value, 10);
                starButtons.forEach(b => {
                    const v = parseInt(b.dataset.value, 10);
                    b.classList.toggle('active', v <= selectedRating);
                });
                if (starHint) starHint.textContent = getStarLabel(selectedRating);
            });
        });

        // Form submit
        const form = card.querySelector('#floatingFeedbackForm');
        const submitBtn = card.querySelector('#floatingSubmitBtn');
        const msgBox = card.querySelector('#floatingFormMsg');

        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const category = form.querySelector('#floatingCategory').value;
                const userInfo = form.querySelector('#floatingUserInfo').value.trim();
                const message = form.querySelector('#floatingMessage').value.trim();

                if (!message || message.length < 3) {
                    showMsg('Please write a message (at least 3 characters).', 'error');
                    return;
                }

                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.textContent = 'Submitting...';
                }

                try {
                    const res = await fetch('/api/feedback/submit', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            rating: selectedRating,
                            category: category,
                            user_info: userInfo,
                            message: message
                        })
                    });

                    const resData = await res.json();
                    if (res.ok && resData.status === 'success') {
                        // Show success view
                        const formPane = card.querySelector('#floatingFormPane');
                        if (formPane) {
                            formPane.innerHTML = `
                                <div class="floating-form-success">
                                    <div class="floating-success-icon">✓</div>
                                    <h5>Thank You!</h5>
                                    <p>Your feedback has been submitted successfully.</p>
                                    <button type="button" class="floating-submit-btn" id="btnViewReviews">
                                        View Community Reviews (${summaryData.total_count + 1}) →
                                    </button>
                                </div>
                            `;
                            const btnView = formPane.querySelector('#btnViewReviews');
                            if (btnView) {
                                btnView.addEventListener('click', () => {
                                    activeTab = 'reviews';
                                    fetchSummary();
                                });
                            }
                        }
                        // Refresh summary in background
                        fetchSummary();
                    } else {
                        showMsg(resData.message || 'Could not save feedback.', 'error');
                        if (submitBtn) {
                            submitBtn.disabled = false;
                            submitBtn.textContent = 'Send Feedback →';
                        }
                    }
                } catch (err) {
                    showMsg('Network error. Please try again.', 'error');
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'Send Feedback →';
                    }
                }
            });
        }

        function showMsg(text, type) {
            if (!msgBox) return;
            msgBox.style.display = 'block';
            msgBox.style.color = type === 'error' ? '#e74c3c' : '#27ae60';
            msgBox.textContent = text;
        }
    }

    function getStarLabel(rating) {
        switch (rating) {
            case 5: return '5 Stars (Excellent)';
            case 4: return '4 Stars (Good)';
            case 3: return '3 Stars (Okay)';
            case 2: return '2 Stars (Poor)';
            case 1: return '1 Star (Very poor)';
            default: return '';
        }
    }

    /* ========================================================
       REVIEWS PANE & CAROUSEL
    ======================================================== */

    function renderReviewsPaneHtml() {
        const count = summaryData.total_count || 0;
        const avg = summaryData.avg_rating || 0;
        const sat = summaryData.positive_percent || 0;
        const p5 = (summaryData.star_percents && summaryData.star_percents[5]) || 0;
        const p4 = (summaryData.star_percents && summaryData.star_percents[4]) || 0;
        const p3 = (summaryData.star_percents && summaryData.star_percents[3]) || 0;
        const reviews = summaryData.recent_reviews || [];

        const ratingDisplay = count > 0 ? `${avg.toFixed(1)} <span class="sum-item-stars">★</span>` : '—';
        const satDisplay = count > 0 ? `${sat}%` : '—';

        return `
            <div class="floating-reviews-pane">
                <div class="floating-sum-strip">
                    <div class="floating-sum-item">
                        <span class="sum-item-val">${ratingDisplay}</span>
                        <span class="sum-item-lbl">Avg Rating</span>
                    </div>
                    <div class="floating-sum-item">
                        <span class="sum-item-val">${count}</span>
                        <span class="sum-item-lbl">Total Reviews</span>
                    </div>
                    <div class="floating-sum-item">
                        <span class="sum-item-val">${satDisplay}</span>
                        <span class="sum-item-lbl">Satisfaction</span>
                    </div>
                </div>

                <div class="floating-breakdown-row">
                    ${count > 0 ? `
                        <div class="floating-mini-bar-wrap">
                            <span class="mini-bar-lbl">5 ★</span>
                            <div class="mini-bar-track">
                                <div class="mini-bar-fill bar-star-5" style="width: ${p5}%;"></div>
                            </div>
                            <span class="mini-bar-pct">${p5}%</span>
                        </div>
                        <div class="floating-mini-bar-wrap">
                            <span class="mini-bar-lbl">4 ★</span>
                            <div class="mini-bar-track">
                                <div class="mini-bar-fill bar-star-4" style="width: ${p4}%;"></div>
                            </div>
                            <span class="mini-bar-pct">${p4}%</span>
                        </div>
                        ${p3 > 0 ? `
                        <div class="floating-mini-bar-wrap">
                            <span class="mini-bar-lbl">3 ★</span>
                            <div class="mini-bar-track">
                                <div class="mini-bar-fill bar-star-3" style="width: ${p3}%;"></div>
                            </div>
                            <span class="mini-bar-pct">${p3}%</span>
                        </div>` : ''}
                    ` : `
                        <div style="text-align: center; color: #8a7a76; font-size: 11px; padding: 4px 0;">
                            No ratings yet. Submit your feedback to be featured!
                        </div>
                    `}
                </div>

                <div class="floating-reviews-carousel" id="floatingCarouselWrap">
                    <div class="carousel-title-row">
                        <span class="carousel-section-lbl">User Testimonials (${reviews.length})</span>
                        ${reviews.length > 1 ? `
                            <div class="carousel-nav-arrows">
                                <button class="carousel-nav-btn" id="carouselPrevBtn" title="Previous review" aria-label="Previous review">‹</button>
                                <button class="carousel-nav-btn" id="carouselNextBtn" title="Next review" aria-label="Next review">›</button>
                            </div>
                        ` : ''}
                    </div>

                    <div id="carouselSlideContainer"></div>
                    <div class="carousel-dots" id="carouselDotsContainer"></div>
                </div>
            </div>
        `;
    }

    function bindReviewsPaneEvents(card) {
        const prevBtn = card.querySelector('#carouselPrevBtn');
        const nextBtn = card.querySelector('#carouselNextBtn');
        if (prevBtn) prevBtn.addEventListener('click', showPrevSlide);
        if (nextBtn) nextBtn.addEventListener('click', showNextSlide);

        const carouselWrap = card.querySelector('#floatingCarouselWrap');
        if (carouselWrap) {
            carouselWrap.addEventListener('mouseenter', stopCarousel);
            carouselWrap.addEventListener('mouseleave', startCarousel);
        }

        renderSlide();
        startCarousel();
    }

    function renderSlide() {
        const slideBox = document.getElementById('carouselSlideContainer');
        const dotsBox = document.getElementById('carouselDotsContainer');
        if (!slideBox) return;

        const reviews = summaryData.recent_reviews || [];
        if (reviews.length === 0) {
            slideBox.innerHTML = `
                <div class="carousel-card-slide" style="text-align: center; padding: 16px 12px;">
                    <p class="slide-message" style="margin: 0 0 8px; font-style: normal; color: #6e615e;">
                        No user feedback submitted yet.
                    </p>
                    <button type="button" class="floating-submit-btn" id="btnGoToSubmit" style="font-size:12px; padding:6px 12px; width:auto; margin:0 auto;">
                        ✍ Write First Review
                    </button>
                </div>
            `;
            const btnGo = slideBox.querySelector('#btnGoToSubmit');
            if (btnGo) {
                btnGo.addEventListener('click', () => {
                    activeTab = 'submit';
                    renderWidget();
                });
            }
            if (dotsBox) dotsBox.innerHTML = '';
            return;
        }

        if (currentSlideIndex >= reviews.length) currentSlideIndex = 0;
        if (currentSlideIndex < 0) currentSlideIndex = reviews.length - 1;

        const rev = reviews[currentSlideIndex];
        const stars = rev.rating ? ('★'.repeat(rev.rating) + '☆'.repeat(5 - rev.rating)) : '';

        slideBox.innerHTML = `
            <div class="carousel-card-slide">
                <div class="slide-header">
                    <span class="slide-stars">${stars}</span>
                    <span class="slide-category">${escapeHtml(rev.category_label || 'Feedback')}</span>
                </div>
                <p class="slide-message">“${escapeHtml(rev.message)}”</p>
                <div class="slide-meta-row">
                    <span>👤 ${escapeHtml(rev.user_display || 'Verified User')}</span>
                    <span>🕒 ${escapeHtml(rev.created_at_formatted || 'Recently')}</span>
                </div>
            </div>
        `;

        if (dotsBox && reviews.length > 1) {
            dotsBox.innerHTML = '';
            reviews.forEach((_, idx) => {
                const dot = document.createElement('span');
                dot.className = `carousel-dot ${idx === currentSlideIndex ? 'active' : ''}`;
                dot.addEventListener('click', () => {
                    currentSlideIndex = idx;
                    renderSlide();
                });
                dotsBox.appendChild(dot);
            });
        } else if (dotsBox) {
            dotsBox.innerHTML = '';
        }
    }

    function showNextSlide() {
        const reviews = summaryData.recent_reviews || [];
        if (reviews.length <= 1) return;
        currentSlideIndex = (currentSlideIndex + 1) % reviews.length;
        renderSlide();
    }

    function showPrevSlide() {
        const reviews = summaryData.recent_reviews || [];
        if (reviews.length <= 1) return;
        currentSlideIndex = (currentSlideIndex - 1 + reviews.length) % reviews.length;
        renderSlide();
    }

    function startCarousel() {
        stopCarousel();
        const reviews = summaryData.recent_reviews || [];
        if (reviews.length > 1) {
            autoPlayTimer = setInterval(showNextSlide, 4500);
        }
    }

    function stopCarousel() {
        if (autoPlayTimer) {
            clearInterval(autoPlayTimer);
            autoPlayTimer = null;
        }
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Auto-fetch on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fetchSummary);
    } else {
        fetchSummary();
    }
})();
