/* eslint-env browser */
/* global FullCalendar, flatpickr, applyClientSearchFilter, Intl */

// calendar.js: FullCalendar instantiation and main app wiring (ES Modules)
import {
    setBase,
    getTheme, setTheme,
    getWeekendsSetting, setWeekendsSetting,
    loadSelectedDentists, saveSelectedDentists,
    loadIncludeUnassigned, saveIncludeUnassigned,
    getDefaultEventDurationMin, setDefaultEventDurationMin,
    saveSearchQuery, loadSearchQuery,
    sharedEventsCache, pendingEventsFetches, buildCacheKey, storeEventsToCache, cacheCoversRange, eventsFromCache,
    updateEventInCacheById, removeEventFromCacheById, addEventToCache,
    dentistsCache, fetchDentistsOnce, clearDentistsCache,
    ensureRangeCached, buildVisibleHolidaysFromCache, clearHolidaysCache
} from './storage.js';
import {
    debounce, rafThrottle, showToast,
    formatLocalYmdHm, toLocalISO, ymdFromDate,
    computePopupPosition, extractPhoneFromText,
    colorForDentist, repaintDentistBarsForEvent
} from './utils.js';

function ymdhmss(d) {
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}
function startOfDay(d) { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; }
function startOfMonth(d) { return new Date(d.getFullYear(), d.getMonth(), 1); }
function startOfNextMonth(d) { return new Date(d.getFullYear(), d.getMonth() + 1, 1); }

export function initCalendarApp() {
    const BASE = (typeof window !== 'undefined' && window.__AGENDA_BASE__) ? window.__AGENDA_BASE__ : '';
    setBase(BASE);
    const staticBase = BASE + '/static';
    const calendarEl = document.getElementById('calendar');

    // preload templates
    Promise.all([
        fetch(staticBase + '/event-popover.html').then(res => res.text()),
        fetch(staticBase + '/event-contextmenu.html').then(res => res.text()),
        fetch(staticBase + '/event-detail-popover.html').then(res => res.text()),
        fetch(staticBase + '/settings-menu.html').then(res => res.text()),
        fetch(staticBase + '/search-menu.html').then(res => res.text())
    ]).then(([popoverHtml, contextHtml, detailPopoverHtml, settingsMenuHtml, searchMenuHtml]) => {
        try { const popWrap = document.getElementById('popover-container'); if (popWrap) popWrap.innerHTML = popoverHtml; } catch (e) { console.error('An error occurred:', e); }
        try { const ctxWrap = document.getElementById('contextmenu-container'); if (ctxWrap) ctxWrap.innerHTML = contextHtml; } catch (e) { console.error('An error occurred:', e); }
        try {
            if (!document.getElementById('eventDetailPopover')) {
                document.body.insertAdjacentHTML('beforeend', detailPopoverHtml);
            } else {
                const el = document.getElementById('eventDetailPopover');
                if (el && el.parentElement !== document.body) document.body.appendChild(el);
            }
        } catch (e) { console.error('An error occurred:', e); }
        try { document.getElementById('settingsmenu-container').innerHTML = settingsMenuHtml; } catch (e) { console.error('An error occurred:', e); }
        let searchContainer = document.getElementById('searchmenu-container');
        if (!searchContainer) { searchContainer = document.createElement('div'); searchContainer.id = 'searchmenu-container'; document.body.appendChild(searchContainer); }
        searchContainer.innerHTML = searchMenuHtml;
        try {
            const menu = document.getElementById('eventContextMenu');
            if (menu) { if (menu.parentElement !== document.body) document.body.appendChild(menu); menu.style.display = 'none'; }
        } catch (e) { console.error('An error occurred:', e); }

        // Init pickers base instances to enforce BR formats
        try {
            const s1 = document.getElementById('popoverEventStart');
            const e1 = document.getElementById('popoverEventEnd');
            const sD = document.getElementById('popoverEventStartDate');
            const eD = document.getElementById('popoverEventEndDate');
            if (window.flatpickr && s1 && e1 && sD && eD) {
                const fpDateOpts = { enableTime: false, allowInput: true, locale: (window.flatpickr?.l10ns?.pt) || 'pt', dateFormat: 'Y-m-d', altInput: true, altFormat: 'd/m/Y' };
                const fpDateTimeOpts = { enableTime: true, time_24hr: true, allowInput: true, minuteIncrement: 5, locale: (window.flatpickr?.l10ns?.pt) || 'pt', dateFormat: 'Y-m-d\\TH:i', altInput: true, altFormat: 'd/m/Y H:i' };
                flatpickr(s1, fpDateTimeOpts); flatpickr(e1, fpDateTimeOpts); flatpickr(sD, fpDateOpts); flatpickr(eD, fpDateOpts);
            }
        } catch (e) { console.error('An error occurred:', e); }

        // Apply saved theme
        const savedTheme = getTheme();
        applyTheme(savedTheme, false);

        // Build plugins array defensively
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

        // Holidays visible cache for current main view
        let holidayDates = new Set();
        let holidayMeta = {};
        const dayCellEls = {}; // date -> [elements]
        function syncHolidayHighlight() {
            Object.keys(dayCellEls).forEach(d => {
                (dayCellEls[d] || []).forEach(el => {
                    if (!el || !el.classList) return;
                    if (holidayDates.has(d)) {
                        el.classList.add('fc-day-holiday');
                        const meta = holidayMeta[d];
                        if (meta && el.setAttribute) el.setAttribute('title', meta.name);
                    } else {
                        el.classList.remove('fc-day-holiday');
                        if (el.getAttribute && el.getAttribute('title')) el.removeAttribute('title');
                    }
                });
            });
        }
        function updateHolidaysForCurrentView(calendar) {
            const view = calendar.view;
            if (!(view && view.currentStart && view.currentEnd)) return Promise.resolve();
            const start = new Date(view.currentStart);
            const endInc = new Date(view.currentEnd); endInc.setDate(endInc.getDate() - 1);
            return ensureRangeCached(start, endInc).then(() => {
                const built = buildVisibleHolidaysFromCache(start, endInc);
                holidayDates = built.dates; holidayMeta = built.meta; syncHolidayHighlight();
            });
        }

        function applyTheme(theme, persist = true) {
            try {
                const link = document.getElementById('theme-override');
                if (theme === 'default') {
                    link && link.removeAttribute('href');
                    try { document.body.classList.remove('theme-dark'); } catch (e) { console.error('An error occurred:', e); }
                } else if (theme === 'dark') {
                    link && link.setAttribute('href', staticBase + '/themes/theme-dark.css');
                    try { document.body.classList.add('theme-dark'); } catch (e) { console.error('An error occurred:', e); }
                } else if (theme === 'contrast') {
                    link && link.setAttribute('href', staticBase + '/themes/theme-contrast.css');
                    try { document.body.classList.remove('theme-dark'); } catch (e) { console.error('An error occurred:', e); }
                }
                if (persist) setTheme(theme);
            } catch (e) { console.error('An error occurred:', e); }
        }

        // Settings/Search menu toggle helpers
        const settingsMenu = document.getElementById('settingsMenu');
        const searchMenu = document.getElementById('searchMenu');
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

        function toggleSettingsMenu(anchorEl, calendar) {
            if (!settingsMenu) return;
            const onOpen = () => {
                try {
                    setActiveThemeButton(getTheme());
                    let saved = getDefaultEventDurationMin();
                    setActiveDurationButton(saved);
                    document.querySelectorAll('#settingsMenu [data-weekends]').forEach(btn => {
                        const wk = getWeekendsSetting();
                        btn.classList.toggle('active', String(wk) === btn.getAttribute('data-weekends'));
                    });
                    if (window.__fetchAndUpdateTokenBadge) window.__fetchAndUpdateTokenBadge();
                } catch (e) { console.error('An error occurred:', e); }
            };
            const { toggleMenu } = awaitImportToggle();
            toggleMenu(settingsMenu, anchorEl, onOpen, null);
        }
        function toggleSearchMenu(anchorEl) {
            if (!searchMenu) return;
            const onOpen = () => {
                try {
                    const inp = document.getElementById('searchQueryInput');
                    if (inp) { inp.value = loadSearchQuery(); inp.focus(); inp.select(); }
                } catch (e) { console.error('An error occurred:', e); }
            };
            const { toggleMenu } = awaitImportToggle();
            toggleMenu(searchMenu, anchorEl, onOpen, null);
        }
        function awaitImportToggle() {
            return {
                toggleMenu: (el, anchor, onOpen, onClose) => {
                    const isVisible = el.style.display === 'block';
                    const outsideListener = (e) => {
                        if (!el.contains(e.target)) {
                            try { el.style.display = 'none'; el.classList.add('visually-hidden'); } catch (err) { console.error('An error occurred:', err); }
                            document.removeEventListener('mousedown', outsideListener);
                            if (typeof onClose === 'function') onClose();
                        }
                    };
                    if (isVisible) {
                        el.style.display = 'none'; el.classList.add('visually-hidden'); document.removeEventListener('mousedown', outsideListener); if (typeof onClose === 'function') onClose(); return;
                    }
                    el.style.display = 'block'; el.classList.remove('visually-hidden');
                    setTimeout(() => { try { const r = el.getBoundingClientRect(); const pos = computePopupPosition(r.width, r.height, anchor); el.style.position = 'fixed'; el.style.left = pos.left + 'px'; el.style.top = pos.top + 'px'; el.style.zIndex = '10000'; } catch (e) { console.error('An error occurred:', e); } }, 10);
                    if (typeof onOpen === 'function') onOpen();
                    setTimeout(() => document.addEventListener('mousedown', outsideListener), 10);
                }
            };
        }

        const updateEmptyFilterNotice = (() => {
            let emptyNoticeTimer = null;
            return function () {
                try {
                    const el = document.getElementById('filterNotice');
                    if (!el) return;
                    const ids = loadSelectedDentists();
                    const includeUn = loadIncludeUnassigned();
                    const show = (!ids || ids.length === 0) && !includeUn;
                    if (emptyNoticeTimer) { clearTimeout(emptyNoticeTimer); emptyNoticeTimer = null; }
                    if (show) {
                        emptyNoticeTimer = setTimeout(() => { try { el.style.display = 'block'; } catch (e) { console.error('An error occurred:', e); } }, 350);
                    } else { el.style.display = 'none'; }
                } catch (e) { console.error('An error occurred:', e); }
            };
        })();
        const updateEmptyFilterNoticeDeb = debounce(updateEmptyFilterNotice, 200);

        const calendar = new FullCalendar.Calendar(calendarEl, {
            themeSystem: 'bootstrap5',
            locale: 'pt-br',
            initialView: 'timeGridWeek',
            eventTimeFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
            slotLabelFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
            customButtons: {
                prev: { text: '‹', click: () => calendar.prev() },
                next: { text: '›', click: () => calendar.next() },
                prevYear: { text: '≪', click: () => { const d = calendar.getDate(); calendar.gotoDate(new Date(d.getFullYear(), d.getMonth() - 1, d.getDate())); } },
                nextYear: { text: '≫', click: () => { const d = calendar.getDate(); calendar.gotoDate(new Date(d.getFullYear(), d.getMonth() + 1, d.getDate())); } },
                settings: { text: 'Configurações', click: function () { const btn = calendarEl.querySelector('.fc-settings-button'); if (!btn) return; const wrap = document.getElementById('settingsmenu-container'); if (wrap && wrap.childElementCount === 0) { fetch(staticBase + '/settings-menu.html').then(r => r.text()).then(html => { wrap.innerHTML = html; toggleSettingsMenu(btn, calendar); }).catch(() => toggleSettingsMenu(btn, calendar)); return; } toggleSettingsMenu(btn, calendar); } },
                search: { text: 'Buscar', click: function () { const btn = calendarEl.querySelector('.fc-search-button'); if (!btn) return; let wrap = document.getElementById('searchmenu-container'); if (!wrap) { wrap = document.createElement('div'); wrap.id = 'searchmenu-container'; document.body.appendChild(wrap); } if (wrap.childElementCount === 0) { fetch(staticBase + '/search-menu.html').then(r => r.text()).then(html => { wrap.innerHTML = html; toggleSearchMenu(btn); wireSearchMenu(calendar, BASE); }).catch(() => { toggleSearchMenu(btn); wireSearchMenu(calendar, BASE); }); return; } toggleSearchMenu(btn); wireSearchMenu(calendar, BASE); } }
            },
            headerToolbar: { left: 'prev,next today settings search', center: 'title', right: 'prevYear,nextYear dayGridMonth,timeGridWeek,timeGridDay,listWeek,multiMonthYear' },
            buttonText: { today: 'Hoje', month: 'Mês', week: 'Semana', day: 'Dia', list: 'Lista', listWeek: 'Lista', listMonth: 'Lista mês', listYear: 'Lista ano', dayGridMonth: 'Mês', timeGridWeek: 'Semana', timeGridDay: 'Dia', multiMonthYear: 'Ano' },
            moreLinkText: (n) => `+${n} mais`,
            views: { dayGridMonth: { eventDisplay: 'block' }, multiMonthYear: { type: 'multiMonth', duration: { years: 1 }, multiMonthMaxColumns: 3, eventDisplay: 'block', buttonText: 'Ano' } },
            plugins,
            dayCellClassNames: (arg) => (holidayDates.has(toLocalISO(arg.date)) ? ['fc-day-holiday'] : []),
            dayCellDidMount: (arg) => {
                const iso = toLocalISO(arg.date);
                if (!dayCellEls[iso]) dayCellEls[iso] = [];
                dayCellEls[iso].push(arg.el);
                if (holidayDates.has(iso)) { arg.el.classList.add('fc-day-holiday'); const meta = holidayMeta[iso]; if (meta && arg.el?.setAttribute) arg.el.setAttribute('title', meta.name); }
            },
            eventDidMount: function (info) {
                try {
                    // Tag element for later repaint and apply initial dentist color bars
                    if (info.el && info.event?.id != null) info.el.setAttribute('data-eid', String(info.event.id));
                    const pid = info.event?.extendedProps?.profissional_id;
                    repaintDentistBarsForEvent(info.event.id, pid, dentistsCache?.map || {});
                } catch (e) { console.error('An error occurred:', e); }

                // Right-click context menu
                try {
                    info.el.addEventListener('contextmenu', function (e) {
                        e.preventDefault();
                        const menu = document.getElementById('eventContextMenu');
                        if (!menu) return;
                        // position and show
                        menu.style.display = 'block';
                        menu.classList.remove('visually-hidden');
                        setTimeout(() => {
                            try {
                                const r = menu.getBoundingClientRect();
                                const pos = computePopupPosition(r.width, r.height, info.el);
                                menu.style.position = 'fixed';
                                menu.style.left = pos.left + 'px';
                                menu.style.top = pos.top + 'px';
                                menu.style.zIndex = '10000';
                            } catch (err) { console.error('An error occurred:', err); }
                        }, 10);

                        const closeMenu = () => { try { menu.style.display = 'none'; menu.classList.add('visually-hidden'); } catch (e2) { console.error('An error occurred:', e2); } document.removeEventListener('mousedown', outsideListener); };
                        const outsideListener = (evt) => { if (!menu.contains(evt.target)) closeMenu(); };
                        setTimeout(() => document.addEventListener('mousedown', outsideListener), 10);

                        function fmtDate(d) { const pad = (n) => String(n).padStart(2, '0'); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }
                        function fmtDateTime(d) { const pad = (n) => String(n).padStart(2, '0'); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`; }
                        function addDays(d, n) { const nd = new Date(d); nd.setDate(nd.getDate() + n); return nd; }
                        function addMonths(d, n) { const nd = new Date(d); nd.setMonth(nd.getMonth() + n); return nd; }

                        function duplicateWith(offset) {
                            try {
                                const ev = info.event;
                                const isAllDay = !!ev.allDay;
                                const start = new Date(ev.start);
                                const end = ev.end ? new Date(ev.end) : (isAllDay ? addDays(start, 1) : addDays(start, 1));
                                const pid2 = ev.extendedProps && ev.extendedProps.profissional_id ? Number(ev.extendedProps.profissional_id) : null;
                                let newStart, newEnd;
                                if (offset.type === 'd') { newStart = addDays(start, offset.value); newEnd = addDays(end, offset.value); }
                                else if (offset.type === 'm') { newStart = addMonths(start, offset.value); newEnd = addMonths(end, offset.value); }
                                const body = { title: ev.title || '', start: isAllDay ? fmtDate(newStart) : fmtDateTime(newStart), end: isAllDay ? fmtDate(newEnd) : fmtDateTime(newEnd), notes: '', color: '#f59e42', profissional_id: pid2 };
                                fetch(BASE + '/add_event', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
                                    .then(r => r.json()).then(j => {
                                        if (j && j.status === 'success' && j.event) {
                                            try { calendar.addEvent(j.event); addEventToCache(j.event); if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); closeMenu(); showToast('Evento duplicado.', 'success', 1400); } catch (e3) { console.error('An error occurred:', e3); calendar.refetchEvents(); }
                                        } else { alert('Erro ao duplicar evento.'); }
                                    }).catch(() => alert('Erro ao duplicar evento.'));
                            } catch (err) { console.error('An error occurred:', err); }
                        }

                        const dup1w = document.getElementById('dup1wBtn'); if (dup1w) dup1w.onclick = () => duplicateWith({ type: 'd', value: 7 });
                        const dup2w = document.getElementById('dup2wBtn'); if (dup2w) dup2w.onclick = () => duplicateWith({ type: 'd', value: 14 });
                        const dup3w = document.getElementById('dup3wBtn'); if (dup3w) dup3w.onclick = () => duplicateWith({ type: 'd', value: 21 });
                        const dup4w = document.getElementById('dup4wBtn'); if (dup4w) dup4w.onclick = () => duplicateWith({ type: 'd', value: 28 });
                        const dup1m = document.getElementById('dup1mBtn'); if (dup1m) dup1m.onclick = () => duplicateWith({ type: 'm', value: 1 });

                        const delBtn = document.getElementById('deleteEventBtn');
                        if (delBtn) delBtn.onclick = function () {
                            fetch(BASE + '/delete_event', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: info.event.id }) })
                                .then(r => r.json()).then(d => { if (d.status === 'success') { try { info.event.remove(); } catch (e4) { console.error('An error occurred:', e4); } removeEventFromCacheById(info.event.id); try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e5) { console.error('An error occurred:', e5); } closeMenu(); showToast('Evento excluído.', 'success', 1200); } else { alert('Erro ao deletar evento!'); } });
                        };

                        const colorCircles = menu.querySelectorAll('#colorOptions .color-circle');
                        colorCircles.forEach((circle) => {
                            circle.onclick = function () {
                                const color = this.getAttribute('data-color');
                                fetch(BASE + '/update_event_color', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: info.event.id, color }) })
                                    .then(r => r.json()).then(d => { if (d.status === 'success') { try { info.event.setProp('backgroundColor', color); info.event.setProp('borderColor', color); } catch (e6) { console.error('An error occurred:', e6); } updateEventInCacheById(info.event.id, { color }); try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e7) { console.error('An error occurred:', e7); } closeMenu(); } else { alert('Erro ao atualizar cor!'); } });
                            };
                        });
                    });
                } catch (e) { console.error('An error occurred:', e); }

                // Enrich items rendered inside "+X more" popover with title/time/notes
                try {
                    setTimeout(() => {
                        const pop = info.el.closest('.fc-more-popover');
                        if (!pop) return;
                        const isAllDay = info.event.allDay;
                        let timeStr = '';
                        if (!isAllDay && info.event.start) {
                            try { timeStr = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit', hour12: false }).format(info.event.start); }
                            catch (_) { const d = info.event.start; const hh = String(d.getHours()).padStart(2, '0'); const mm = String(d.getMinutes()).padStart(2, '0'); timeStr = `${hh}:${mm}`; }
                        }
                        const title = info.event.title || '';
                        const notes = (info.event.extendedProps && info.event.extendedProps.notes) ? info.event.extendedProps.notes : '';
                        const sep = timeStr ? `<span class="fc-event-time-start"> ${timeStr}</span>` : '';
                        const notesLine = notes ? `<div class="fc-event-notes">${notes}</div>` : '';
                        const html = `<div class="fc-event-main-custom fc-popover-rich"><div class="line1"><span class="fc-event-title">${title}</span>${sep}</div>${notesLine}</div>`;
                        const main = info.el.querySelector('.fc-event-main') || info.el.querySelector('.fc-event-main-frame') || info.el;
                        if (main) main.innerHTML = html;
                    }, 0);
                } catch (e) { console.error('An error occurred:', e); }

                // Apply client-side search filter, if provided by page
                try { if (typeof applyClientSearchFilter === 'function') applyClientSearchFilter(); } catch (e) { console.error('An error occurred:', e); }
            },
            selectable: true,
            editable: true,
            nowIndicator: true,
            navLinks: true,
            weekends: getWeekendsSetting(),
            eventContent: function (arg) {
                const isAllDay = arg.event.allDay;
                const title = arg.event.title || '';
                function fmtTime(date) {
                    if (!date) return '';
                    try { return new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit', hour12: false }).format(date); } catch (e) {
                        const d = date; const hh = String(d.getHours()).padStart(2, '0'); const mm = String(d.getMinutes()).padStart(2, '0'); return `${hh}:${mm}`;
                    }
                }
                if (arg.view.type === 'timeGridWeek') {
                    let timeStr = (!isAllDay && arg.event.start) ? fmtTime(arg.event.start) : '';
                    let durationMin = 0;
                    if (!isAllDay && arg.event.start && arg.event.end) durationMin = Math.max(0, Math.round((arg.event.end - arg.event.start) / 60000));
                    else if (!isAllDay && arg.event.start && !arg.event.end) durationMin = 60;
                    let html;
                    if (durationMin > 30) {
                        const timeLine = timeStr ? `<div class="fc-event-time-start">${timeStr}</div>` : '';
                        html = `<div class="fc-event-main-custom two-line"><div class="fc-event-title">${title}</div>${timeLine}</div>`;
                    } else {
                        const timeInline = timeStr ? `<span class=\"fc-event-time-start\"> ${timeStr}</span>` : '';
                        html = `<div class=\"fc-event-main-custom\"><span class=\"fc-event-title\">${title}</span>${timeInline}</div>`;
                    }
                    return { html };
                }
                if (arg.view.type === 'timeGridDay') {
                    const notes = arg.event.extendedProps?.notes || '';
                    let durationMin = 0;
                    if (!arg.event.allDay && arg.event.start) durationMin = Math.max(0, Math.round(((arg.event.end || new Date(arg.event.start.getTime() + 3600000)) - arg.event.start) / 60000));
                    let sizeClass = '';
                    if (durationMin >= 120) sizeClass = ' size-large';
                    else if (durationMin >= 60) sizeClass = ' size-medium';
                    const sep = notes ? ' - ' : '';
                    const html = `<div class=\"fc-event-main-custom${sizeClass}\"><span class=\"fc-event-title fw-bold\">${title}</span>${sep}<span class=\"fc-event-notes\">${notes}</span></div>`;
                    return { html };
                }
                if (arg.view.type && arg.view.type.startsWith('list')) {
                    const notes = arg.event.extendedProps?.notes || '';
                    const sep = notes ? ' - ' : '';
                    return { html: `<span class=\"fc-event-title fw-bold\">${title}</span>${sep}<span class=\"fc-event-notes\">${notes}</span>` };
                }
                if (arg.view.type === 'dayGridMonth' || (arg.view.type && arg.view.type.startsWith('multiMonth'))) {
                    const timeStr = (!isAllDay && arg.event.start) ? fmtTime(arg.event.start) : '';
                    const timeInline = timeStr ? `<span class=\"fc-event-time-start\"> ${timeStr}</span>` : '';
                    return { html: `<div class=\"fc-event-main-custom fc-month-line\"><span class=\"fc-event-title\">${title}</span>${timeInline}</div>` };
                }
                return undefined;
            },
            events: function (fetchInfo, success, failure) {
                try {
                    const key = buildCacheKey();
                    let covStart, covEnd;
                    const override = (typeof window !== 'undefined' && window.__fetchMonthOverride) ? window.__fetchMonthOverride : null;
                    const usedOverride = !!override;
                    if (override && override.start && override.end) {
                        covStart = startOfDay(new Date(override.start));
                        covEnd = startOfDay(new Date(override.end));
                    } else {
                        const vs = new Date(fetchInfo.start);
                        const ve = new Date(fetchInfo.end);
                        const monthStart = startOfMonth(vs);
                        const endInc = new Date(ve); endInc.setDate(endInc.getDate() - 1);
                        const lastMonthStart = startOfMonth(endInc);
                        const monthEnd = startOfNextMonth(lastMonthStart);
                        covStart = startOfDay(monthStart);
                        covEnd = startOfDay(monthEnd);
                    }
                    const dedupKey = `${key}|${covStart.toISOString()}|${covEnd.toISOString()}`;
                    if (cacheCoversRange(covStart, covEnd, key)) {
                        const result = eventsFromCache(new Date(fetchInfo.start), new Date(fetchInfo.end), key);
                        success(result);
                        try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { console.error('An error occurred:', e); }
                        try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) { console.error('An error occurred:', e); }
                        return;
                    }
                    if (pendingEventsFetches.has(dedupKey)) {
                        pendingEventsFetches.get(dedupKey)
                            .then(() => {
                                const result = eventsFromCache(new Date(fetchInfo.start), new Date(fetchInfo.end), key);
                                success(result);
                                try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { console.error('An error occurred:', e); }
                                try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) { console.error('An error occurred:', e); }
                            })
                            .catch(err => { if (typeof failure === 'function') failure(err instanceof Error ? err : new Error('Failed to load events')); else success([]); });
                        return;
                    }
                    const ids = loadSelectedDentists();
                    const includeUn = loadIncludeUnassigned();
                    const q = loadSearchQuery();
                    const params = new URLSearchParams({ dentists: (ids && ids.length ? ids.join(',') : ''), include_unassigned: includeUn ? '1' : '', q: q || '', start: ymdhmss(covStart), end: ymdhmss(covEnd) });
                    const p = fetch(`${BASE}/events?${params.toString()}`)
                        .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
                        .then(list => {
                            storeEventsToCache(Array.isArray(list) ? list : [], covStart, covEnd, key);
                            const result = eventsFromCache(new Date(fetchInfo.start), new Date(fetchInfo.end), key);
                            success(result);
                            try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { console.error('An error occurred:', e); }
                            try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) { console.error('An error occurred:', e); }
                        })
                        .catch(err => { if (typeof failure === 'function') failure(err instanceof Error ? err : new Error('Failed to load events')); else success([]); })
                        .finally(() => { try { pendingEventsFetches.delete(dedupKey); } catch (e) { console.error('An error occurred:', e); } try { if (usedOverride) window.__fetchMonthOverride = null; } catch (e) { console.error('An error occurred:', e); } });
                    pendingEventsFetches.set(dedupKey, p);
                } catch (e) { if (typeof failure === 'function') failure(e instanceof Error ? e : new Error('Unexpected error')); else success([]); }
            },
            select: function (info) {
                const popover = document.getElementById('eventPopover');
                popover.style.display = 'block';
                popover.classList.remove('visually-hidden');
                try { popover.style.zIndex = '4000'; } catch (e) { console.error('An error occurred:', e); }
                let x = 0, y = 0;
                if (info.jsEvent) { x = info.jsEvent.clientX; y = info.jsEvent.clientY; }
                else { const rect = calendarEl.getBoundingClientRect(); x = rect.left + rect.width / 2; y = rect.top + rect.height / 2; }
                setTimeout(() => {
                    const popRect = popover.getBoundingClientRect();
                    let left = x; let top = y;
                    if (left + popRect.width > window.innerWidth) left = window.innerWidth - popRect.width - 10;
                    if (left < 10) left = 10;
                    if (top + popRect.height > window.innerHeight) top = window.innerHeight - popRect.height - 10;
                    if (top < 10) top = 10;
                    popover.style.position = 'fixed'; popover.style.left = left + 'px'; popover.style.top = top + 'px'; popover.style.zIndex = '1060';
                }, 10);
                document.getElementById('popoverEventTitle').value = '';
                try { const sel = document.getElementById('popoverDentist'); if (sel) { const ids = loadSelectedDentists(); if (ids && ids.length === 1) sel.value = String(ids[0]); else sel.value = ''; } } catch (e) { console.error('An error occurred:', e); }
                const startInput = document.getElementById('popoverEventStart');
                const endInput = document.getElementById('popoverEventEnd');
                const startDateInput = document.getElementById('popoverEventStartDate');
                const endDateInput = document.getElementById('popoverEventEndDate');
                if (info.allDay) {
                    startInput.classList.add('visually-hidden'); endInput.classList.add('visually-hidden');
                    startDateInput.classList.remove('visually-hidden'); endDateInput.classList.remove('visually-hidden');
                    try { const startLbl = document.querySelector('#eventPopoverForm label[for="popoverEventStart"], #eventPopoverForm label[for="popoverEventStartDate"]'); if (startLbl) startLbl.setAttribute('for', 'popoverEventStartDate'); const endLbl = document.querySelector('#eventPopoverForm label[for="popoverEventEnd"], #eventPopoverForm label[for="popoverEventEndDate"]'); if (endLbl) endLbl.setAttribute('for', 'popoverEventEndDate'); } catch (e) { console.error('An error occurred:', e); }
                    startDateInput.value = info.startStr;
                    if (info.endStr) { const endDate = new Date(info.endStr); endDate.setDate(endDate.getDate() - 1); endDateInput.value = endDate.toISOString().slice(0, 10); } else { endDateInput.value = ''; }
                    try { if (startInput._flatpickr) startInput._flatpickr.destroy(); if (endInput._flatpickr) endInput._flatpickr.destroy(); } catch (e) { console.error('An error occurred:', e); }
                    const fpDateOpts = { enableTime: false, allowInput: true, locale: (window.flatpickr?.l10ns?.pt) || 'pt', dateFormat: 'Y-m-d', altInput: true, altFormat: 'd/m/Y' };
                    if (window.flatpickr) { flatpickr(startDateInput, fpDateOpts); flatpickr(endDateInput, fpDateOpts); }
                } else {
                    startInput.classList.remove('visually-hidden'); endInput.classList.remove('visually-hidden');
                    startDateInput.classList.add('visually-hidden'); endDateInput.classList.add('visually-hidden');
                    try { const startLbl = document.querySelector('#eventPopoverForm label[for="popoverEventStart"], #eventPopoverForm label[for="popoverEventStartDate"]'); if (startLbl) startLbl.setAttribute('for', 'popoverEventStart'); const endLbl = document.querySelector('#eventPopoverForm label[for="popoverEventEnd"], #eventPopoverForm label[for="popoverEventEndDate"]'); if (endLbl) endLbl.setAttribute('for', 'popoverEventEnd'); } catch (e) { console.error('An error occurred:', e); }
                    try { if (info.start instanceof Date && !isNaN(info.start.getTime())) startInput.value = formatLocalYmdHm(info.start); else { const d = new Date(info.startStr); startInput.value = isNaN(d.getTime()) ? (info.startStr || '').slice(0, 16) : formatLocalYmdHm(d); } } catch (e) { console.error('An error occurred:', e); startInput.value = (info.startStr || '').slice(0, 16); }
                    (function () {
                        const dur = getDefaultEventDurationMin();
                        try {
                            const startISO = info.startStr; const startDate = new Date(startISO); const selectionEndISO = info.endStr || '';
                            let useDefault = false;
                            if (selectionEndISO) { const selEndDate = new Date(selectionEndISO); const diffMin = Math.max(0, Math.round((selEndDate - startDate) / 60000)); if (diffMin === 30 && dur !== 30) useDefault = true; else if (diffMin === 0) useDefault = true; }
                            else useDefault = true;
                            if (useDefault) { const endDate = new Date(startDate); endDate.setMinutes(endDate.getMinutes() + dur); endInput.value = formatLocalYmdHm(endDate); }
                            else { const sel = new Date(selectionEndISO); endInput.value = isNaN(sel.getTime()) ? selectionEndISO.slice(0, 16) : formatLocalYmdHm(sel); }
                        } catch (e) { console.error('An error occurred:', e); endInput.value = ''; }
                    })();
                    try { if (startInput._flatpickr) startInput._flatpickr.destroy(); if (endInput._flatpickr) endInput._flatpickr.destroy(); } catch (e) { console.error('An error occurred:', e); }
                    const fpOpts = { enableTime: true, time_24hr: true, allowInput: true, minuteIncrement: 5, locale: (window.flatpickr?.l10ns?.pt) || 'pt', dateFormat: 'Y-m-d\\TH:i', altInput: true, altFormat: 'd/m/Y H:i' };
                    if (window.flatpickr) { flatpickr(startInput, fpOpts); flatpickr(endInput, fpOpts); }
                }
                document.getElementById('popoverEventDesc').value = '';
                setTimeout(() => { document.getElementById('popoverEventTitle').focus(); setupAutocomplete(BASE); }, 50);
                function closePopover() { popover.style.display = 'none'; document.removeEventListener('mousedown', outsideClickListener); }
                function outsideClickListener(e) { if (!popover.contains(e.target)) closePopover(); }
                setTimeout(() => { document.addEventListener('mousedown', outsideClickListener); }, 10);
                document.getElementById('closePopoverBtn').onclick = closePopover;
                const form = document.getElementById('eventPopoverForm');
                form.onsubmit = function (e) {
                    e.preventDefault();
                    const title = document.getElementById('popoverEventTitle').value;
                    let start, end;
                    if (info.allDay) {
                        start = document.getElementById('popoverEventStartDate').value;
                        end = document.getElementById('popoverEventEndDate').value;
                    } else {
                        start = document.getElementById('popoverEventStart').value;
                        end = document.getElementById('popoverEventEnd').value;
                        if (!end && start) { const dt = new Date(start); dt.setHours(dt.getHours() + 1); end = dt.toISOString().slice(0, 16); }
                    }
                    const selDent = (() => { const el = document.getElementById('popoverDentist'); if (!el) return null; const v = (el.value || '').trim(); return v && /^\d+$/.test(v) ? parseInt(v, 10) : null; })();
                    if (title && start) {
                        let endToSend = end;
                        if (info.allDay) {
                            try { const base = new Date(start + 'T00:00:00'); let endDate = end ? new Date(end + 'T00:00:00') : new Date(base); endDate.setDate(endDate.getDate() + 1); endToSend = endDate.toISOString().slice(0, 10); }
                            catch (e) { console.error('An error occurred:', e); try { const d = new Date(start + 'T00:00:00'); d.setDate(d.getDate() + 1); endToSend = d.toISOString().slice(0, 10); } catch (e2) { console.error('An error occurred:', e2); endToSend = end || start; } }
                        }
                        fetch(BASE + '/add_event', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title, start, end: (function () { if (info.allDay) return endToSend; if (end) return end; try { const dur = getDefaultEventDurationMin(); const dt = new Date(start); dt.setMinutes(dt.getMinutes() + dur); return formatLocalYmdHm(dt); } catch (e) { console.error('An error occurred:', e); return end; } })(), notes: document.getElementById('popoverEventDesc').value || '', profissional_id: selDent }) })
                            .then(async (response) => {
                                let data; try { data = await response.json(); } catch (e) { console.error('An error occurred:', e); data = {}; }
                                if (response.ok && data.status === 'success' && data.event) {
                                    try { calendar.addEvent(data.event); addEventToCache(data.event); try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { console.error('An error occurred:', e); } try { showToast('Evento criado.', 'success', 1600); } catch (e) { console.error('An error occurred:', e); } }
                                    catch (e) { console.error('An error occurred:', e); try { calendar.refetchEvents(); } catch (_) { console.error('An error occurred:', _); } }
                                    closePopover();
                                } else { const msg = (data && data.message) ? data.message : 'Erro ao adicionar evento!'; alert(msg); }
                            })
                            .catch(() => alert('Erro ao adicionar evento!'));
                    }
                };
                calendar.unselect();
            },
            eventClick: function (info) {
                const menuEl = document.getElementById('eventContextMenu'); if (menuEl) menuEl.style.display = 'none';
                const popover = document.getElementById('eventDetailPopover'); if (!popover) return;
                try { if (popover && popover.parentElement !== document.body) document.body.appendChild(popover); } catch (e) { console.error('An error occurred:', e); }
                const fmtDate = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
                const fmtTime = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit', hour12: false });
                function buildTimeText(ev) {
                    const start = ev.start; const end = ev.end;
                    if (ev.allDay) {
                        if (!end) return `${fmtDate.format(start)} (dia inteiro)`;
                        const last = new Date(end.getTime() - 86400000);
                        const same = start.getFullYear() === last.getFullYear() && start.getMonth() === last.getMonth() && start.getDate() === last.getDate();
                        return same ? `${fmtDate.format(start)} (dia inteiro)` : `${fmtDate.format(start)} – ${fmtDate.format(last)} (dia inteiro)`;
                    } else {
                        if (end) { const sameDay = start.toDateString() === end.toDateString(); return sameDay ? `${fmtDate.format(start)} ${fmtTime.format(start)} – ${fmtTime.format(end)}` : `${fmtDate.format(start)} ${fmtTime.format(start)} – ${fmtDate.format(end)} ${fmtTime.format(end)}`; }
                        else { return `${fmtDate.format(start)} ${fmtTime.format(start)}`; }
                    }
                }
                document.getElementById('detailEventTitle').textContent = info.event.title;
                document.getElementById('detailEventTime').textContent = buildTimeText(info.event);
                const notesArea = document.getElementById('detailEventNotes');
                const saveNotesBtn = document.getElementById('saveDetailNotesBtn');
                if (notesArea) notesArea.value = info.event.extendedProps?.notes || '';
                if (saveNotesBtn) {
                    saveNotesBtn.onclick = function () {
                        const newNotes = notesArea ? notesArea.value : '';
                        fetch(BASE + '/update_event_notes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: info.event.id, notes: newNotes }) })
                            .then(r => r.json())
                            .then(data => { if (data.status === 'success') { try { info.event.setExtendedProp('notes', newNotes); } catch (e) { console.error('An error occurred:', e); } updateEventInCacheById(info.event.id, { notes: newNotes }); try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { console.error('An error occurred:', e); } } else { alert('Erro ao salvar descrição.'); } })
                            .catch(() => alert('Erro ao salvar descrição.'));
                    };
                }
                try {
                    const sel = document.getElementById('detailEventDentist');
                    const btn = document.getElementById('saveDetailDentistBtn');
                    if (sel) {
                        const ensureDentistOptions = () => {
                            return fetchDentistsOnce().then(list => {
                                if (!Array.isArray(list)) return [];
                                if (!sel.querySelector('option[value=""]')) {
                                    const optEmpty = document.createElement('option');
                                    optEmpty.value = '';
                                    optEmpty.textContent = 'Sem profissional';
                                    sel.insertBefore(optEmpty, sel.firstChild);
                                }
                                const hasReal = Array.from(sel.options).some(o => o.value && o.value !== '');
                                if (!hasReal) {
                                    list.forEach(d => { const o = document.createElement('option'); o.value = String(d.id); o.textContent = d.nome || d.name || `#${d.id}`; sel.appendChild(o); });
                                }
                                return list;
                            });
                        };
                        ensureDentistOptions().then(() => {
                            const currentDentistId = info.event.extendedProps?.profissional_id ?? null;
                            sel.value = (currentDentistId != null ? String(currentDentistId) : '');
                        }).catch(e => console.error('An error occurred:', e));
                        if (btn) {
                            btn.onclick = function () {
                                const v = sel.value && /^\d+$/.test(sel.value) ? parseInt(sel.value, 10) : null;
                                fetch(BASE + '/update_event_dentist', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: info.event.id, profissional_id: v }) })
                                    .then(r => r.json())
                                    .then(data => {
                                        if (data && data.status === 'success') {
                                            try { info.event.setExtendedProp('profissional_id', v); } catch (e) { console.error('An error occurred:', e); }
                                            updateEventInCacheById(info.event.id, { profissional_id: v });
                                            try { showToast('Profissional atualizado.', 'success', 1400); } catch (e) { console.error('An error occurred:', e); }
                                        } else { alert('Erro ao atualizar profissional.'); }
                                    })
                                    .catch(() => alert('Erro ao atualizar profissional.'));
                            };
                        }
                    }
                } catch (e) { console.error('An error occurred:', e); }
                try {
                    popover.style.display = 'block';
                    popover.classList.remove('visually-hidden');
                    setTimeout(() => {
                        const rect = popover.getBoundingClientRect();
                        let left = (info.jsEvent?.clientX ?? (window.innerWidth / 2));
                        let top = (info.jsEvent?.clientY ?? (window.innerHeight / 2));
                        if (left + rect.width > window.innerWidth) left = window.innerWidth - rect.width - 10;
                        if (top + rect.height > window.innerHeight) top = window.innerHeight - rect.height - 10;
                        if (left < 10) left = 10; if (top < 10) top = 10;
                        popover.style.position = 'fixed';
                        popover.style.left = left + 'px';
                        popover.style.top = top + 'px';
                        popover.style.zIndex = '1060';
                    }, 10);
                } catch (e) { console.error('An error occurred:', e); }
            },
            eventDrop: function (info) {
                const ev = info.event;
                const payload = { id: ev.id, start: ev.start ? formatLocalYmdHm(ev.start) : null, end: ev.end ? formatLocalYmdHm(ev.end) : null, all_day: !!ev.allDay };
                fetch(BASE + '/update_event_time', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
                    .then(r => r.json())
                    .then(data => { if (!(data && data.status === 'success')) { info.revert(); } else { updateEventInCacheById(ev.id, { start: payload.start, end: payload.end, allDay: payload.all_day }); } })
                    .catch(() => { info.revert(); });
            },
            eventResize: function (info) {
                const ev = info.event;
                const payload = { id: ev.id, start: ev.start ? formatLocalYmdHm(ev.start) : null, end: ev.end ? formatLocalYmdHm(ev.end) : null, all_day: !!ev.allDay };
                fetch(BASE + '/update_event_time', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
                    .then(r => r.json())
                    .then(data => { if (!(data && data.status === 'success')) { info.revert(); } else { updateEventInCacheById(ev.id, { start: payload.start, end: payload.end, allDay: payload.all_day }); } })
                    .catch(() => { info.revert(); });
            },
            datesSet: function () { updateHolidaysForCurrentView(calendar); try { if (window.__miniCalendar) window.__miniCalendar.gotoDate(calendar.getDate()); } catch (e) { console.error('An error occurred:', e); } },
        });

        calendar.render();
        updateHolidaysForCurrentView(calendar);
        updateEmptyFilterNoticeDeb();

        const miniEl = document.getElementById('miniCalendar');
        if (miniEl && window.FullCalendar) {
            try {
                const mini = new FullCalendar.Calendar(miniEl, {
                    initialView: 'dayGridMonth',
                    headerToolbar: { left: 'prev,next', center: 'title', right: '' },
                    locale: 'pt-br',
                    navLinks: true,
                    selectable: false,
                    events: (info, success) => { success([]); },
                    dateClick: (arg) => { try { calendar.gotoDate(arg.date); } catch (e) { console.error('An error occurred:', e); } },
                });
                mini.render();
                window.__miniCalendar = mini;
                window.__rebuildMiniIndicators = function () { /* placeholder */ };
            } catch (e) { console.error('An error occurred:', e); }
        }

        document.addEventListener('click', (ev) => {
            const t = ev.target;
            if (!(t instanceof HTMLElement)) return;
            if (t.matches('#settingsMenu [data-theme]')) { ev.preventDefault(); const theme = t.getAttribute('data-theme'); applyTheme(theme); }
            if (t.matches('#settingsMenu [data-weekends]')) { ev.preventDefault(); const v = t.getAttribute('data-weekends') === 'true'; setWeekendsSetting(v); calendar.setOption('weekends', v); }
            if (t.matches('#settingsMenu [data-duration]')) { ev.preventDefault(); const mins = parseInt(t.getAttribute('data-duration') || '60', 10); setDefaultEventDurationMin(mins); }
        });

        (function wireDentistFilters() {
            // Support both modern IDs (dentistsFilterList/includeUnassignedToggle)
            // and legacy sidebar IDs (dentistsContainer/dent_all)
            const modernListEl = document.getElementById('dentistsFilterList');
            const legacyContainer = document.getElementById('dentistsContainer');
            const modernToggle = document.getElementById('includeUnassignedToggle');
            const legacyToggle = document.getElementById('dent_all');
            const applyToggleChecked = (el) => { try { el.checked = !!loadIncludeUnassigned(); } catch (e) { console.error('An error occurred:', e); } };
            if (modernToggle) applyToggleChecked(modernToggle);
            if (legacyToggle) applyToggleChecked(legacyToggle);

            const onToggleChange = (checked) => {
                try { saveIncludeUnassigned(!!checked); } catch (e) { console.error('An error occurred:', e); }
                try { calendar.refetchEvents(); } catch (e) { console.error('An error occurred:', e); }
                try { updateEmptyFilterNoticeDeb(); } catch (e) { console.error('An error occurred:', e); }
            };
            if (modernToggle) modernToggle.addEventListener('change', () => onToggleChange(!!modernToggle.checked));
            if (legacyToggle) legacyToggle.addEventListener('change', () => onToggleChange(!!legacyToggle.checked));

            // If legacy container exists, render checkbox list into it
            if (legacyContainer) {
                fetchDentistsOnce().then(list => {
                    if (!Array.isArray(list)) return;
                    const selected = new Set((loadSelectedDentists() || []).map(Number));
                    const ul = document.createElement('ul');
                    ul.className = 'dentist-list';
                    list.forEach(d => {
                        const li = document.createElement('li');
                        li.className = 'dentist-item d-flex align-items-center gap-2 py-1 border-bottom';
                        const color = colorForDentist(d);
                        li.innerHTML = `
							<input type="checkbox" class="form-check-input" id="dent_${d.id}" ${selected.has(Number(d.id)) ? 'checked' : ''} />
							<span class="dentist-color" style="background:${color}"></span>
							<label class="form-check-label" for="dent_${d.id}">${d.nome || d.name || ('Dentista ' + d.id)}</label>
						`;
                        ul.appendChild(li);
                    });
                    if (ul.lastElementChild) ul.lastElementChild.classList.remove('border-bottom');
                    legacyContainer.innerHTML = '';
                    legacyContainer.appendChild(ul);
                    legacyContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                        cb.addEventListener('change', () => {
                            const ids = Array.from(legacyContainer.querySelectorAll('input[type="checkbox"]'))
                                .filter(x => x.checked)
                                .map(x => parseInt(x.id.replace('dent_', ''), 10))
                                .filter(n => Number.isFinite(n));
                            saveSelectedDentists(ids);
                            try { calendar.refetchEvents(); } catch (e) { console.error('An error occurred:', e); }
                            try { updateEmptyFilterNoticeDeb(); } catch (e) { console.error('An error occurred:', e); }
                            // Auto-select in creation popover if exactly one dentist selected
                            try { const sel = document.getElementById('popoverDentist'); if (sel) { if (ids.length === 1) sel.value = String(ids[0]); else if (ids.length === 0) sel.value = ''; } } catch (e) { console.error('An error occurred:', e); }
                        });
                    });
                });
                return; // done with legacy path
            }

            // Otherwise, use modern list element if available
            if (modernListEl) {
                fetchDentistsOnce().then(list => {
                    if (!Array.isArray(list)) return;
                    modernListEl.innerHTML = '';
                    const saved = new Set((loadSelectedDentists() || []).map(x => String(x)));
                    list.forEach(d => {
                        const idStr = String(d.id);
                        const li = document.createElement('li');
                        li.className = 'list-group-item py-1';
                        li.innerHTML = `<label class=\"form-check form-check-sm\"><input class=\"form-check-input dentist-filter\" type=\"checkbox\" value=\"${idStr}\" ${saved.has(idStr) ? 'checked' : ''}> <span class=\"form-check-label\">${d.nome || d.name || ('#' + idStr)}</span></label>`;
                        modernListEl.appendChild(li);
                    });
                    modernListEl.addEventListener('change', (e2) => {
                        if (!(e2.target instanceof HTMLInputElement) || !e2.target.classList.contains('dentist-filter')) return;
                        const checks = Array.from(modernListEl.querySelectorAll('input.dentist-filter:checked')).map(i => parseInt(i.value, 10)).filter(n => !isNaN(n));
                        saveSelectedDentists(checks);
                        calendar.refetchEvents();
                        updateEmptyFilterNoticeDeb();
                    });
                    if (modernToggle) modernToggle.addEventListener('change', () => { saveIncludeUnassigned(!!modernToggle.checked); calendar.refetchEvents(); updateEmptyFilterNoticeDeb(); });
                });
            }
        })();

        wireSearchMenu(calendar, BASE);
    });
}

function wireSearchMenu(calendar, BASE) {
    try {
        const wrap = document.getElementById('searchMenu') || document.getElementById('searchmenu-container');
        if (!wrap) return;
        const input = document.getElementById('searchQueryInput');
        const applyBtn = document.getElementById('applySearchBtn');
        const clearBtn = document.getElementById('clearSearchBtn');
        if (input) { try { input.value = loadSearchQuery(); } catch (e) { console.error('An error occurred:', e); } }
        const apply = () => { const q = input ? (input.value || '').trim() : ''; saveSearchQuery(q); try { if (typeof applyClientSearchFilter === 'function') applyClientSearchFilter(q); } catch (e) { console.error('An error occurred:', e); } calendar.refetchEvents(); };
        if (applyBtn) applyBtn.onclick = (e) => { e.preventDefault(); apply(); };
        if (clearBtn) clearBtn.onclick = (e) => { e.preventDefault(); if (input) input.value = ''; saveSearchQuery(''); try { if (typeof applyClientSearchFilter === 'function') applyClientSearchFilter(''); } catch (e2) { console.error('An error occurred:', e2); } calendar.refetchEvents(); };
        if (input) input.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); apply(); } });
    } catch (e) { console.error('An error occurred:', e); }
}

function setupAutocomplete(BASE) {
    try {
        const input = document.getElementById('popoverEventTitle');
        if (!input) return;
        // Stub for future enhancements
    } catch (e) { console.error('An error occurred:', e); }
}
