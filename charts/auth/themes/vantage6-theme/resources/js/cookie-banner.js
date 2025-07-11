(function() {
    'use strict';

    // Check if user has already accepted cookies
    function hasAcceptedCookies() {
        return localStorage.getItem('vantage6-cookies-accepted') === 'true';
    }

    // Set cookie acceptance
    function acceptCookies() {
        localStorage.setItem('vantage6-cookies-accepted', 'true');
        hideCookieBanner();
    }

    // Set cookie rejection
    function rejectCookies() {
        localStorage.setItem('vantage6-cookies-accepted', 'false');
        hideCookieBanner();
    }

    // Hide the cookie banner
    function hideCookieBanner() {
        const banner = document.getElementById('cookie-banner');
        if (banner) {
            banner.classList.add('hidden');
        }
    }

    // Show the cookie banner
    function showCookieBanner() {
        const banner = document.getElementById('cookie-banner');
        if (banner) {
            banner.classList.remove('hidden');
        }
    }

    // Initialize cookie banner
    function initCookieBanner() {
        // Don't show if already accepted
        if (hasAcceptedCookies()) {
            return;
        }

        // Add event listeners
        const acceptBtn = document.getElementById('cookie-accept');
        const rejectBtn = document.getElementById('cookie-reject');

        if (acceptBtn) {
            acceptBtn.addEventListener('click', acceptCookies);
        }

        if (rejectBtn) {
            rejectBtn.addEventListener('click', rejectCookies);
        }

        // Show banner after a short delay
        setTimeout(showCookieBanner, 1000);
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCookieBanner);
    } else {
        initCookieBanner();
    }
})();