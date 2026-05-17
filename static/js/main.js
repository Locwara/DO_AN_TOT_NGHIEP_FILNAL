(function () {
    const SKIP_SELECTOR = [
        '[data-no-loading]',
        '[data-loading="false"]',
        '.no-loading',
        '[download]',
        '[target="_blank"]',
    ].join(',');

    let overlay = null;
    let activeTimer = null;
    let failSafeTimer = null;
    let lastSubmitter = null;

    function getOverlay() {
        if (!overlay) {
            overlay = document.getElementById('global-loading');
        }
        return overlay;
    }

    function show(message) {
        const el = getOverlay();
        if (!el) return;
        if (activeTimer) {
            window.clearTimeout(activeTimer);
            activeTimer = null;
        }
        if (failSafeTimer) {
            window.clearTimeout(failSafeTimer);
        }
        const title = el.querySelector('.global-loading__title');
        if (title && message) {
            title.textContent = message;
        }
        el.classList.add('is-active');
        el.setAttribute('aria-hidden', 'false');
        failSafeTimer = window.setTimeout(hide, 12000);
    }

    function hide() {
        const el = getOverlay();
        if (!el) return;
        if (activeTimer) {
            window.clearTimeout(activeTimer);
            activeTimer = null;
        }
        if (failSafeTimer) {
            window.clearTimeout(failSafeTimer);
            failSafeTimer = null;
        }
        el.classList.remove('is-active');
        el.setAttribute('aria-hidden', 'true');
        document.querySelectorAll('.loading-inline').forEach((node) => {
            node.classList.remove('loading-inline');
            if (node.dataset.loadingTextOriginal) {
                node.innerHTML = node.dataset.loadingTextOriginal;
                delete node.dataset.loadingTextOriginal;
            }
        });
    }

    function delayedShow(message, delay) {
        if (activeTimer) {
            window.clearTimeout(activeTimer);
        }
        activeTimer = window.setTimeout(() => show(message), delay == null ? 80 : delay);
    }

    function isModifiedClick(event) {
        return event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0;
    }

    function shouldSkipElement(el) {
        return !el || Boolean(el.closest(SKIP_SELECTOR));
    }

    function shouldSkipHref(anchor) {
        const href = anchor.getAttribute('href');
        if (!href) return true;
        const normalized = href.trim().toLowerCase();
        if (
            normalized === '#' ||
            normalized.startsWith('#') ||
            normalized.startsWith('javascript:') ||
            normalized.startsWith('mailto:') ||
            normalized.startsWith('tel:')
        ) {
            return true;
        }
        try {
            const url = new URL(href, window.location.href);
            const path = url.pathname.toLowerCase();
            if (
                path.includes('/export/') ||
                path.endsWith('.csv') ||
                path.endsWith('.pdf') ||
                path.endsWith('.zip')
            ) {
                return true;
            }
        } catch (error) {
            return true;
        }
        return false;
    }

    function markSubmitter(button) {
        if (!button || shouldSkipElement(button)) return;
        if (button.tagName === 'BUTTON' || button.tagName === 'A') {
            button.classList.add('loading-inline');
        }
    }

    document.addEventListener('click', function (event) {
        const submitter = event.target.closest('button[type="submit"], input[type="submit"]');
        if (submitter) {
            lastSubmitter = submitter;
            return;
        }

        const anchor = event.target.closest('a[href]');
        if (!anchor || isModifiedClick(event) || shouldSkipElement(anchor) || shouldSkipHref(anchor)) {
            return;
        }

        const url = new URL(anchor.href, window.location.href);
        if (url.origin !== window.location.origin) {
            return;
        }

        window.setTimeout(() => {
            if (!event.defaultPrevented) {
                delayedShow(anchor.dataset.loadingText || 'Đang tải');
            }
        }, 0);
    });

    document.addEventListener('submit', function (event) {
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || shouldSkipElement(form)) {
            return;
        }
        if (form.target === '_blank') {
            return;
        }
        if (typeof form.checkValidity === 'function' && !form.checkValidity()) {
            return;
        }
        window.setTimeout(() => {
            if (!event.defaultPrevented) {
                const submitter = lastSubmitter && form.contains(lastSubmitter)
                    ? lastSubmitter
                    : form.querySelector('button[type="submit"], input[type="submit"]');
                markSubmitter(submitter);
                delayedShow(form.dataset.loadingText || 'Đang xử lý');
            }
            lastSubmitter = null;
        }, 0);
    });

    document.addEventListener('DOMContentLoaded', hide);
    window.addEventListener('pageshow', hide);
    window.addEventListener('pagehide', hide);

    window.DevLearnLoading = {
        show,
        hide,
        delayedShow,
        withLoading: function (promise, message) {
            show(message || 'Đang xử lý');
            return Promise.resolve(promise).finally(hide);
        },
    };
})();
