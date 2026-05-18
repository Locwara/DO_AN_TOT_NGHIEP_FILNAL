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

(function () {
    const STORAGE_PREFIX = 'devlearn.admin.savedFilters.';
    const LEGACY_STORAGE_PREFIX = 'devlearn.admin.savedFilter.';

    function storageKey() {
        return STORAGE_PREFIX + window.location.pathname;
    }

    function legacyStorageKey() {
        return LEGACY_STORAGE_PREFIX + window.location.pathname;
    }

    function currentQuery() {
        return window.location.search;
    }

    function hasMeaningfulQuery() {
        return window.location.search.length > 1;
    }

    function toast(message) {
        const existing = document.querySelector('.admin-filter-toast');
        if (existing) existing.remove();
        const node = document.createElement('div');
        node.className = 'admin-filter-toast';
        node.textContent = message;
        node.style.position = 'fixed';
        node.style.right = '18px';
        node.style.bottom = '18px';
        node.style.zIndex = '1200';
        node.style.padding = '10px 14px';
        node.style.borderRadius = '9px';
        node.style.background = 'var(--primary-900)';
        node.style.color = 'white';
        node.style.fontSize = '13px';
        node.style.fontWeight = '700';
        node.style.boxShadow = 'var(--shadow-modal)';
        document.body.appendChild(node);
        window.setTimeout(() => node.remove(), 2200);
    }

    function readFilters() {
        migrateLegacySavedFilter();
        try {
            const parsed = JSON.parse(window.localStorage.getItem(storageKey()) || '[]');
            if (!Array.isArray(parsed)) return [];
            return parsed.filter((item) => (
                item &&
                typeof item.id === 'string' &&
                typeof item.name === 'string' &&
                typeof item.query === 'string' &&
                item.query.startsWith('?')
            ));
        } catch (error) {
            return [];
        }
    }

    function writeFilters(filters) {
        window.localStorage.setItem(storageKey(), JSON.stringify(filters));
        renderSavedFilters();
    }

    function migrateLegacySavedFilter() {
        const legacyValue = window.localStorage.getItem(legacyStorageKey());
        if (!legacyValue || window.localStorage.getItem(storageKey())) return;
        const queryIndex = legacyValue.indexOf('?');
        const query = queryIndex >= 0 ? legacyValue.slice(queryIndex) : '';
        if (!query) return;
        const now = new Date().toISOString();
        window.localStorage.setItem(storageKey(), JSON.stringify([{
            id: String(Date.now()),
            name: 'Bộ lọc cũ',
            query,
            createdAt: now,
            updatedAt: now,
        }]));
    }

    function defaultFilterName() {
        const pageTitle = (document.querySelector('h1, h2') || {}).textContent || 'Bộ lọc';
        const now = new Date();
        const day = String(now.getDate()).padStart(2, '0');
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const hour = String(now.getHours()).padStart(2, '0');
        const minute = String(now.getMinutes()).padStart(2, '0');
        return `${pageTitle.trim()} ${day}/${month} ${hour}:${minute}`.trim();
    }

    function promptFilterName(message, currentName) {
        const value = window.prompt(message, currentName || defaultFilterName());
        if (value === null) return null;
        const name = value.trim().slice(0, 80);
        if (!name) {
            toast('Tên bộ lọc không được để trống');
            return null;
        }
        return name;
    }

    function filterCount(query) {
        const params = new URLSearchParams(query);
        let count = 0;
        params.forEach((value, key) => {
            if (!value || key === 'page' || key === 'type') return;
            count += 1;
        });
        return count;
    }

    function formatDate(value) {
        if (!value) return '';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return '';
        return date.toLocaleString('vi-VN', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        });
    }

    function makeButton(icon, text, action, id, extraClass) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `btn btn-sm ${extraClass || 'btn-ghost'}`;
        button.dataset.noLoading = 'true';
        button.dataset.savedFilterAction = action;
        button.dataset.savedFilterId = id;

        const iconNode = document.createElement('span');
        iconNode.className = 'material-symbols-outlined text-xs';
        iconNode.textContent = icon;
        button.appendChild(iconNode);
        button.appendChild(document.createTextNode(text));
        return button;
    }

    function renderSavedFilters() {
        const filters = readFilters();
        document.querySelectorAll('.admin-saved-filter-count').forEach((node) => {
            node.textContent = String(filters.length);
        });

        document.querySelectorAll('.js-saved-filter-list').forEach((list) => {
            list.innerHTML = '';
            if (!filters.length) {
                const empty = document.createElement('p');
                empty.className = 'admin-saved-filter-empty';
                empty.textContent = 'Chưa có bộ lọc nào.';
                list.appendChild(empty);
                return;
            }

            filters.forEach((filter) => {
                const item = document.createElement('div');
                item.className = 'admin-saved-filter-item';

                const head = document.createElement('div');
                head.className = 'admin-saved-filter-head';

                const titleBox = document.createElement('div');
                const name = document.createElement('p');
                name.className = 'admin-saved-filter-name';
                name.textContent = filter.name;
                titleBox.appendChild(name);

                const meta = document.createElement('p');
                meta.className = 'admin-saved-filter-meta';
                meta.textContent = `${filterCount(filter.query)} điều kiện · cập nhật ${formatDate(filter.updatedAt)}`;
                titleBox.appendChild(meta);

                const badge = document.createElement('span');
                badge.className = 'badge bg-primary-100 text-primary-700';
                badge.textContent = 'Đã lưu';

                head.appendChild(titleBox);
                head.appendChild(badge);

                const query = document.createElement('p');
                query.className = 'admin-saved-filter-query';
                query.title = filter.query;
                query.textContent = filter.query;

                const actions = document.createElement('div');
                actions.className = 'admin-saved-filter-actions';
                actions.appendChild(makeButton('play_arrow', 'Áp dụng', 'apply', filter.id, 'btn-primary'));
                actions.appendChild(makeButton('edit', 'Đổi tên', 'rename', filter.id));
                actions.appendChild(makeButton('save', 'Ghi đè', 'overwrite', filter.id));
                actions.appendChild(makeButton('delete', 'Xóa', 'delete', filter.id, 'bg-danger-100 text-danger-700'));

                item.appendChild(head);
                item.appendChild(query);
                item.appendChild(actions);
                list.appendChild(item);
            });
        });
    }

    async function copyFilterLink(button) {
        const url = window.location.href;
        try {
            await navigator.clipboard.writeText(url);
            toast('Đã copy link bộ lọc');
        } catch (error) {
            const temp = document.createElement('input');
            temp.value = url;
            document.body.appendChild(temp);
            temp.select();
            document.execCommand('copy');
            temp.remove();
            toast('Đã copy link bộ lọc');
        }
        if (button) {
            button.classList.add('btn-primary');
            window.setTimeout(() => button.classList.remove('btn-primary'), 900);
        }
    }

    function saveFilter() {
        if (!hasMeaningfulQuery()) {
            toast('Chưa có bộ lọc để lưu');
            return;
        }
        const name = promptFilterName('Đặt tên cho bộ lọc này');
        if (!name) return;
        const now = new Date().toISOString();
        const filters = readFilters();
        filters.unshift({
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            name,
            query: currentQuery(),
            createdAt: now,
            updatedAt: now,
        });
        writeFilters(filters.slice(0, 30));
        toast('Đã lưu bộ lọc');
    }

    function applySavedFilter(id) {
        const filter = readFilters().find((item) => item.id === id);
        if (!filter) return;
        window.location.href = window.location.pathname + filter.query;
    }

    function renameSavedFilter(id) {
        const filters = readFilters();
        const filter = filters.find((item) => item.id === id);
        if (!filter) return;
        const name = promptFilterName('Đổi tên bộ lọc', filter.name);
        if (!name) return;
        filter.name = name;
        filter.updatedAt = new Date().toISOString();
        writeFilters(filters);
        toast('Đã đổi tên bộ lọc');
    }

    function overwriteSavedFilter(id) {
        if (!hasMeaningfulQuery()) {
            toast('Chưa có bộ lọc hiện tại để ghi đè');
            return;
        }
        const filters = readFilters();
        const filter = filters.find((item) => item.id === id);
        if (!filter) return;
        if (!window.confirm(`Ghi đè "${filter.name}" bằng bộ lọc hiện tại?`)) return;
        filter.query = currentQuery();
        filter.updatedAt = new Date().toISOString();
        writeFilters(filters);
        toast('Đã ghi đè bộ lọc');
    }

    function deleteSavedFilter(id) {
        const filters = readFilters();
        const filter = filters.find((item) => item.id === id);
        if (!filter) return;
        if (!window.confirm(`Xóa bộ lọc "${filter.name}"?`)) return;
        writeFilters(filters.filter((item) => item.id !== id));
        toast('Đã xóa bộ lọc');
    }

    document.addEventListener('click', function (event) {
        const copyButton = event.target.closest('.js-copy-filter-link');
        if (copyButton) {
            event.preventDefault();
            copyFilterLink(copyButton);
            return;
        }

        const saveButton = event.target.closest('.js-save-filter');
        if (saveButton) {
            event.preventDefault();
            saveFilter();
            return;
        }

        const savedActionButton = event.target.closest('[data-saved-filter-action]');
        if (savedActionButton) {
            event.preventDefault();
            const action = savedActionButton.dataset.savedFilterAction;
            const id = savedActionButton.dataset.savedFilterId;
            if (action === 'apply') applySavedFilter(id);
            if (action === 'rename') renameSavedFilter(id);
            if (action === 'overwrite') overwriteSavedFilter(id);
            if (action === 'delete') deleteSavedFilter(id);
        }
    });

    function enhanceLongFilterSelects() {
        document.querySelectorAll('.admin-filter-form select, .admin-filter-panel select').forEach((select) => {
            if (select.dataset.searchEnhanced || select.options.length < 12 || select.multiple) {
                return;
            }
            select.dataset.searchEnhanced = '1';
            const optionData = Array.from(select.options).map((option) => ({
                value: option.value,
                text: option.textContent,
            }));
            const input = document.createElement('input');
            input.type = 'search';
            input.className = 'form-input admin-select-search';
            input.placeholder = 'Gõ để lọc danh sách...';
            input.setAttribute('aria-label', 'Lọc lựa chọn');
            select.parentNode.insertBefore(input, select);
            input.addEventListener('input', () => {
                const keyword = input.value.trim().toLowerCase();
                const currentValue = select.value;
                const matches = optionData.filter((item, index) => (
                    index === 0 ||
                    item.value === currentValue ||
                    item.text.toLowerCase().includes(keyword)
                ));
                select.innerHTML = '';
                matches.forEach((item) => {
                    const option = document.createElement('option');
                    option.value = item.value;
                    option.textContent = item.text;
                    select.appendChild(option);
                });
                select.value = currentValue;
            });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        renderSavedFilters();
        enhanceLongFilterSelects();
    });
})();
