/* eslint-env browser */
/* global FullCalendar, flatpickr, bootstrap, applyClientSearchFilter, Intl */
/* eslint no-empty: ["error", { "allowEmptyCatch": true }] */

function __initAgendaApp() {
    const BASE = (typeof window !== 'undefined' && window.__AGENDA_BASE__) ? window.__AGENDA_BASE__ : '';
    const staticBase = BASE + '/static';
    Promise.all([
        fetch(staticBase + '/event-popover.html').then(res => res.text()),
        fetch(staticBase + '/event-contextmenu.html').then(res => res.text()),
        fetch(staticBase + '/event-detail-popover.html').then(res => res.text()),
        fetch(staticBase + '/settings-menu.html').then(res => res.text()),
        fetch(staticBase + '/search-menu.html').then(res => res.text())
    ]).then(([popoverHtml, contextHtml, detailPopoverHtml, settingsMenuHtml, searchMenuHtml]) => {
        document.getElementById('popover-container').innerHTML = popoverHtml;
        document.getElementById('contextmenu-container').innerHTML = contextHtml;
        document.body.insertAdjacentHTML('beforeend', detailPopoverHtml);
        document.getElementById('settingsmenu-container').innerHTML = settingsMenuHtml;
        // inserir menu de busca
        let searchContainer = document.getElementById('searchmenu-container');
        if (!searchContainer) {
            searchContainer = document.createElement('div');
            searchContainer.id = 'searchmenu-container';
            document.body.appendChild(searchContainer);
        }
        searchContainer.innerHTML = searchMenuHtml;

        // Inicialização global dos pickers para garantir formato BR mesmo antes da seleção
        try {
            const s1 = document.getElementById('popoverEventStart');
            const e1 = document.getElementById('popoverEventEnd');
            const sD = document.getElementById('popoverEventStartDate');
            const eD = document.getElementById('popoverEventEndDate');
            if (window.flatpickr && s1 && e1 && sD && eD) {
                const fpDateOpts = {
                    enableTime: false,
                    allowInput: true,
                    locale: (window.flatpickr && window.flatpickr.l10ns && window.flatpickr.l10ns.pt) ? window.flatpickr.l10ns.pt : 'pt',
                    dateFormat: 'Y-m-d',
                    altInput: true,
                    altFormat: 'd/m/Y'
                };
                const fpDateTimeOpts = {
                    enableTime: true,
                    time_24hr: true,
                    allowInput: true,
                    minuteIncrement: 5,
                    locale: (window.flatpickr && window.flatpickr.l10ns && window.flatpickr.l10ns.pt) ? window.flatpickr.l10ns.pt : 'pt',
                    dateFormat: 'Y-m-d\\TH:i',
                    altInput: true,
                    altFormat: 'd/m/Y H:i'
                };
                // Pickers são destruídos/recriados quando o modo muda (allDay vs time)
                flatpickr(s1, fpDateTimeOpts);
                flatpickr(e1, fpDateTimeOpts);
                flatpickr(sD, fpDateOpts);
                flatpickr(eD, fpDateOpts);
            }
        } catch (e) {
            /* noop */
        }

        // Aplicar tema salvo (se houver)
        const savedTheme = localStorage.getItem('calendarTheme') || 'default';
        applyTheme(savedTheme, false);

        const plugins = [];
        if (window.FullCalendar) {
            if (FullCalendar.dayGridPlugin) plugins.push(FullCalendar.dayGridPlugin);
            if (FullCalendar.timeGridPlugin) plugins.push(FullCalendar.timeGridPlugin);
            if (FullCalendar.listPlugin) plugins.push(FullCalendar.listPlugin);
            if (FullCalendar.interactionPlugin) plugins.push(FullCalendar.interactionPlugin);
            if (FullCalendar.multiMonthPlugin) plugins.push(FullCalendar.multiMonthPlugin);
            if (FullCalendar.scrollGridPlugin) plugins.push(FullCalendar.scrollGridPlugin);
            if (FullCalendar.adaptivePlugin) plugins.push(FullCalendar.adaptivePlugin);
        }
        const calendarEl = document.getElementById('calendar');
        // Utils: debounce and rAF-throttle
        function debounce(fn, wait = 200) {
            let t;
            return function (...args) {
                clearTimeout(t);
                t = setTimeout(() => fn.apply(this, args), wait);
            };
        }
        function rafThrottle(fn) {
            let scheduled = false;
            let lastArgs = null;
            return function (...args) {
                lastArgs = args;
                if (scheduled) return;
                scheduled = true;
                requestAnimationFrame(() => {
                    scheduled = false;
                    fn.apply(this, lastArgs);
                });
            };
        }
        // Toast helper (Bootstrap 5)
        function showToast(message, variant = 'success', delay = 2500) {
            try {
                let cont = document.getElementById('toastContainer');
                if (!cont) {
                    cont = document.createElement('div');
                    cont.id = 'toastContainer';
                    cont.style.position = 'fixed';
                    cont.style.bottom = '16px';
                    cont.style.right = '16px';
                    cont.style.zIndex = '5000';
                    cont.style.display = 'flex';
                    cont.style.flexDirection = 'column';
                    cont.style.gap = '8px';
                    document.body.appendChild(cont);
                }
                const toastEl = document.createElement('div');
                toastEl.className = `toast align-items-center text-bg-${variant} border-0`;
                toastEl.setAttribute('role', 'alert');
                toastEl.setAttribute('aria-live', 'assertive');
                toastEl.setAttribute('aria-atomic', 'true');
                toastEl.innerHTML = `
          <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
          </div>`;
                cont.appendChild(toastEl);
                if (window.bootstrap && window.bootstrap.Toast) {
                    const t = new bootstrap.Toast(toastEl, { delay, autohide: true });
                    t.show();
                    toastEl.addEventListener('hidden.bs.toast', () => { try { toastEl.remove(); } catch (e) { } });
                } else {
                    // Fallback: simple timed removal
                    toastEl.style.display = 'block';
                    setTimeout(() => { try { toastEl.remove(); } catch (e) { } }, delay);
                }
            } catch (e) { /* noop */ }
        }
        // Aviso quando nenhum dentista selecionado
        let emptyNoticeTimer = null;
        function updateEmptyFilterNotice() {
            try {
                const el = document.getElementById('filterNotice');
                if (!el) return;
                const ids = loadSelectedDentists();
                const includeUn = loadIncludeUnassigned();
                // Mostrar aviso somente quando nada está marcado:
                // nem dentistas específicos nem "Todos (sem dentista)"
                const show = (!ids || ids.length === 0) && !includeUn;
                // clear any pending
                if (emptyNoticeTimer) { clearTimeout(emptyNoticeTimer); emptyNoticeTimer = null; }
                if (show) {
                    // small delay to avoid flashing before initial state settles
                    emptyNoticeTimer = setTimeout(() => {
                        try {
                            el.style.display = 'block';
                        } catch (e) { }
                    }, 350);
                } else {
                    el.style.display = 'none';
                }
            } catch (e) { }
        }
        const updateEmptyFilterNoticeDeb = debounce(updateEmptyFilterNotice, 200);

        // ===== Shared events cache (main + mini) =====
        const sharedEventsCache = {
            key: null,     // string key for filters: dentists|includeUn|q
            start: null,   // Date coverage start (inclusive)
            end: null,     // Date coverage end (exclusive)
            events: []     // array of event objects as returned by server
        };
        // In-flight de-duplication for events fetches: key -> Promise
        const pendingEventsFetches = new Map();
        function buildCacheKey() {
            const ids = loadSelectedDentists() || [];
            const includeUn = loadIncludeUnassigned() ? '1' : '';
            const q = loadSearchQuery() || '';
            return `${ids.sort((a, b) => a - b).join(',')}|${includeUn}|${q}`;
        }
        function ymdhmss(d) {
            // format YYYY-MM-DDTHH:MM:SS without timezone
            const pad = n => String(n).padStart(2, '0');
            return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
        }
        function startOfDay(d) { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; }
    // removed unused helpers endOfDayExclusive and unionRanges (lint cleanup)
        function storeEventsToCache(list, covStart, covEnd, key) {
            const sameKey = sharedEventsCache.key === key;
            if (!sameKey || !sharedEventsCache.start || !sharedEventsCache.end) {
                sharedEventsCache.key = key;
                sharedEventsCache.start = covStart;
                sharedEventsCache.end = covEnd;
                sharedEventsCache.events = Array.isArray(list) ? list.slice() : [];
                return;
            }
            // merge events by id and expand coverage
            const byId = new Map(sharedEventsCache.events.map(e => [String(e.id), e]));
            (list || []).forEach(e => byId.set(String(e.id), e));
            sharedEventsCache.events = Array.from(byId.values());
            if (covStart && covStart < sharedEventsCache.start) sharedEventsCache.start = covStart;
            if (covEnd && covEnd > sharedEventsCache.end) sharedEventsCache.end = covEnd;
        }
        function cacheCoversRange(rangeStart, rangeEnd, key) {
            if (sharedEventsCache.key !== key) return false;
            if (!sharedEventsCache.start || !sharedEventsCache.end) return false;
            return sharedEventsCache.start <= rangeStart && sharedEventsCache.end >= rangeEnd;
        }
        function eventsFromCache(rangeStart, rangeEnd, key) {
            if (sharedEventsCache.key !== key) return [];
            const rs = rangeStart.getTime();
            const re = rangeEnd.getTime();
            return (sharedEventsCache.events || []).filter(ev => {
                try {
                    const s = ev.start ? new Date(ev.start.replace(' ', 'T')) : null;
                    const e = ev.end ? new Date(ev.end.replace(' ', 'T')) : null;
                    if (s && e) return e.getTime() >= rs && s.getTime() < re;
                    if (s && !e) return s.getTime() < re; // open-ended
                    return false;
                } catch (e) { return false; }
            });
        }
        // Mutate a cached event by id (keeps coverage and key); returns updated obj or null
        function updateEventInCacheById(id, changes) {
            try {
                const list = sharedEventsCache.events || [];
                const idx = list.findIndex(e => String(e.id) === String(id));
                if (idx === -1) return null;
                const old = list[idx] || {};
                const updated = { ...old, ...changes };
                // merge extended props if provided nested (not used now, but safe)
                if (old.extendedProps || changes?.extendedProps) {
                    updated.extendedProps = { ...(old.extendedProps || {}), ...(changes.extendedProps || {}) };
                }
                list[idx] = updated;
                sharedEventsCache.events = list;
                return updated;
            } catch (e) { return null; }
        }
        function removeEventFromCacheById(id) {
            try {
                if (!sharedEventsCache.events) return;
                sharedEventsCache.events = sharedEventsCache.events.filter(e => String(e.id) !== String(id));
            } catch (e) { /* noop */ }
        }
        function addEventToCache(ev) {
            try {
                if (!sharedEventsCache.events) sharedEventsCache.events = [];
                // avoid duplicates by id
                const id = ev && ev.id != null ? String(ev.id) : null;
                if (id) {
                    const exists = sharedEventsCache.events.some(e => String(e.id) === id);
                    if (exists) return;
                }
                sharedEventsCache.events.push(ev);
            } catch (e) { /* noop */ }
        }
        // Helper: detect a Brazilian phone number within free text (first match)
        function extractPhoneFromText(text) {
            if (!text) return null;
            try {
                // Supports formats like: +55 11 91234-5678, (11) 91234-5678, 112345-6789, 1234-5678, 9 1234-5678
                const re = /(?:\+?55[\s\-.]?)?(?:\(?\d{2}\)?[\s\-.]?)?(?:9\d{4}|\d{4})[\s\-.]?\d{4}\b/;
                const m = String(text).match(re);
                return m ? m[0].trim() : null;
            } catch (e) {
                return null;
            }
        }
        // Helper: format Date to local 'YYYY-MM-DDTHH:MM' string
        function formatLocalYmdHm(d) {
            const pad = (n) => String(n).padStart(2, '0');
            const y = d.getFullYear();
            const m = pad(d.getMonth() + 1);
            const day = pad(d.getDate());
            const h = pad(d.getHours());
            const min = pad(d.getMinutes());
            return `${y}-${m}-${day}T${h}:${min}`;
        }

        // Weekends setting (for week view)
        function getWeekendsSetting() {
            const v = localStorage.getItem('timeGridWeek_weekends');
            return v === null ? true : v === 'true';
        }

        function setWeekendsSetting(val) {
            try {
                localStorage.setItem('timeGridWeek_weekends', String(!!val));
            } catch (e) { }
        }

        // Client-side holiday cache
        let holidayDates = new Set(); // visible set 'YYYY-MM-DD'
        let holidayMeta = {}; // visible map date -> meta
        const dayCellEls = {}; // date -> [elements]
        // Session in-memory cache by year to avoid repeated GETs
        const holidaysYearCache = {}; // { [year]: { dates:Set, meta:{[date]:meta} } }
        const holidaysYearPending = {}; // { [year]: Promise }

        function toLocalISO(date) {
            const pad = (n) => String(n).padStart(2, '0');
            return [
                date.getFullYear(),
                pad(date.getMonth() + 1),
                pad(date.getDate())
            ].join('-');
        }

        function syncHolidayHighlight() {
            Object.keys(dayCellEls).forEach(d => {
                (dayCellEls[d] || []).forEach(el => {
                    if (!el || !el.classList) return;
                    if (holidayDates.has(d)) {
                        el.classList.add('fc-day-holiday');
                        const meta = holidayMeta[d];
                        if (meta && el.setAttribute) {
                            el.setAttribute('title', meta.name);
                        }
                    } else {
                        el.classList.remove('fc-day-holiday');
                        if (el.getAttribute && el.getAttribute('title')) {
                            el.removeAttribute('title');
                        }
                    }
                });
            });
        }

        function ymdFromDate(d) {
            const pad = n => String(n).padStart(2, '0');
            return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
        }

        function yearsInRangeInclusive(startDate, endDateInclusive) {
            const ys = [];
            const y1 = startDate.getFullYear();
            const y2 = endDateInclusive.getFullYear();
            for (let y = y1; y <= y2; y++) ys.push(y);
            return ys;
        }

        function ensureYearCached(year) {
            if (holidaysYearCache[year]) return Promise.resolve();
            if (holidaysYearPending[year]) return holidaysYearPending[year];
            const p = fetch(`${BASE}/holidays/year?year=${year}`)
                .then(r => r.json())
                .then(list => {
                    const dates = new Set(list.map(h => h.date));
                    const meta = {};
                    list.forEach(h => {
                        meta[h.date] = {
                            name: h.name,
                            type: h.type,
                            level: h.level
                        };
                    });
                    holidaysYearCache[year] = {
                        dates,
                        meta
                    };
                })
                .catch(() => {
                    /* swallow; leave uncached to retry later */
                })
                .finally(() => {
                    delete holidaysYearPending[year];
                });
            holidaysYearPending[year] = p;
            return p;
        }

        function ensureRangeCached(startDate, endDateInclusive) {
            const years = yearsInRangeInclusive(startDate, endDateInclusive);
            return Promise.all(years.map(y => ensureYearCached(y)));
        }

        function buildVisibleFromCache(startDate, endDateInclusive) {
            const resDates = new Set();
            const resMeta = {};
            let d = new Date(startDate);
            while (d <= endDateInclusive) {
                const y = d.getFullYear();
                const yc = holidaysYearCache[y];
                const key = ymdFromDate(d);
                if (yc && yc.dates.has(key)) {
                    resDates.add(key);
                    if (yc.meta[key]) resMeta[key] = yc.meta[key];
                }
                d.setDate(d.getDate() + 1);
            }
            return {
                dates: resDates,
                meta: resMeta
            };
        }

        function updateHolidaysForCurrentView() {
            const view = calendar.view;
            if (!(view && view.currentStart && view.currentEnd)) return;
            const start = new Date(view.currentStart);
            const endInc = new Date(view.currentEnd);
            endInc.setDate(endInc.getDate() - 1); // end is exclusive
            return ensureRangeCached(start, endInc).then(() => {
                const built = buildVisibleFromCache(start, endInc);
                holidayDates = built.dates;
                holidayMeta = built.meta;
                syncHolidayHighlight();
            });
        }

        // Estado de filtro de dentistas (persistido no navegador)
        const storageKey = 'selectedDentists';
        const storageKeyUnassigned = 'includeUnassigned';

        function saveSelectedDentists(ids) {
            try {
                localStorage.setItem(storageKey, JSON.stringify(ids));
            } catch (e) { }
        }

        function loadSelectedDentists() {
            try {
                const v = localStorage.getItem(storageKey);
                if (!v) return [];
                const arr = JSON.parse(v);
                return Array.isArray(arr) ? arr : [];
            } catch (e) {
                return [];
            }
        }

        function saveIncludeUnassigned(val) {
            try {
                localStorage.setItem(storageKeyUnassigned, String(!!val));
            } catch (e) { }
        }

        function loadIncludeUnassigned() {
            try {
                return localStorage.getItem(storageKeyUnassigned) === 'true';
            } catch (e) {
                return false;
            }
        }

        function colorForDentist(d) {
            // fallback padrão se não houver cor: paleta baseada em id
            if (d && d.color) return d.color;
            const palette = ['#2563eb', '#16a34a', '#dc2626', '#9333ea', '#ea580c', '#0891b2', '#4f46e5', '#059669'];
            const id = d && d.id ? Number(d.id) : 0;
            return palette[Math.abs(id) % palette.length];
        }
        // Renderizar lista lateral de dentistas
        const dentistsCache = {
            list: [],
            map: {}
        };

        // Client-side dentists loader with memoization + TTL cache in localStorage
        const DENTISTS_CACHE_KEY = 'dentistsCacheV1';
        const DENTISTS_CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes
        let dentistsPending = null; // Promise in-flight

        function loadDentistsFromStorage() {
            try {
                const raw = localStorage.getItem(DENTISTS_CACHE_KEY);
                if (!raw) return null;
                const obj = JSON.parse(raw);
                if (!obj || !Array.isArray(obj.list) || !obj.at) return null;
                if ((Date.now() - obj.at) > DENTISTS_CACHE_TTL_MS) return null;
                return obj.list;
            } catch (e) { return null; }
        }

        function saveDentistsToStorage(list) {
            try {
                localStorage.setItem(DENTISTS_CACHE_KEY, JSON.stringify({ list, at: Date.now() }));
            } catch (e) { }
        }

        // Force repaint of dentist color bars for all rendered instances of a given event id
        function repaintDentistBarsForEvent(eventId, pid) {
            try {
                const els = document.querySelectorAll(`[data-eid="${eventId}"]`);
                let col = null;
                if (pid != null && dentistsCache && dentistsCache.map && dentistsCache.map[pid]) {
                    const d = dentistsCache.map[pid];
                    col = colorForDentist(d);
                }
                els.forEach(el => {
                    // Ensure classes exist for styling consistency
                    if (col) {
                        el.classList.add('dentist-rightbar');
                        el.classList.add('dentist-leftbar');
                        el.style.borderRight = `6px solid ${col}`;
                        el.style.borderLeft = `2px solid ${col}`;
                        try { el.style.boxShadow = `inset -6px 0 0 0 ${col}`; } catch (e) { }
                    } else {
                        // No dentist: remove custom bars
                        el.style.borderRight = '';
                        el.style.borderLeft = '';
                        try { el.style.boxShadow = ''; } catch (e) { }
                        el.classList.remove('dentist-rightbar');
                        el.classList.remove('dentist-leftbar');
                    }
                });
            } catch (e) { }
        }

        function fetchDentistsOnce(force = false) {
            // If not forcing and already in memory, resolve immediately
            if (!force && dentistsCache.list && dentistsCache.list.length) {
                return Promise.resolve(dentistsCache.list);
            }
            // Try storage cache unless forcing
            if (!force) {
                const fromStorage = loadDentistsFromStorage();
                if (fromStorage) {
                    dentistsCache.list = fromStorage.map(d => ({ id: Number(d.id), nome: d.nome, color: d.color || null }));
                    dentistsCache.map = Object.fromEntries(dentistsCache.list.map(d => [d.id, d]));
                    return Promise.resolve(dentistsCache.list);
                }
            }
            if (dentistsPending) return dentistsPending;
            const url = BASE + '/dentists' + (force ? (`?_t=${Date.now()}`) : '');
            const fetchOpts = force ? { cache: 'no-store', headers: { 'Cache-Control': 'no-cache' } } : {};
            dentistsPending = fetch(url, fetchOpts)
                .then(r => {
                    if (r.status === 304) {
                        // Not modified; return what we have (or empty)
                        return dentistsCache.list || [];
                    }
                    return r.json();
                })
                .then(list => {
                    const norm = Array.isArray(list) ? list.map(d => ({
                        id: Number(d.id),
                        nome: d.nome || String(d.id),
                        color: d.color || null
                    })) : [];
                    dentistsCache.list = norm;
                    dentistsCache.map = Object.fromEntries(norm.map(d => [d.id, d]));
                    try { saveDentistsToStorage(norm); } catch (e) { }
                    // If no saved selection, default to all dentists to avoid empty results on first load
                    try {
                        const saved = loadSelectedDentists();
                        if (!saved || saved.length === 0) {
                            saveSelectedDentists(norm.map(d => d.id));
                        }
                    } catch (e) { }
                    return norm;
                })
                .finally(() => { dentistsPending = null; });
            return dentistsPending;
        }

        function renderDentistsSidebar(list) {
            const cont = document.getElementById('dentistsContainer');
            if (!cont) return;
            // restaurar estado 'Todos (sem dentista)'
            try {
                const cbAll = document.getElementById('dent_all');
                if (cbAll) {
                    cbAll.checked = loadIncludeUnassigned();
                    cbAll.onchange = () => {
                        saveIncludeUnassigned(cbAll.checked);
                        try {
                            calendar.refetchEvents();
                        } catch (e) { }
                        updateEmptyFilterNoticeDeb();
                        // manter mini calendário em sincronia com filtros
                        try {
                            if (window.__miniCalendar) window.__miniCalendar.refetchEvents();
                        } catch (e) { }
                        try {
                            if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators();
                        } catch (e) { }
                    };
                }
            } catch (e) { }
            const selected = new Set(loadSelectedDentists());
            const ul = document.createElement('ul');
            ul.className = 'dentist-list';
            list.forEach(d => {
                const li = document.createElement('li');
                li.className = 'dentist-item d-flex align-items-center gap-2 py-1 border-bottom';
                const color = colorForDentist(d);
                li.innerHTML = `
                            <input type="checkbox" class="form-check-input" id="dent_${d.id}" ${selected.has(d.id) ? 'checked' : ''} />
                            <span class="dentist-color" style="background:${color}"></span>
                            <label class="form-check-label" for="dent_${d.id}">${d.nome || ('Dentista ' + d.id)}</label>
                        `;
                ul.appendChild(li);
            });
            // remove borda do último item
            ul.lastElementChild && ul.lastElementChild.classList.remove('border-bottom');
            cont.innerHTML = '';
            cont.appendChild(ul);
            cont.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                cb.addEventListener('change', () => {
                    const ids = Array.from(cont.querySelectorAll('input[type="checkbox"]'))
                        .filter(x => x.checked)
                        .map(x => parseInt(x.id.replace('dent_', ''), 10))
                        .filter(n => Number.isFinite(n));
                    saveSelectedDentists(ids);
                    try {
                        calendar.refetchEvents();
                    } catch (e) { }
                    updateEmptyFilterNotice();
                    // manter mini calendário em sincronia com filtros
                    try {
                        if (window.__miniCalendar) window.__miniCalendar.refetchEvents();
                    } catch (e) { }
                    try {
                        if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators();
                    } catch (e) { }
                    // Auto selecionar no popover se houver exatamente um dentista selecionado
                    try {
                        const sel = document.getElementById('popoverDentist');
                        if (sel) {
                            if (ids.length === 1) sel.value = String(ids[0]);
                            else if (ids.length === 0) sel.value = '';
                        }
                    } catch (e) { }
                });
            });
        }

        const calendar = new FullCalendar.Calendar(calendarEl, {
            themeSystem: 'bootstrap5',
            locale: 'pt-br',
            initialView: 'timeGridWeek',
            // Garantir 24h em toda a UI do FullCalendar
            eventTimeFormat: {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            },
            slotLabelFormat: {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            },
            // Não depender de ícones externos: sobrescrever botões com texto
            customButtons: {
                prev: {
                    text: '‹',
                    click: () => calendar.prev()
                },
                next: {
                    text: '›',
                    click: () => calendar.next()
                },
                prevYear: {
                    text: '≪',
                    click: () => {
                        const d = calendar.getDate();
                        calendar.gotoDate(new Date(
                            d.getFullYear(), d.getMonth() - 1, d.getDate()
                        ));
                    }
                },
                nextYear: {
                    text: '≫',
                    click: () => {
                        const d = calendar.getDate();
                        calendar.gotoDate(new Date(
                            d.getFullYear(), d.getMonth() + 1, d.getDate()
                        ));
                    }
                },
                settings: {
                    text: 'Configurações',
                    click: function () {
                        const btn = calendarEl.querySelector('.fc-settings-button');
                        if (!btn) return;
                        const wrap = document.getElementById('settingsmenu-container');
                        if (wrap && wrap.childElementCount === 0) {
                            fetch(staticBase + '/settings-menu.html')
                                .then(r => r.text())
                                .then(html => { wrap.innerHTML = html; toggleSettingsMenu(btn); })
                                .catch(() => toggleSettingsMenu(btn));
                            return;
                        }
                        toggleSettingsMenu(btn);
                    }
                },
                search: {
                    text: 'Buscar',
                    click: function () {
                        const btn = calendarEl.querySelector('.fc-search-button');
                        if (!btn) return;
                        let wrap = document.getElementById('searchmenu-container');
                        if (!wrap) {
                            wrap = document.createElement('div');
                            wrap.id = 'searchmenu-container';
                            document.body.appendChild(wrap);
                        }
                        if (wrap.childElementCount === 0) {
                            fetch(staticBase + '/search-menu.html')
                                .then(r => r.text())
                                .then(html => { wrap.innerHTML = html; toggleSearchMenu(btn); })
                                .catch(() => toggleSearchMenu(btn));
                            return;
                        }
                        toggleSearchMenu(btn);
                    }
                }
            },
            headerToolbar: {
                left: 'prev,next today settings search',
                center: 'title',
                right: 'prevYear,nextYear dayGridMonth,timeGridWeek,timeGridDay,listWeek,multiMonthYear'
            },
            buttonText: {
                today: 'Hoje',
                month: 'Mês',
                week: 'Semana',
                day: 'Dia',
                list: 'Lista',
                listWeek: 'Lista',
                listMonth: 'Lista mês',
                listYear: 'Lista ano',
                dayGridMonth: 'Mês',
                timeGridWeek: 'Semana',
                timeGridDay: 'Dia',
                multiMonthYear: 'Ano'
            },
            moreLinkText: function (n) {
                return `+${n} mais`;
            },
            views: {
                dayGridMonth: {
                    eventDisplay: 'block'
                },
                multiMonthYear: {
                    type: 'multiMonth',
                    duration: {
                        years: 1
                    },
                    // boas colunas para layout 12 meses (3 col x 4 linhas)
                    multiMonthMaxColumns: 3,
                    eventDisplay: 'block',
                    buttonText: 'Ano'
                }
            },
            plugins: plugins,
            dayCellClassNames: function (arg) {
                const iso = toLocalISO(arg.date);
                return holidayDates.has(iso) ? ['fc-day-holiday'] : [];
            },
            dayCellDidMount: function (arg) {
                const iso = toLocalISO(arg.date);
                if (!dayCellEls[iso]) dayCellEls[iso] = [];
                dayCellEls[iso].push(arg.el);
                // apply immediately if data already loaded
                if (holidayDates.has(iso)) {
                    arg.el.classList.add('fc-day-holiday');
                    const meta = holidayMeta[iso];
                    if (meta && arg.el && arg.el.setAttribute) {
                        arg.el.setAttribute('title', meta.name);
                    }
                }
            },
            selectable: true,
            editable: true,
            nowIndicator: true,
            navLinks: true,
            weekends: getWeekendsSetting(),
            eventContent: function (arg) {
                // Semana: mostrar apenas hora inicial + título em uma linha
                if (arg.view.type === 'timeGridWeek') {
                    const isAllDay = arg.event.allDay;
                    let timeStr = '';
                    if (!isAllDay && arg.event.start) {
                        try {
                            timeStr = new Intl.DateTimeFormat('pt-BR', {
                                hour: '2-digit',
                                minute: '2-digit',
                                hour12: false
                            }).format(arg.event.start);
                        } catch (e) {
                            /* fallback */
                            const d = arg.event.start;
                            const hh = String(d.getHours()).padStart(2, '0');
                            const mm = String(d.getMinutes()).padStart(2, '0');
                            timeStr = `${hh}:${mm}`;
                        }
                    }
                    const title = arg.event.title || '';
                    // calcular duração em minutos
                    let durationMin = 0;
                    if (!isAllDay && arg.event.start && arg.event.end) {
                        durationMin = Math.max(0, Math.round((arg.event.end.getTime() - arg.event.start.getTime()) / 60000));
                    } else if (!isAllDay && arg.event.start && !arg.event.end) {
                        // sem fim explícito: assumir 60min, comum em consultas
                        durationMin = 60;
                    }
                    let html;
                    if (durationMin > 30) {
                        // duas linhas: título em cima (negrito), hora embaixo (normal)
                        const timeLine = timeStr ? `<div class="fc-event-time-start">${timeStr}</div>` : '';
                        html = `<div class="fc-event-main-custom two-line"><div class="fc-event-title">${title}</div>${timeLine}</div>`;
                    } else {
                        // linha única: Título + hora
                        const timeInline = timeStr ? `<span class="fc-event-time-start"> ${timeStr}</span>` : '';
                        html = `<div class="fc-event-main-custom"><span class="fc-event-title">${title}</span>${timeInline}</div>`;
                    }

                    return {
                        html
                    };
                }
                // Dia: Nome (negrito) - descrição do evento
                if (arg.view.type === 'timeGridDay') {
                    const title = arg.event.title || '';
                    const notes = (arg.event.extendedProps && arg.event.extendedProps.notes) ? arg.event.extendedProps.notes : '';
                    // calcular duração em minutos (para escalar fonte)
                    let durationMin = 0;
                    if (!arg.event.allDay && arg.event.start) {
                        if (arg.event.end) {
                            durationMin = Math.max(0, Math.round((arg.event.end.getTime() - arg.event.start.getTime()) / 60000));
                        } else {
                            durationMin = 60; // padrão quando sem fim explícito
                        }
                    }
                    let sizeClass = '';
                    if (durationMin >= 120) sizeClass = ' size-large';
                    else if (durationMin >= 60) sizeClass = ' size-medium';
                    const sep = notes ? ' - ' : '';
                    const html = `<div class="fc-event-main-custom${sizeClass}"><span class="fc-event-title fw-bold">${title}</span>${sep}<span class="fc-event-notes">${notes}</span></div>`;
                    return {
                        html
                    };
                }
                // Lista: Nome (negrito) - descrição
                if (arg.view.type && arg.view.type.startsWith('list')) {
                    const title = arg.event.title || '';
                    const notes = (arg.event.extendedProps && arg.event.extendedProps.notes) ? arg.event.extendedProps.notes : '';
                    const sep = notes ? ' - ' : '';
                    const html = `<span class="fc-event-title fw-bold">${title}</span>${sep}<span class="fc-event-notes">${notes}</span>`;
                    return {
                        html
                    };
                }
                // Mês: título primeiro e horário em seguida numa única linha (mantém fundo colorido padrão)
                if (arg.view.type === 'dayGridMonth') {
                    const isAllDay = arg.event.allDay;
                    let timeStr = '';
                    if (!isAllDay && arg.event.start) {
                        try {
                            timeStr = new Intl.DateTimeFormat('pt-BR', {
                                hour: '2-digit',
                                minute: '2-digit',
                                hour12: false
                            }).format(arg.event.start);
                        } catch (e) {
                            const d = arg.event.start;
                            const hh = String(d.getHours()).padStart(2, '0');
                            const mm = String(d.getMinutes()).padStart(2, '0');
                            timeStr = `${hh}:${mm}`;
                        }
                    }
                    const title = arg.event.title || '';
                    const timeInline = timeStr ? `<span class="fc-event-time-start"> ${timeStr}</span>` : '';
                    const html = `<div class="fc-event-main-custom fc-month-line"><span class="fc-event-title">${title}</span>${timeInline}</div>`;
                    return {
                        html
                    };
                }
                // Visualização Anual (multiMonth): mesmo layout do mês
                if (arg.view.type && arg.view.type.startsWith('multiMonth')) {
                    const isAllDay = arg.event.allDay;
                    let timeStr = '';
                    if (!isAllDay && arg.event.start) {
                        try {
                            timeStr = new Intl.DateTimeFormat('pt-BR', {
                                hour: '2-digit',
                                minute: '2-digit',
                                hour12: false
                            }).format(arg.event.start);
                        } catch (e) {
                            const d = arg.event.start;
                            const hh = String(d.getHours()).padStart(2, '0');
                            const mm = String(d.getMinutes()).padStart(2, '0');
                            timeStr = `${hh}:${mm}`;
                        }
                    }
                    const title = arg.event.title || '';
                    const timeInline = timeStr ? `<span class="fc-event-time-start"> ${timeStr}</span>` : '';
                    const html = `<div class="fc-event-main-custom fc-month-line"><span class="fc-event-title">${title}</span>${timeInline}</div>`;
                    return {
                        html
                    };
                }
                // Outras visões: padrão
                return undefined;
            },
        events: function (fetchInfo, success, failure) {
                try {
                    const key = buildCacheKey();
            // Fetch the actual visible range for the current view, with a small pad
            const vs = new Date(fetchInfo.start);
            const ve = new Date(fetchInfo.end);
            const padStart = new Date(vs);
            padStart.setDate(padStart.getDate() - 2);
            const padEnd = new Date(ve);
            padEnd.setDate(padEnd.getDate() + 2);
            const covStart = startOfDay(padStart);
            const covEnd = startOfDay(padEnd);
            // Use only dates for de-duplication here; avoid referencing `calendar` before init
            const dedupKey = `${key}|${covStart.toISOString()}|${covEnd.toISOString()}`;
                    // If cache covers this padded month, just serve the requested subrange
                    if (cacheCoversRange(padStart, padEnd, key)) {
                        const result = eventsFromCache(new Date(fetchInfo.start), new Date(fetchInfo.end), key);
                        success(result);
                        try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                        try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) { }
                        return;
                    }
                    // If an identical fetch is in-flight, wait for it and then serve from cache
                    if (pendingEventsFetches.has(dedupKey)) {
                        pendingEventsFetches.get(dedupKey)
                            .then(() => {
                                const result = eventsFromCache(new Date(fetchInfo.start), new Date(fetchInfo.end), key);
                                success(result);
                                try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                                try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) { }
                            })
                            .catch(err => {
                                if (typeof failure === 'function') failure(err instanceof Error ? err : new Error('Failed to load events'));
                                else success([]);
                            });
                        return;
                    }
                    // Build query params for padded visible range
                    const ids = loadSelectedDentists();
                    const includeUn = loadIncludeUnassigned();
                    const q = loadSearchQuery();
                    const params = new URLSearchParams({
                        dentists: (ids && ids.length ? ids.join(',') : ''),
                        include_unassigned: includeUn ? '1' : '',
                        q: q || '',
                        start: ymdhmss(covStart),
                        end: ymdhmss(covEnd)
                    });
                    const p = fetch(`${BASE}/events?${params.toString()}`)
                        .then(r => {
                            if (!r.ok) throw new Error(`HTTP ${r.status}`);
                            return r.json();
                        })
                        .then(list => {
                            storeEventsToCache(Array.isArray(list) ? list : [], covStart, covEnd, key);
                            const result = eventsFromCache(new Date(fetchInfo.start), new Date(fetchInfo.end), key);
                            success(result);
                            try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                            try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) { }
                        })
                        .catch(err => {
                            if (typeof failure === 'function') failure(err instanceof Error ? err : new Error('Failed to load events'));
                            else success([]);
                        })
                        .finally(() => { try { pendingEventsFetches.delete(dedupKey); } catch (e) { } });
                    pendingEventsFetches.set(dedupKey, p);
                } catch (e) {
                    if (typeof failure === 'function') failure(e instanceof Error ? e : new Error('Unexpected error'));
                    else success([]);
                }
            },
            select: function (info) {
                const popover = document.getElementById('eventPopover');
                popover.style.display = 'block';
                popover.classList.remove('visually-hidden');
                // garantir que fica acima do popover do dia/ano
                try {
                    popover.style.zIndex = '4000';
                } catch (e) { }
                let x = 0,
                    y = 0;
                if (info.jsEvent) {
                    x = info.jsEvent.clientX;
                    y = info.jsEvent.clientY;
                } else {
                    const rect = calendarEl.getBoundingClientRect();
                    x = rect.left + rect.width / 2;
                    y = rect.top + rect.height / 2;
                }
                setTimeout(() => {
                    const popRect = popover.getBoundingClientRect();
                    let left = x;
                    let top = y;
                    if (left + popRect.width > window.innerWidth) left = window.innerWidth - popRect.width - 10;
                    if (left < 10) left = 10;
                    if (top + popRect.height > window.innerHeight) top = window.innerHeight - popRect.height - 10;
                    if (top < 10) top = 10;
                    popover.style.position = 'fixed';
                    popover.style.left = left + 'px';
                    popover.style.top = top + 'px';
                    popover.style.zIndex = '1060';
                }, 10);
                // Preencher campos do popover
                document.getElementById('popoverEventTitle').value = '';
                // Pré-selecionar dentista se exatamente um estiver marcado na sidebar
                try {
                    const sel = document.getElementById('popoverDentist');
                    if (sel) {
                        const ids = loadSelectedDentists();
                        if (ids && ids.length === 1) sel.value = String(ids[0]);
                        else sel.value = '';
                    }
                } catch (e) { }
                // Alterna inputs conforme allDay
                const startInput = document.getElementById('popoverEventStart');
                const endInput = document.getElementById('popoverEventEnd');
                const startDateInput = document.getElementById('popoverEventStartDate');
                const endDateInput = document.getElementById('popoverEventEndDate');
                if (info.allDay) {
                    startInput.classList.add('visually-hidden');
                    endInput.classList.add('visually-hidden');
                    startDateInput.classList.remove('visually-hidden');
                    endDateInput.classList.remove('visually-hidden');
                    // Acessibilidade: ajustar labels para o campo visível (date)
                    try {
                        const startLbl = document.querySelector('#eventPopoverForm label[for="popoverEventStart"], #eventPopoverForm label[for="popoverEventStartDate"]');
                        if (startLbl) startLbl.setAttribute('for', 'popoverEventStartDate');
                        const endLbl = document.querySelector('#eventPopoverForm label[for="popoverEventEnd"], #eventPopoverForm label[for="popoverEventEndDate"]');
                        if (endLbl) endLbl.setAttribute('for', 'popoverEventEndDate');
                    } catch (e) { }
                    startDateInput.value = info.startStr;
                    if (info.endStr) {
                        const endDate = new Date(info.endStr);
                        endDate.setDate(endDate.getDate() - 1);
                        endDateInput.value = endDate.toISOString().slice(0, 10);
                    } else {
                        endDateInput.value = '';
                    }
                    // Se for dia inteiro, não usar datetime picker
                    try {
                        if (startInput._flatpickr) startInput._flatpickr.destroy();
                        if (endInput._flatpickr) endInput._flatpickr.destroy();
                    } catch (e) { }
                    // Aplicar flatpickr nos campos de data (dd/mm/yyyy)
                    const fpDateOpts = {
                        enableTime: false,
                        allowInput: true,
                        locale: (window.flatpickr && window.flatpickr.l10ns && window.flatpickr.l10ns.pt) ? window.flatpickr.l10ns.pt : 'pt',
                        dateFormat: 'Y-m-d', // valor real do input
                        altInput: true,
                        altFormat: 'd/m/Y' // exibição para o usuário
                    };
                    if (window.flatpickr) {
                        flatpickr(startDateInput, fpDateOpts);
                        flatpickr(endDateInput, fpDateOpts);
                    }
                } else {
                    startInput.classList.remove('visually-hidden');
                    endInput.classList.remove('visually-hidden');
                    startDateInput.classList.add('visually-hidden');
                    endDateInput.classList.add('visually-hidden');
                    // Acessibilidade: ajustar labels para o campo visível (datetime)
                    try {
                        const startLbl = document.querySelector('#eventPopoverForm label[for="popoverEventStart"], #eventPopoverForm label[for="popoverEventStartDate"]');
                        if (startLbl) startLbl.setAttribute('for', 'popoverEventStart');
                        const endLbl = document.querySelector('#eventPopoverForm label[for="popoverEventEnd"], #eventPopoverForm label[for="popoverEventEndDate"]');
                        if (endLbl) endLbl.setAttribute('for', 'popoverEventEnd');
                    } catch (e) { }
                    startInput.value = info.startStr.slice(0, 16);
                    // Se a seleção não tiver fim, sugerir fim = início + duração padrão
                    (function () {
                        const saved = parseInt(localStorage.getItem('defaultEventDurationMin') || '60', 10);
                        const dur = isFinite(saved) && saved > 0 ? saved : 60;
                        try {
                            const startISO = info.startStr;
                            const startDate = new Date(startISO);
                            // valor sugerido pelo FullCalendar (geralmente 30min)
                            const selectionEndISO = info.endStr || '';
                            let useDefault = false;
                            if (selectionEndISO) {
                                const selEndDate = new Date(selectionEndISO);
                                const diffMin = Math.max(0, Math.round((selEndDate.getTime() - startDate.getTime()) / 60000));
                                // Se seleção for o slot padrão (30min) e default != 30, usar default
                                // Se usuário arrastou mais que o default, respeitar o arrasto
                                if (diffMin === 30 && dur !== 30) {
                                    useDefault = true;
                                } else if (diffMin === 0) {
                                    useDefault = true;
                                }
                            } else {
                                useDefault = true;
                            }
                            if (useDefault) {
                                const endDate = new Date(startDate);
                                endDate.setMinutes(endDate.getMinutes() + dur);
                                endInput.value = formatLocalYmdHm(endDate);
                            } else {
                                // selectionEndISO pode conter timezone; converter para local string HH:MM
                                const sel = new Date(selectionEndISO);
                                endInput.value = isNaN(sel.getTime()) ? selectionEndISO.slice(0, 16) : formatLocalYmdHm(sel);
                            }
                        } catch (e) {
                            endInput.value = '';
                        }
                    })();
                    // Inicializar/atualizar flatpickr 24h com valores ISO (mantém value no formato ISO; mostra formato BR ao usuário)
                    try {
                        if (startInput._flatpickr) startInput._flatpickr.destroy();
                        if (endInput._flatpickr) endInput._flatpickr.destroy();
                    } catch (e) { }
                    const fpOpts = {
                        enableTime: true,
                        time_24hr: true,
                        allowInput: true,
                        minuteIncrement: 5,
                        locale: (window.flatpickr && window.flatpickr.l10ns && window.flatpickr.l10ns.pt) ? window.flatpickr.l10ns.pt : 'pt',
                        dateFormat: "Y-m-d\\TH:i", // value real enviado
                        altInput: true,
                        altFormat: "d/m/Y H:i" // o que o usuário vê
                    };
                    if (window.flatpickr) {
                        flatpickr(startInput, fpOpts);
                        flatpickr(endInput, fpOpts);
                    }
                }
                document.getElementById('popoverEventDesc').value = '';
                setTimeout(() => {
                    document.getElementById('popoverEventTitle').focus();
                    // Configurar autocompletar
                    setupAutocomplete();
                }, 50);

                function closePopover() {
                    popover.style.display = 'none';
                    document.removeEventListener('mousedown', outsideClickListener);
                }

                function outsideClickListener(e) {
                    if (!popover.contains(e.target)) closePopover();
                }
                setTimeout(() => {
                    document.addEventListener('mousedown', outsideClickListener);
                }, 10);
                document.getElementById('closePopoverBtn').onclick = closePopover;
                const form = document.getElementById('eventPopoverForm');
                form.onsubmit = function (e) {
                    e.preventDefault();
                    const title = document.getElementById('popoverEventTitle').value;
                    let start, end;
                    if (info.allDay) {
                        start = document.getElementById('popoverEventStartDate').value;
                        end = document.getElementById('popoverEventEndDate').value;
                        // UI mostra fim inclusivo; para o backend/FullCalendar precisamos enviar fim exclusivo
                        // Se usuário não preencher, usar start + 1 dia
                    } else {
                        start = document.getElementById('popoverEventStart').value;
                        end = document.getElementById('popoverEventEnd').value;
                        if (!end && start) {
                            const dt = new Date(start);
                            dt.setHours(dt.getHours() + 1);
                            end = dt.toISOString().slice(0, 16);
                        }
                    }
                    const selDent = (function () {
                        const el = document.getElementById('popoverDentist');
                        if (!el) return null;
                        const v = (el.value || '').trim();
                        return v && /^\d+$/.test(v) ? parseInt(v, 10) : null;
                    })();
                    if (title && start) {
                        // Preparar end a ser enviado respeitando regras de all-day (fim exclusivo)
                        let endToSend = end;
                        if (info.allDay) {
                            try {
                                const base = new Date(start + 'T00:00:00');
                                let endDate = end ? new Date(end + 'T00:00:00') : new Date(base);
                                endDate.setDate(endDate.getDate() + 1); // tornar exclusivo
                                endToSend = endDate.toISOString().slice(0, 10);
                            } catch (e) {
                                // fallback: se algo falhar, garantir pelo menos +1 dia
                                try {
                                    const d = new Date(start + 'T00:00:00');
                                    d.setDate(d.getDate() + 1);
                                    endToSend = d.toISOString().slice(0, 10);
                                } catch (e2) {
                                    endToSend = end || start;
                                }
                            }
                        }
                        fetch(BASE + '/add_event', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                title: title,
                                start: start,
                                end: (function () {
                                    if (info.allDay) return endToSend;
                                    if (end) return end;
                                    // aplicar duração padrão ao salvar se vazio (caso com hora)
                                    try {
                                        const saved = parseInt(localStorage.getItem('defaultEventDurationMin') || '60', 10);
                                        const dur = isFinite(saved) && saved > 0 ? saved : 60;
                                        const dt = new Date(start);
                                        dt.setMinutes(dt.getMinutes() + dur);
                                        return formatLocalYmdHm(dt);
                                    } catch (e) {
                                        return end;
                                    }
                                })(),
                                notes: document.getElementById('popoverEventDesc').value || '',
                                profissional_id: selDent
                            })
                        })
                            .then(response => response.json())
                            .then(data => {
                                if (data.status === 'success' && data.event) {
                                    try {
                                        // Adiciona imediatamente no calendário e no cache compartilhado
                                        calendar.addEvent(data.event);
                                        addEventToCache(data.event);
                                        try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                                        try { showToast('Evento criado.', 'success', 1600); } catch (e) { }
                                    } catch (e) {
                                        // Fallback: força recarregar eventos
                                        try { calendar.refetchEvents(); } catch (_) { }
                                    }
                                    closePopover();
                                } else {
                                    alert('Erro ao adicionar evento!');
                                }
                            });
                    }
                };
                calendar.unselect();
            },
            eventClick: function (info) {
                document.getElementById('eventContextMenu').style.display = 'none';
                const popover = document.getElementById('eventDetailPopover');
                // mover para o body para evitar contextos de empilhamento e garantir topo
                try {
                    if (popover && popover.parentElement !== document.body) {
                        document.body.appendChild(popover);
                    }
                } catch (e) { }
                // Formatação correta do horário (pt-BR)
                const fmtDate = new Intl.DateTimeFormat('pt-BR', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric'
                });
                const fmtTime = new Intl.DateTimeFormat('pt-BR', {
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: false
                });

                function buildTimeText(ev) {
                    const start = ev.start;
                    const end = ev.end;
                    if (ev.allDay) {
                        if (!end) return `${fmtDate.format(start)} (dia inteiro)`;
                        const last = new Date(end.getTime() - 24 * 60 * 60 * 1000);
                        const same = start.getFullYear() === last.getFullYear() &&
                            start.getMonth() === last.getMonth() &&
                            start.getDate() === last.getDate();
                        return same ?
                            `${fmtDate.format(start)} (dia inteiro)` :
                            `${fmtDate.format(start)} – ${fmtDate.format(last)} (dia inteiro)`;
                    } else {
                        if (end) {
                            const sameDay = start.toDateString() === end.toDateString();
                            return sameDay ?
                                `${fmtDate.format(start)} ${fmtTime.format(start)} – ${fmtTime.format(end)}` :
                                `${fmtDate.format(start)} ${fmtTime.format(start)} – ${fmtDate.format(end)} ${fmtTime.format(end)}`;
                        } else {
                            return `${fmtDate.format(start)} ${fmtTime.format(start)}`;
                        }
                    }
                }
                // Preencher apenas título e horário
                document.getElementById('detailEventTitle').textContent = info.event.title;
                document.getElementById('detailEventTime').textContent = buildTimeText(info.event);
                // Preencher notas (descrição)
                const notesArea = document.getElementById('detailEventNotes');
                const saveNotesBtn = document.getElementById('saveDetailNotesBtn');
                if (notesArea) {
                    notesArea.value = info.event.extendedProps && info.event.extendedProps.notes ? info.event.extendedProps.notes : '';
                }
                if (saveNotesBtn) {
                    saveNotesBtn.onclick = function () {
                        const newNotes = notesArea ? notesArea.value : '';
                        fetch(BASE + '/update_event_notes', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                id: info.event.id,
                                notes: newNotes
                            })
                        })
                            .then(r => r.json())
                            .then(data => {
                                if (data.status === 'success') {
                                    try { info.event.setExtendedProp('notes', newNotes); } catch (e) { }
                                    updateEventInCacheById(info.event.id, { notes: newNotes });
                                    try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                                } else {
                                    alert('Erro ao salvar descrição.');
                                }
                            })
                            .catch(() => alert('Erro ao salvar descrição.'));
                    };
                }
                // Dentista: preencher opções e valor atual
                try {
                    const sel = document.getElementById('detailEventDentist');
                    const btn = document.getElementById('saveDetailDentistBtn');
                    if (sel) {
                        // Limpar e repopular mantendo 'Sem dentista'
                        const keep = sel.querySelector('option[value=""]');
                        sel.innerHTML = '';
                        if (keep) sel.appendChild(keep);
                        (dentistsCache.list || []).forEach(d => {
                            const opt = document.createElement('option');
                            opt.value = String(d.id);
                            opt.textContent = d.nome;
                            sel.appendChild(opt);
                        });
                        const pid = info.event.extendedProps && info.event.extendedProps.profissional_id;
                        sel.value = (pid != null) ? String(pid) : '';
                    }
                    if (btn) {
                        btn.onclick = function () {
                            const v = (sel && sel.value || '').trim();
                            const pid = v && /^\d+$/.test(v) ? parseInt(v, 10) : null;
                            fetch(BASE + '/update_event', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    id: info.event.id,
                                    profissional_id: pid
                                })
                            })
                                .then(r => r.json())
                                .then(j => {
                                    if (j && j.status === 'success') {
                                        try { info.event.setExtendedProp('profissional_id', pid); } catch (e) { }
                                        updateEventInCacheById(info.event.id, { profissional_id: pid });
                                        // Re-render events to re-run eventDidMount and apply new dentist colors
                                        try { calendar.rerenderEvents(); } catch (e) { }
                                        // Also directly repaint current DOM nodes for immediate feedback
                                        try { repaintDentistBarsForEvent(info.event.id, pid); } catch (e) { }
                                        try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                                    } else {
                                        alert('Erro ao salvar dentista.');
                                    }
                                })
                                .catch(() => alert('Erro ao salvar dentista.'));
                        };
                    }
                } catch (e) { }
                // Buscar telefone do paciente e habilitar clique para copiar
                const phoneSection = document.getElementById('detailEventPhoneSection');
                const phoneDiv = document.getElementById('detailEventPhone');
                const waLink = document.getElementById('detailEventWhatsApp');

                function normalizePhoneForWhatsApp(raw) {
                    if (!raw) return null;
                    const digits = String(raw).replace(/\D+/g, '');
                    if (!digits) return null;
                    // Se já tem DDI e parece E.164 brasileiro (55 + 11 dígitos para celular ou 10 para fixo)
                    if (digits.startsWith('55') && (digits.length === 12 || digits.length === 13)) {
                        return digits;
                    }
                    // Se parece internacional (mais que 11 dígitos e não começa com 55), manter
                    if (!digits.startsWith('55') && digits.length > 11) {
                        return digits;
                    }
                    const DEFAULT_DDI = '55';
                    const DEFAULT_DDD = '33'; // conforme solicitado
                    if (digits.length === 11) {
                        // DDD + celular (9 dígitos)
                        return DEFAULT_DDI + digits;
                    }
                    if (digits.length === 10) {
                        // DDD + fixo
                        return DEFAULT_DDI + digits;
                    }
                    if (digits.length === 9 || digits.length === 8) {
                        // sem DDD, usar padrão
                        return DEFAULT_DDI + DEFAULT_DDD + digits;
                    }
                    // fallback: se muito curto, retornar null
                    return null;
                }

                function applyWhatsAppLink(num) {
                    if (!waLink) return;
                    const normalized = normalizePhoneForWhatsApp(num);
                    if (normalized) {
                        waLink.href = `https://wa.me/${normalized}`;
                        waLink.classList.remove('visually-hidden');
                    } else {
                        waLink.classList.add('visually-hidden');
                    }
                }
                if (phoneSection && phoneDiv) {
                    phoneSection.classList.add('hidden');
                    phoneDiv.textContent = '';
                    fetch(`${BASE}/buscar_telefone?nome=${encodeURIComponent(info.event.title)}`)
                        .then(response => response.json())
                        .then(data => {
                            const tel = (data && data.telefone) ? String(data.telefone).trim() : '';
                            const fromNotes = (!tel && info.event.extendedProps) ?
                                extractPhoneFromText(info.event.extendedProps.notes) :
                                null;
                            const finalTel = tel || (fromNotes || '');
                            if (finalTel) {
                                phoneDiv.textContent = finalTel;
                                phoneDiv.classList.remove('copied');
                                phoneSection.classList.remove('hidden');
                                applyWhatsAppLink(finalTel);
                                phoneDiv.onclick = async () => {
                                    try {
                                        await navigator.clipboard.writeText(finalTel);
                                        phoneDiv.classList.add('copied');
                                        setTimeout(() => phoneDiv.classList.remove('copied'), 1200);
                                    } catch (e) {
                                        const ta = document.createElement('textarea');
                                        ta.value = finalTel;
                                        document.body.appendChild(ta);
                                        ta.select();
                                        document.execCommand('copy');
                                        document.body.removeChild(ta);
                                        phoneDiv.classList.add('copied');
                                        setTimeout(() => phoneDiv.classList.remove('copied'), 1200);
                                    }
                                };
                            }
                        })
                        .catch(() => {
                            // Fallback silencioso: tentar extrair do texto das notas
                            const notes = (info.event.extendedProps && info.event.extendedProps.notes) ? String(info.event.extendedProps.notes) : '';
                            const extracted = extractPhoneFromText(notes);
                            if (extracted) {
                                phoneDiv.textContent = extracted;
                                phoneDiv.classList.remove('copied');
                                phoneSection.classList.remove('hidden');
                                applyWhatsAppLink(extracted);
                                phoneDiv.onclick = async () => {
                                    try {
                                        await navigator.clipboard.writeText(extracted);
                                        phoneDiv.classList.add('copied');
                                        setTimeout(() => phoneDiv.classList.remove('copied'), 1200);
                                    } catch (e) {
                                        const ta = document.createElement('textarea');
                                        ta.value = extracted;
                                        document.body.appendChild(ta);
                                        ta.select();
                                        document.execCommand('copy');
                                        document.body.removeChild(ta);
                                        phoneDiv.classList.add('copied');
                                        setTimeout(() => phoneDiv.classList.remove('copied'), 1200);
                                    }
                                };
                            }
                        });
                }

                // Exibir popover próximo ao clique
                let x = 0,
                    y = 0;
                if (info.jsEvent) {
                    x = info.jsEvent.clientX;
                    y = info.jsEvent.clientY;
                } else {
                    const rect = calendarEl.getBoundingClientRect();
                    x = rect.left + rect.width / 2;
                    y = rect.top + rect.height / 2;
                }
                popover.style.display = 'block';
                popover.classList.remove('visually-hidden');
                try {
                    popover.style.zIndex = '10000';
                } catch (e) { }
                setTimeout(() => {
                    const popRect = popover.getBoundingClientRect();
                    const calRect = calendarEl.getBoundingClientRect();
                    let left = x;
                    let top = y + window.scrollY;
                    if (left + popRect.width > calRect.right) left = calRect.right - popRect.width;
                    if (left < calRect.left) left = calRect.left;
                    if (top + popRect.height > calRect.bottom + window.scrollY) top = calRect.bottom + window.scrollY - popRect.height;
                    if (top < calRect.top + window.scrollY) top = calRect.top + window.scrollY;
                    popover.style.left = left + 'px';
                    popover.style.top = top + 'px';
                }, 10);
                // Fechar ao clicar fora ou no botão
                function closePopover() {
                    popover.style.display = 'none';
                    popover.classList.add('visually-hidden');
                    document.removeEventListener('mousedown', outsideClickListener);
                }

                function outsideClickListener(e) {
                    if (!popover.contains(e.target)) closePopover();
                }
                setTimeout(() => {
                    document.addEventListener('mousedown', outsideClickListener);
                }, 10);
                document.getElementById('closeDetailPopoverBtn').onclick = closePopover;
            },
            eventDidMount: function (info) {
                // marcar elemento com id para filtros de busca
                try {
                    if (info && info.el && info.event && info.event.id != null) {
                        info.el.setAttribute('data-eid', String(info.event.id));
                    }
                } catch (e) { }
                info.el.addEventListener('contextmenu', function (e) {
                    e.preventDefault();
                    const menu = document.getElementById('eventContextMenu');
                    let x = e.clientX,
                        y = e.clientY;
                    menu.style.display = 'block';
                    setTimeout(() => {
                        const menuRect = menu.getBoundingClientRect();
                        const calRect = calendarEl.getBoundingClientRect();
                        let left = x;
                        let top = y + window.scrollY;
                        if (left + menuRect.width > calRect.right) left = calRect.right - menuRect.width;
                        if (left < calRect.left) left = calRect.left;
                        if (top + menuRect.height > calRect.bottom + window.scrollY) top = calRect.bottom + window.scrollY - menuRect.height;
                        if (top < calRect.top + window.scrollY) top = calRect.top + window.scrollY;
                        menu.style.left = left + 'px';
                        menu.style.top = top + 'px';
                    }, 10);

                    function closeMenu() {
                        menu.style.display = 'none';
                        document.removeEventListener('mousedown', outsideClickListener);
                    }

                    function outsideClickListener(ev) {
                        if (!menu.contains(ev.target)) closeMenu();
                    }
                    setTimeout(() => {
                        document.addEventListener('mousedown', outsideClickListener);
                    }, 10);
                    // Duplicação rápida (+1 semana, +2 semanas, +1 mês)
                    const ORANGE = '#f59e42';

                    function pad(n) {
                        return String(n).padStart(2, '0');
                    }

                    function fmtDate(d) {
                        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
                    }

                    function fmtDateTime(d) {
                        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
                    }

                    function addDays(d, n) {
                        const nd = new Date(d);
                        nd.setDate(nd.getDate() + n);
                        return nd;
                    }

                    function addMonths(d, n) {
                        const nd = new Date(d);
                        nd.setMonth(nd.getMonth() + n);
                        return nd;
                    }

                    function duplicateWith(offset) {
                        try {
                            const ev = info.event;
                            const isAllDay = !!ev.allDay;
                            const start = new Date(ev.start);
                            const end = ev.end ? new Date(ev.end) : (isAllDay ? addDays(start, 1) : addDays(start, 1));
                            const pid = ev.extendedProps && ev.extendedProps.profissional_id ? Number(ev.extendedProps.profissional_id) : null;
                            let newStart, newEnd;
                            if (offset.type === 'd') {
                                newStart = addDays(start, offset.value);
                                newEnd = addDays(end, offset.value);
                            } else if (offset.type === 'm') {
                                newStart = addMonths(start, offset.value);
                                newEnd = addMonths(end, offset.value);
                            }
                            const body = {
                                title: ev.title || '',
                                start: isAllDay ? fmtDate(newStart) : fmtDateTime(newStart),
                                end: isAllDay ? fmtDate(newEnd) : fmtDateTime(newEnd),
                                notes: '',
                                color: ORANGE,
                                profissional_id: pid
                            };
                            fetch(BASE + '/add_event', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify(body)
                            })
                                .then(r => r.json()).then(j => {
                                    if (j && j.status === 'success' && j.event) {
                                        try {
                                            calendar.addEvent(j.event);
                                            addEventToCache(j.event);
                                            try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                                            closeMenu();
                                        } catch (e) {
                                            calendar.refetchEvents();
                                        }
                                    } else {
                                        alert('Erro ao duplicar evento.');
                                    }
                                }).catch(() => alert('Erro ao duplicar evento.'));
                        } catch (e) {
                            /* noop */
                        }
                    }
                    const dup1w = document.getElementById('dup1wBtn');
                    const dup2w = document.getElementById('dup2wBtn');
                    const dup3w = document.getElementById('dup3wBtn');
                    const dup4w = document.getElementById('dup4wBtn');
                    const dup1m = document.getElementById('dup1mBtn');
                    if (dup1w) dup1w.onclick = () => duplicateWith({
                        type: 'd',
                        value: 7
                    });
                    if (dup2w) dup2w.onclick = () => duplicateWith({
                        type: 'd',
                        value: 14
                    });
                    if (dup3w) dup3w.onclick = () => duplicateWith({
                        type: 'd',
                        value: 21
                    });
                    if (dup4w) dup4w.onclick = () => duplicateWith({
                        type: 'd',
                        value: 28
                    });
                    if (dup1m) dup1m.onclick = () => duplicateWith({
                        type: 'm',
                        value: 1
                    });

                    document.getElementById('deleteEventBtn').onclick = function () {
                        fetch(BASE + '/delete_event', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                id: info.event.id
                            })
                        })
                            .then(response => response.json())
                            .then(data => {
                                if (data.status === 'success') {
                                    try { info.event.remove(); } catch (e) { }
                                    removeEventFromCacheById(info.event.id);
                                    try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                                    closeMenu();
                                } else {
                                    alert('Erro ao deletar evento!');
                                }
                            });
                    };
                    document.querySelectorAll('#colorOptions .color-circle').forEach(function (circle) {
                        circle.onclick = function () {
                            const color = this.getAttribute('data-color');
                            fetch(BASE + '/update_event_color', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    id: info.event.id,
                                    color: color
                                })
                            })
                                .then(response => response.json())
                                .then(data => {
                                    if (data.status === 'success') {
                                        try {
                                            info.event.setProp('backgroundColor', color);
                                            info.event.setProp('borderColor', color);
                                        } catch (e) { }
                                        updateEventInCacheById(info.event.id, { color });
                                        try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                                        closeMenu();
                                    } else {
                                        alert('Erro ao atualizar cor!');
                                    }
                                });
                        };
                    });
                });

                // Aplicar borda direita espessa + esquerda fina por dentista
                try {
                    const pid = info.event.extendedProps && info.event.extendedProps.profissional_id;
                    if (pid != null && dentistsCache && dentistsCache.map && dentistsCache.map[pid]) {
                        const d = dentistsCache.map[pid];
                        const col = colorForDentist(d);
                        info.el.classList.add('dentist-rightbar');
                        info.el.style.borderRight = `6px solid ${col}`;
                        info.el.classList.add('dentist-leftbar');
                        info.el.style.borderLeft = `2px solid ${col}`;
                        // Reforço visual em views baseadas em tabela (list) e em elementos sem borda visível
                        try {
                            info.el.style.boxShadow = `inset -6px 0 0 0 ${col}`;
                        } catch (e) { }
                    }
                } catch (e) { }

                // Enriquecer eventos no popover "+ mais" (multiMonth/dayGrid): título, horário e descrição
                // Executa após render para garantir que o elemento esteja dentro do popover
                setTimeout(() => {
                    const pop = info.el.closest('.fc-more-popover');
                    if (!pop) return; // apenas dentro do popover
                    try {
                        const isAllDay = info.event.allDay;
                        let timeStr = '';
                        if (!isAllDay && info.event.start) {
                            try {
                                timeStr = new Intl.DateTimeFormat('pt-BR', {
                                    hour: '2-digit',
                                    minute: '2-digit',
                                    hour12: false
                                }).format(info.event.start);
                            } catch (e) {
                                const d = info.event.start;
                                const hh = String(d.getHours()).padStart(2, '0');
                                const mm = String(d.getMinutes()).padStart(2, '0');
                                timeStr = `${hh}:${mm}`;
                            }
                        }
                        const title = info.event.title || '';
                        const notes = (info.event.extendedProps && info.event.extendedProps.notes) ? info.event.extendedProps.notes : '';
                        const sep = timeStr ? '<span class="fc-event-time-start"> ' + timeStr + '</span>' : '';
                        const notesLine = notes ? `<div class="fc-event-notes">${notes}</div>` : '';
                        const html = `<div class="fc-event-main-custom fc-popover-rich">
                                    <div class="line1"><span class="fc-event-title">${title}</span>${sep}</div>
                                    ${notesLine}
                                </div>`;
                        const main = info.el.querySelector('.fc-event-main') || info.el.querySelector('.fc-event-main-frame') || info.el;
                        if (main) main.innerHTML = html;
                    } catch (e) {
                        /* noop */
                    }
                }, 0);
                // aplicar filtro de busca para novos elementos
                try {
                    if (typeof applyClientSearchFilter === 'function') applyClientSearchFilter();
                } catch (e) { }
            },
            eventDrop: function (info) {
                let start = info.event.startStr;
                let end = info.event.endStr;
                if (info.event.allDay) {
                    if (start && start.length > 10) start = start.slice(0, 10);
                    if (end && end.length > 10) end = end.slice(0, 10);
                }
                fetch(BASE + '/update_event', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        id: info.event.id,
                        start: start,
                        end: end
                    })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status !== 'success') {
                            alert('Erro ao atualizar evento!');
                            info.revert();
                        }
                    })
                    .catch(() => {
                        alert('Erro ao atualizar evento!');
                        info.revert();
                    });
            },
            eventResize: function (info) {
                let start = info.event.startStr;
                let end = info.event.endStr;
                if (info.event.allDay) {
                    if (start && start.length > 10) start = start.slice(0, 10);
                    if (end && end.length > 10) end = end.slice(0, 10);
                }
                fetch(BASE + '/update_event', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        id: info.event.id,
                        start: start,
                        end: end
                    })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status !== 'success') {
                            alert('Erro ao atualizar evento!');
                            info.revert();
                        }
                    })
                    .catch(() => {
                        alert('Erro ao atualizar evento!');
                        info.revert();
                    });
            }
        });
        calendar.render();
        // After main events are loaded/rendered, refresh the mini to consume the cache and rebuild indicators
        try {
            calendar.on('eventsSet', () => {
                try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) { }
            });
        } catch (e) { }

        // ===== Mini calendário (sidebar) =====
        (function initMiniCalendar() {
            try {
                const miniEl = document.getElementById('miniCalendar');
                if (!miniEl || !window.FullCalendar) return;
                const miniPlugins = [];
                if (FullCalendar.dayGridPlugin) miniPlugins.push(FullCalendar.dayGridPlugin);
                if (FullCalendar.interactionPlugin) miniPlugins.push(FullCalendar.interactionPlugin);
                const selectedYmd = () => ymdFromDate(calendar.getDate());
                // guard to avoid loops when syncing main -> mini
                let __syncingMini = false;
                // track the visible grid range to detect month navigation in mini
                let __lastMiniGridKey = '';
                // Debounced refetch for main when mini month changes
                const refetchMainDebounced = debounce(() => { try { calendar.refetchEvents(); } catch (e) { } }, 120);
                const mini = new FullCalendar.Calendar(miniEl, {
                    plugins: miniPlugins,
                    locale: 'pt-br',
                    initialView: 'dayGridMonth',
                    initialDate: calendar.getDate(),
                    height: 'auto',
                    fixedWeekCount: false,
                    showNonCurrentDates: true,
                    headerToolbar: {
                        left: 'prev,next',
                        center: 'title',
                        right: ''
                    },
                    selectable: false,
                    editable: false,
                    eventClick: (info) => {
                        try {
                            const d = info.event.start || info.jsEvent?.date || info.el?.fcSeg?.start;
                            if (d) calendar.gotoDate(d);
                        } catch (e) { }
                    },
                    // Não renderizar conteúdo dos eventos no mini; usaremos indicadores customizados
                    eventContent: function () {
                        return {
                            domNodes: []
                        };
                    },
                    // Read events from the shared cache; no network here
                    events: function (fetchInfo, success) {
                        try {
                            const key = buildCacheKey();
                            const res = eventsFromCache(new Date(fetchInfo.start), new Date(fetchInfo.end), key);
                            success(res);
                        } catch (e) { success([]); }
                    },
                    dateClick: (info) => {
                        try {
                            calendar.gotoDate(info.date);
                        } catch (e) { }
                    },
                    dayCellDidMount: (arg) => {
                        try {
                            const ymd = ymdFromDate(arg.date);
                            if (ymd === selectedYmd()) arg.el.classList.add('mini-selected');
                            else arg.el.classList.remove('mini-selected');
                            // Holiday highlight using year cache (same logic as main, but per-mini view)
                            const key = ymdFromDate(arg.date);
                            const y = arg.date.getFullYear();
                            const yc = holidaysYearCache[y];
                            const isHoliday = !!(yc && yc.dates && yc.dates.has(key));
                            if (isHoliday) {
                                arg.el.classList.add('fc-day-holiday');
                                const meta = yc.meta && yc.meta[key];
                                if (meta && arg.el && arg.el.setAttribute) {
                                    arg.el.setAttribute('title', meta.name);
                                }
                                // add bg overlay similar to main
                                const bg = document.createElement('div');
                                bg.className = 'fc-holiday-bg';
                                bg.style.position = 'absolute';
                                bg.style.inset = '0';
                                bg.style.borderRadius = '4px';
                                bg.style.pointerEvents = 'none';
                                // insert as first child to sit below events
                                const frame = arg.el.querySelector('.fc-daygrid-day-frame');
                                if (frame && !frame.querySelector('.fc-holiday-bg')) {
                                    frame.insertBefore(bg, frame.firstChild);
                                }
                            }
                            // preparar container de indicadores
                            const frame = arg.el.querySelector('.fc-daygrid-day-frame');
                            if (frame && !frame.querySelector('.mini-indicators')) {
                                const ind = document.createElement('div');
                                ind.className = 'mini-indicators';
                                frame.appendChild(ind);
                            }
                        } catch (e) { }
                    }
                });
                mini.render();
                // util: refaz indicadores com base nos eventos atuais do mini
                const rebuildMiniIndicators = rafThrottle(function () {
                    try {
                        // Using mini.view only for side effects below; no local alias needed
                        // mapa ymd -> lista de cores (ordem de chegada, sem duplicar adjacentes)
                        const colorMap = {};
                        // conjunto de dias com QUALQUER evento (all-day ou com hora)
                        const anyEventDays = {};
                        // 1) processar all-day para barras e presença
                        mini.getEvents().forEach(ev => {
                            const s0 = ev.start ? new Date(ev.start) : null;
                            if (!s0) return;
                            if (ev.allDay) {
                                const s = new Date(s0);
                                const e = ev.end ? new Date(ev.end) : new Date(s0);
                                const d = new Date(s);
                                const eInc = new Date(e);
                                if (ev.end) eInc.setDate(eInc.getDate() - 1);
                                while (d <= eInc) {
                                    const ymd = ymdFromDate(d);
                                    anyEventDays[ymd] = true;
                                    // barras coloridas apenas para all-day
                                    const pid = ev.extendedProps && (ev.extendedProps.profissional_id ?? ev.extendedProps.profissionalId);
                                    let col = null;
                                    try {
                                        if (pid != null && dentistsCache && dentistsCache.map && dentistsCache.map[pid] && dentistsCache.map[pid].color) {
                                            col = dentistsCache.map[pid].color;
                                        }
                                    } catch (e) { }
                                    if (!col) col = ev.backgroundColor || ev.color || 'var(--bs-primary)';
                                    if (!colorMap[ymd]) colorMap[ymd] = [];
                                    const arr = colorMap[ymd];
                                    if (arr[arr.length - 1] !== col) arr.push(col);
                                    d.setDate(d.getDate() + 1);
                                }
                            }
                        });
                        // 2) processar eventos com hora para marcar presença no dia
                        mini.getEvents().forEach(ev => {
                            if (ev.allDay) return; // já coberto
                            const s = ev.start ? new Date(ev.start) : null;
                            if (!s) return;
                            const e = ev.end ? new Date(ev.end) : new Date(s);
                            // considerar sobreposição por dia; excluir próximo dia se terminar exatamente 00:00
                            const eMinus = new Date(e.getTime() - 1);
                            let cur = new Date(s.getFullYear(), s.getMonth(), s.getDate());
                            const last = new Date(eMinus.getFullYear(), eMinus.getMonth(), eMinus.getDate());
                            while (cur <= last) {
                                anyEventDays[ymdFromDate(cur)] = true;
                                cur.setDate(cur.getDate() + 1);
                            }
                        });
                        // aplicar barras
                        miniEl.querySelectorAll('.fc-daygrid-day').forEach(cell => {
                            const dataDate = cell.getAttribute('data-date');
                            const frame = cell.querySelector('.fc-daygrid-day-frame');
                            const ind = frame && frame.querySelector('.mini-indicators');
                            if (!ind) return;
                            ind.innerHTML = '';
                            const cols = (colorMap[dataDate] || []).slice(0, 3);
                            for (let i = 0; i < cols.length; i++) {
                                const bar = document.createElement('div');
                                bar.className = 'bar';
                                bar.style.background = cols[i];
                                ind.appendChild(bar);
                            }
                            const total = (colorMap[dataDate] || []).length;
                            if (total > 3) {
                                const bar = document.createElement('div');
                                bar.className = 'bar';
                                bar.style.background = 'var(--bs-secondary)';
                                ind.appendChild(bar);
                            }
                            // overlay amarelado para dias sem NENHUM evento
                            // limpar overlay anterior
                            const prevEmpty = frame && frame.querySelector('.fc-empty-bg');
                            if (prevEmpty && prevEmpty.remove) prevEmpty.remove();
                            const hasAny = !!anyEventDays[dataDate];
                            // flags visuais do FullCalendar
                            const isToday = cell.classList.contains('fc-day-today');
                            // evitar conflito com overlay de feriado e evitar duplicar sobre o próprio "hoje"
                            const hasHolidayBg = frame && frame.querySelector('.fc-holiday-bg');
                            if (!hasAny && !hasHolidayBg && !isToday) {
                                const ov = document.createElement('div');
                                ov.className = 'fc-empty-bg';
                                ov.style.position = 'absolute';
                                ov.style.inset = '0';
                                // intensidade e cor controladas por CSS (tema claro/escuro)
                                ov.style.borderRadius = '4px';
                                ov.style.pointerEvents = 'none';
                                // inserir como primeiro filho
                                if (frame) frame.insertBefore(ov, frame.firstChild);
                            }
                        });
                    } catch (e) { }
                });
                // expor para outros fluxos (ex.: após carregar dentistas)
                try {
                    window.__miniCalendar = mini;
                    window.__rebuildMiniIndicators = rebuildMiniIndicators;
                } catch (e) { }
                // manter mini em sincronia com a data do calendário principal (sem refetch redundante)
                calendar.on('datesSet', () => {
                    try {
                        // Clear month fetch override when main changes
                        try { window.__fetchMonthOverride = null; } catch (e) { }
                        __syncingMini = true;
                        mini.gotoDate(calendar.getDate());
                        __syncingMini = false;
                        // re-render apenas para atualizar destaque da seleção; o mini fará fetch automático
                        // quando o mês mudar
                        mini.render();
                        rebuildMiniIndicators();
                    } catch (e) { }
                });
                // garantir feriados carregados também quando navegar pelo mini
                mini.on('datesSet', () => {
                    try {
                        const v = mini.view;
                        if (!(v && v.currentStart && v.currentEnd)) return;
                        // If user navigated months on the mini, refetch main to fill cache for the new grid
                        const gridKey = `${new Date(v.currentStart).toISOString().slice(0, 10)}|${new Date(v.currentEnd).toISOString().slice(0, 10)}`;
                        if (!__syncingMini && gridKey !== __lastMiniGridKey) {
                            __lastMiniGridKey = gridKey;
                            // Set month fetch override so main loads the mini's month
                            try { window.__fetchMonthOverride = { start: new Date(v.currentStart), end: new Date(v.currentEnd) }; } catch (e) { }
                            refetchMainDebounced();
                        } else {
                            __lastMiniGridKey = gridKey;
                        }
                        const start = new Date(v.currentStart);
                        const endInc = new Date(v.currentEnd);
                        endInc.setDate(endInc.getDate() - 1);
                        ensureRangeCached(start, endInc).then(() => {
                            // reaplicar tooltips/overlays via re-render
                            mini.render();
                            rebuildMiniIndicators();
                        });
                    } catch (e) { }
                });
                // quando a lista de eventos mudar (filtros/busca), refazer indicadores
                mini.on('eventsSet', () => {
                    try {
                        rebuildMiniIndicators();
                    } catch (e) { }
                });
            } catch (e) {
                /* noop */
            }
        })();

        // Carregar dentistas e montar sidebar (dedup + TTL cache) antes de qualquer refetch
        fetchDentistsOnce()
            .then(list => {
                // normalizar ids para number
                const norm = Array.isArray(list)
                    ? list.map(d => ({ id: Number(d.id), nome: d.nome, color: d.color || null }))
                    : [];
                dentistsCache.list = norm; // ensure structures are set (no-op if already)
                dentistsCache.map = Object.fromEntries(norm.map(d => [d.id, d]));
                // Preencher o select do popover
                try {
                    const sel = document.getElementById('popoverDentist');
                    if (sel) {
                        // mantém 'Sem dentista'
                        norm.forEach(d => {
                            const opt = document.createElement('option');
                            opt.value = String(d.id);
                            opt.textContent = d.nome;
                            sel.appendChild(opt);
                        });
                        const checkedIds = loadSelectedDentists();
                        if (checkedIds && checkedIds.length === 1) sel.value = String(checkedIds[0]);
                    }
                } catch (e) { }
                // Se não houver seleção salva, selecionar todos por padrão (e só então refazer fetch)
                const saved = loadSelectedDentists();
                let selectionChanged = false;
                if (!saved || saved.length === 0) {
                    try {
                        const newSel = norm.map(d => d.id);
                        saveSelectedDentists(newSel);
                        selectionChanged = true;
                    } catch (e) { }
                }
                renderDentistsSidebar(norm);
                // Refazer fetch apenas se a seleção inicial foi alterada (ex.: primeira execução)
                if (selectionChanged) {
                    try { calendar.refetchEvents(); } catch (e) { }
                }
                updateEmptyFilterNoticeDeb();
                // sincronizar mini calendário após carregar dentistas
                if (selectionChanged) {
                    try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                }
                try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) { }
            })
            .catch(() => {
                const cont = document.getElementById('dentistsContainer');
                if (cont) cont.innerHTML = '<div class="text-danger">Falha ao carregar dentistas.</div>';
            });

        // ===== Configurações / Temas =====
        const settingsMenu = document.getElementById('settingsMenu');
        const searchMenu = document.getElementById('searchMenu');

        function toggleSettingsMenu(anchorEl) {
            if (!settingsMenu) return;
            const isVisible = settingsMenu.style.display === 'block';
            if (isVisible) {
                settingsMenu.style.display = 'none';
                settingsMenu.classList.add('visually-hidden');
                document.removeEventListener('mousedown', outsideClickListenerSettings);
                return;
            }
            // Posicionar próximo ao botão
            const rect = anchorEl.getBoundingClientRect();
            const top = rect.bottom + window.scrollY + 6;
            const left = rect.left + window.scrollX;
            settingsMenu.style.display = 'block';
            settingsMenu.classList.remove('visually-hidden');
            settingsMenu.style.position = 'absolute';
            settingsMenu.style.top = top + 'px';
            settingsMenu.style.left = left + 'px';
            // Inicializar UI de feriados somente ao abrir o menu (lazy)
            try {
                if (typeof initHolidaysUIOnce === 'function') initHolidaysUIOnce();
            } catch (e) { }
            setActiveThemeButton(localStorage.getItem('calendarTheme') || 'default');
            (function () {
                let saved = parseInt(localStorage.getItem('defaultEventDurationMin') || '60', 10);
                if (!isFinite(saved) || saved <= 0 || saved === 15) {
                    saved = 60;
                    try {
                        localStorage.setItem('defaultEventDurationMin', String(saved));
                    } catch (e) { }
                }
                setActiveDurationButton(saved);
            })();
            // weekends active state
            (function () {
                const wk = getWeekendsSetting();
                document.querySelectorAll('#settingsMenu [data-weekends]').forEach(btn => {
                    btn.classList.toggle('active', String(wk) === btn.getAttribute('data-weekends'));
                });
            })();
            // Atualizar status do token somente agora
            try {
                if (window.__fetchAndUpdateTokenBadge) window.__fetchAndUpdateTokenBadge();
            } catch (e) { }
            setTimeout(() => document.addEventListener('mousedown', outsideClickListenerSettings), 10);
        }

        function outsideClickListenerSettings(e) {
            if (!settingsMenu.contains(e.target)) {
                settingsMenu.style.display = 'none';
                settingsMenu.classList.add('visually-hidden');
                document.removeEventListener('mousedown', outsideClickListenerSettings);
            }
        }

        // ===== Busca =====
        const searchStateKey = 'calendarSearchQuery';

        function saveSearchQuery(q) {
            try {
                localStorage.setItem(searchStateKey, q || '');
            } catch (e) { }
        }

        function loadSearchQuery() {
            try {
                return localStorage.getItem(searchStateKey) || '';
            } catch (e) {
                return '';
            }
        }

        function toggleSearchMenu(anchorEl) {
            if (!searchMenu) return;
            const isVisible = searchMenu.style.display === 'block';
            if (isVisible) {
                searchMenu.style.display = 'none';
                searchMenu.classList.add('visually-hidden');
                document.removeEventListener('mousedown', outsideClickListenerSearch);
                return;
            }
            const rect = anchorEl.getBoundingClientRect();
            const top = rect.bottom + window.scrollY + 6;
            const left = rect.left + window.scrollX;
            searchMenu.style.display = 'block';
            searchMenu.classList.remove('visually-hidden');
            searchMenu.style.position = 'absolute';
            searchMenu.style.top = top + 'px';
            searchMenu.style.left = left + 'px';
            // Prefill
            try {
                const inp = document.getElementById('searchQueryInput');
                if (inp) {
                    inp.value = loadSearchQuery();
                    inp.focus();
                    inp.select();
                }
            } catch (e) { }
            setTimeout(() => document.addEventListener('mousedown', outsideClickListenerSearch), 10);
        }

        function outsideClickListenerSearch(e) {
            if (!searchMenu.contains(e.target)) {
                searchMenu.style.display = 'none';
                searchMenu.classList.add('visually-hidden');
                document.removeEventListener('mousedown', outsideClickListenerSearch);
            }
        }
        // Busca server-side: alterna para List e ajusta range para cobrir todos resultados
        function gotoListCoveringResults(qstr) {
            const ids = loadSelectedDentists();
            const includeUn = loadIncludeUnassigned();
            const params = new URLSearchParams({
                q: qstr || '',
                dentists: (ids && ids.length ? ids.join(',') : ''),
                include_unassigned: includeUn ? '1' : ''
            });
            fetch(`${BASE}/events/search_range?${params.toString()}`)
                .then(r => r.json())
                .then(j => {
                    const countEl = document.getElementById('searchResultsSummary');
                    if (countEl) {
                        const c = j && typeof j.count === 'number' ? j.count : 0;
                        countEl.textContent = qstr ? `${c} resultado(s)` : '';
                    }
                    if (!j || !j.min || !j.max) {
                        // sem resultados: vai para lista da semana atual e refetch com q
                        calendar.changeView('listWeek');
                        calendar.refetchEvents();
                        return;
                    }
                    try {
                        const start = new Date(j.min);
                        const end = new Date(j.max);
                        // Expandir 1 dia para garantir inclusão do fim (end é exclusivo)
                        end.setDate(end.getDate() + 1);
                        // Goto min e trocar para listMonth ou listWeek baseado no span
                        const diffDays = Math.max(1, Math.round((end - start) / 86400000));
                        if (diffDays > 35) {
                            calendar.changeView('listYear');
                        } else if (diffDays > 28) {
                            calendar.changeView('listMonth');
                        } else {
                            calendar.changeView('listWeek');
                        }
                        // O FullCalendar não permite setar range arbitrário em list sem customização,
                        // então navegamos para a data inicial; o refetch com q garantirá somente resultados.
                        calendar.gotoDate(start);
                        calendar.refetchEvents();
                    } catch (e) {
                        calendar.changeView('listWeek');
                        calendar.refetchEvents();
                    }
                })
                .catch(() => {
                    calendar.changeView('listWeek');
                    calendar.refetchEvents();
                });
        }

        function wireSearchMenu() {
            const inp = document.getElementById('searchQueryInput');
            const btn = document.getElementById('btnApplySearch');
            const clr = document.getElementById('btnClearSearch');
            if (inp) {
                inp.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        const qv = inp.value.trim();
                        saveSearchQuery(qv);
                        gotoListCoveringResults(qv);
                    }
                });
            }
            if (btn) btn.addEventListener('click', () => {
                const v = (inp && inp.value || '').trim();
                saveSearchQuery(v);
                gotoListCoveringResults(v);
            });
            if (clr) clr.addEventListener('click', () => {
                saveSearchQuery('');
                if (inp) inp.value = '';
                calendar.refetchEvents();
            });
        }
        wireSearchMenu();
        // Removido: injeção de extraParams em eventSources/events. 
        // Motivo: nossa função events() já inclui a query (q) ao montar a URL,
        // e mutar opções em runtime pode causar erros em algumas versões do FullCalendar.

        function setActiveThemeButton(theme) {
            document.querySelectorAll('#settingsMenu [data-theme]').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-theme') === theme);
            });
        }

        function setActiveDurationButton(mins) {
            document.querySelectorAll('#settingsMenu [data-duration]').forEach(btn => {
                const v = parseInt(btn.getAttribute('data-duration') || '0', 10);
                btn.classList.toggle('active', v === mins);
            });
        }

        function applyTheme(theme, persist = true) {
            try {
                const link = document.getElementById('theme-override');
                if (theme === 'default') {
                    link.removeAttribute('href');
                    try { document.body.classList.remove('theme-dark'); } catch (e) { }
                } else if (theme === 'dark') {
                    link.setAttribute('href', staticBase + '/themes/theme-dark.css');
                    try { document.body.classList.add('theme-dark'); } catch (e) { }
                } else if (theme === 'contrast') {
                    link.setAttribute('href', staticBase + '/themes/theme-contrast.css');
                    try { document.body.classList.remove('theme-dark'); } catch (e) { }
                }
                if (persist) localStorage.setItem('calendarTheme', theme);
            } catch (e) {
                /* noop */
            }
        }
        // Listeners dos botões do menu de configurações
        document.querySelectorAll('#settingsMenu [data-theme]').forEach(btn => {
            btn.addEventListener('click', () => {
                const t = btn.getAttribute('data-theme');
                applyTheme(t);
                setActiveThemeButton(t);
            });
        });
        // Duração padrão do novo evento (em minutos)
        document.querySelectorAll('#settingsMenu [data-duration]').forEach(btn => {
            btn.addEventListener('click', () => {
                let mins = parseInt(btn.getAttribute('data-duration') || '60', 10);
                if (!isFinite(mins) || mins <= 0 || mins === 15) mins = 60;
                try {
                    localStorage.setItem('defaultEventDurationMin', String(mins));
                } catch (e) { }
                setActiveDurationButton(mins);
            });
        });
        // Weekends toggle (timeGridWeek)
        document.querySelectorAll('#settingsMenu [data-weekends]').forEach(btn => {
            btn.addEventListener('click', () => {
                const val = btn.getAttribute('data-weekends') === 'true';
                setWeekendsSetting(val);
                document.querySelectorAll('#settingsMenu [data-weekends]').forEach(b => {
                    b.classList.toggle('active', b === btn);
                });
                const viewType = calendar.view && calendar.view.type;
                if (viewType && viewType.startsWith('timeGrid')) {
                    calendar.setOption('weekends', val);
                }
            });
        });

        // Re-apply weekends per view dates change
        calendar.on('datesSet', function () {
            const val = getWeekendsSetting();
            calendar.setOption('weekends', val);
            updateHolidaysForCurrentView();
        });
        // prime holidays on initial render
        setTimeout(() => {
            updateHolidaysForCurrentView();
        }, 50);
        // aviso inicial de filtros vazios
        setTimeout(() => {
            updateEmptyFilterNoticeDeb();
        }, 10);
        // ==== Invertexto token and refresh (lazy init) ====
        let __holidaysUIInitialized = false;

        function initHolidaysUIOnce() {
            if (__holidaysUIInitialized) return;
            __holidaysUIInitialized = true;
            const tokenInput = document.getElementById('invertextoToken');
            const yearInput = document.getElementById('holidaysYear');
            const ufInput = document.getElementById('holidaysState');
            const btn = document.getElementById('btnRefreshHolidays');
            const statusEl = document.getElementById('holidaysStatus');
            const clearBtn = document.getElementById('btnClearToken');
            const hardRefreshBtn = document.getElementById('btnHardRefresh');
            const tokenBadge = document.getElementById('tokenStatusBadge');
            if (!tokenInput || !yearInput || !btn) return;
            // Prefill year
            try {
                yearInput.value = String(new Date().getFullYear());
            } catch (e) { }
            // Check if token configured
            function updateTokenBadge(has) {
                if (!tokenBadge) return;
                tokenBadge.textContent = has ? 'Token configurado' : 'Token não configurado';
                tokenBadge.className = has ? 'badge bg-success' : 'badge bg-secondary';
            }

            function fetchAndUpdateTokenBadge() {
                return fetch(BASE + '/settings/invertexto_token')
                    .then(r => r.json())
                    .then(j => {
                        const has = !!(j && j.hasToken);
                        if (!has) statusEl.textContent = 'Token não configurado.';
                        updateTokenBadge(has);
                    })
                    .catch(() => { });
            }
            // Expor para chamada quando abrir o menu
            window.__fetchAndUpdateTokenBadge = fetchAndUpdateTokenBadge;
            // Save token on blur
            function saveToken(value) {
                const v = (value || '').trim();
                if (!v) return Promise.resolve();
                statusEl.textContent = 'Salvando token...';
                return fetch(BASE + '/settings/invertexto_token', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        token: v
                    })
                }).then(r => r.json()).then(j => {
                    if (j && j.status === 'success') {
                        statusEl.textContent = 'Token salvo.';
                        tokenInput.value = '';
                        updateTokenBadge(true);
                    } else {
                        statusEl.textContent = 'Falha ao salvar token.';
                    }
                }).catch(() => {
                    statusEl.textContent = 'Erro ao salvar token.';
                });
            }
            if (clearBtn) {
                clearBtn.addEventListener('click', () => {
                    fetch(BASE + '/settings/invertexto_token', {
                        method: 'DELETE'
                    })
                        .then(r => r.json())
                        .then(j => {
                            if (j && j.status === 'success') {
                                statusEl.textContent = 'Token removido.';
                                updateTokenBadge(false);
                            } else {
                                statusEl.textContent = 'Falha ao remover token.';
                            }
                        })
                        .catch(() => {
                            statusEl.textContent = 'Erro ao remover token.';
                        });
                });
            }
            if (hardRefreshBtn) {
                hardRefreshBtn.addEventListener('click', () => {
                    try { hardRefreshBtn.disabled = true; } catch (e) { }
                    showToast('Limpando cache...', 'warning', 1200);
                    // 1) Clear client caches
                    try {
                        // events cache (in-memory)
                        if (sharedEventsCache) {
                            sharedEventsCache.key = null;
                            sharedEventsCache.start = null;
                            sharedEventsCache.end = null;
                            sharedEventsCache.events = [];
                        }
                    } catch (e) { }
                    try {
                        // dentists cache (localStorage + memory)
                        localStorage.removeItem('dentistsCacheV1');
                        if (typeof dentistsCache === 'object') {
                            dentistsCache.list = [];
                            dentistsCache.map = {};
                        }
                    } catch (e) { }
                    try {
                        // holidays year cache (client)
                        for (const y in holidaysYearCache) delete holidaysYearCache[y];
                        for (const y in holidaysYearPending) delete holidaysYearPending[y];
                    } catch (e) { }
                    // 2) Clear server caches
                    let serverCleared = false;
                    fetch(BASE + '/cache/clear', { method: 'POST' })
                        .then(r => { if (!r.ok) throw new Error('server'); serverCleared = true; })
                        .catch(() => { /* keep serverCleared=false */ })
                        .finally(() => {
                            // 3) Rebuild UI data
                            try {
                                fetchDentistsOnce(true).then(list => {
                                    // Sanitize persisted selection to valid dentists only
                                    try {
                                        const valid = new Set((Array.isArray(list) ? list : []).map(d => Number(d.id)));
                                        let selected = (loadSelectedDentists() || []).map(Number).filter(id => valid.has(id));
                                        // If nothing remains selected, default to all current valid dentists
                                        if (!selected || selected.length === 0) {
                                            selected = (Array.isArray(list) ? list : []).map(d => Number(d.id));
                                        }
                                        saveSelectedDentists(selected);
                                    } catch (e) { }
                                    // Rebuild popover select options to reflect valid dentists
                                    try {
                                        const sel = document.getElementById('popoverDentist');
                                        if (sel) {
                                            // Remove all options except the empty one
                                            for (let i = sel.options.length - 1; i >= 0; i--) {
                                                const opt = sel.options[i];
                                                if (opt && opt.value !== '') sel.remove(i);
                                            }
                                            (Array.isArray(list) ? list : []).forEach(d => {
                                                const opt = document.createElement('option');
                                                opt.value = String(d.id);
                                                opt.textContent = d.nome || String(d.id);
                                                sel.appendChild(opt);
                                            });
                                            const selected = loadSelectedDentists();
                                            if (selected && selected.length === 1) sel.value = String(selected[0]);
                                            else sel.value = '';
                                        }
                                    } catch (e) { }
                                    // Re-render sidebar and notices
                                    try { renderDentistsSidebar(Array.isArray(list) ? list : []); } catch (e) { }
                                    try { updateEmptyFilterNoticeDeb(); } catch (e) { }
                                    // Keep mini calendar in sync
                                    try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                                    try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) { }
                                });
                            } catch (e) { }
                            try { calendar.refetchEvents(); } catch (e) { }
                            try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                            try { if (typeof updateHolidaysForCurrentView === 'function') updateHolidaysForCurrentView(); } catch (e) { }
                            showToast(serverCleared ? 'Cache limpo e recarregado.' : 'Cache local limpo. Falha ao limpar no servidor.', serverCleared ? 'success' : 'danger', 2500);
                            try { hardRefreshBtn.disabled = false; } catch (e) { }
                        });
                });
            }
            tokenInput.addEventListener('change', () => {
                saveToken(tokenInput.value);
            });
            // Refresh action
            btn.addEventListener('click', () => {
                const year = parseInt(yearInput.value || '0', 10);
                const uf = (ufInput && ufInput.value || '').toUpperCase().trim();
                if (!year || year < 1900) {
                    statusEl.textContent = 'Ano inválido.';
                    return;
                }
                statusEl.textContent = 'Atualizando feriados...';
                const maybeToken = (tokenInput.value || '').trim();
                const doRefresh = () => fetch(BASE + '/holidays/refresh', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        year: year,
                        state: uf || undefined
                    })
                }).then(r => r.json()).then(j => {
                    if (j && j.status === 'success') {
                        statusEl.textContent = `Atualizado. ${j.count || 0} registros.`;
                        // Invalidate year cache and rebuild for current view
                        for (const y in holidaysYearCache) delete holidaysYearCache[y];
                        for (const y in holidaysYearPending) delete holidaysYearPending[y];
                        try {
                            updateHolidaysForCurrentView();
                        } catch (e) { }
                    } else {
                        const msg = (j && j.message) ? j.message : 'Falha ao atualizar.';
                        statusEl.textContent = msg + (msg.includes('Não autorizado') ? ' Verifique o token e tente novamente.' : '');
                    }
                }).catch(() => {
                    statusEl.textContent = 'Erro ao atualizar.';
                });
                if (maybeToken) {
                    saveToken(maybeToken).then(doRefresh);
                } else {
                    doRefresh();
                }
            });
        }

        // Função para configurar autocompletar nativo
        function setupAutocomplete() {
            const titleInput = document.getElementById('popoverEventTitle');
            const datalist = document.getElementById('namesList');
            let currentTimeout = null;
            let suggestions = [];
            let currentIndex = -1;

            titleInput.addEventListener('input', function () {
                const query = this.value.trim();
                // Limpar timeout anterior
                if (currentTimeout) {
                    clearTimeout(currentTimeout);
                }
                if (query.length >= 1) {
                    // Aguardar 300ms antes de fazer a busca
                    currentTimeout = setTimeout(() => {
                        fetch(`${BASE}/buscar_nomes?q=${encodeURIComponent(query)}`)
                            .then(response => response.json())
                            .then(nomes => {
                                suggestions = nomes;
                                currentIndex = -1;
                                updateDatalist(nomes);
                            })
                            .catch(error => {
                                console.error('Erro ao buscar nomes:', error);
                                datalist.innerHTML = '';
                                suggestions = [];
                            });
                    }, 300);
                } else {
                    datalist.innerHTML = '';
                    suggestions = [];
                    currentIndex = -1;
                }
            });

            titleInput.addEventListener('keydown', function (e) {
                if (e.key === 'Tab' && suggestions.length > 0) {
                    e.preventDefault();
                    currentIndex = (currentIndex + 1) % suggestions.length;
                    this.value = suggestions[currentIndex];
                }
            });

            function updateDatalist(nomes) {
                datalist.innerHTML = '';
                nomes.forEach(nome => {
                    const option = document.createElement('option');
                    option.value = nome;
                    datalist.appendChild(option);
                });
            }
        }
    });
}
    // Ensure initialization runs even if this script is loaded after DOMContentLoaded
    // (template includes app.js at the end of the body). If DOM is already ready, run now.
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', __initAgendaApp);
    } else {
        __initAgendaApp();
    }
