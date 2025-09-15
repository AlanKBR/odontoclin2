/* eslint-env browser */
// storage.js: All state persistence and data caching (localStorage + in-memory)

// Base URL for API calls; set by calendar.js
let BASE = '';
export function setBase(base) { BASE = base || ''; }

// ---- Theme persistence ----
const THEME_KEY = 'calendarTheme';
export function getTheme() {
    try {
        return localStorage.getItem(THEME_KEY) || 'default';
    } catch (e) {
        console.error('An error occurred:', e);
        return 'default';
    }
}
export function setTheme(theme) {
    try {
        localStorage.setItem(THEME_KEY, theme || 'default');
    } catch (e) {
        console.error('An error occurred:', e);
    }
}

// ---- Weekends setting ----
const WEEKENDS_KEY = 'timeGridWeek_weekends';
export function getWeekendsSetting() {
    try {
        const v = localStorage.getItem(WEEKENDS_KEY);
        return v === null ? true : v === 'true';
    } catch (e) {
        console.error('An error occurred:', e);
        return true;
    }
}
export function setWeekendsSetting(val) {
    try {
        localStorage.setItem(WEEKENDS_KEY, String(!!val));
    } catch (e) {
        console.error('An error occurred:', e);
    }
}

// ---- Dentist selection persistence ----
const DENTISTS_SELECTED_KEY = 'selectedDentists';
const INCLUDE_UNASSIGNED_KEY = 'includeUnassigned';
export function saveSelectedDentists(ids) {
    try {
        localStorage.setItem(DENTISTS_SELECTED_KEY, JSON.stringify(ids || []));
    } catch (e) {
        console.error('An error occurred:', e);
    }
}
export function loadSelectedDentists() {
    try {
        const v = localStorage.getItem(DENTISTS_SELECTED_KEY);
        if (!v) return [];
        const arr = JSON.parse(v);
        return Array.isArray(arr) ? arr : [];
    } catch (e) {
        console.error('An error occurred:', e);
        return [];
    }
}
export function saveIncludeUnassigned(val) {
    try {
        localStorage.setItem(INCLUDE_UNASSIGNED_KEY, String(!!val));
    } catch (e) {
        console.error('An error occurred:', e);
    }
}
export function loadIncludeUnassigned() {
    try {
        return localStorage.getItem(INCLUDE_UNASSIGNED_KEY) === 'true';
    } catch (e) {
        console.error('An error occurred:', e);
        return false;
    }
}

// ---- Default new-event duration (minutes) ----
const DEFAULT_DURATION_KEY = 'defaultEventDurationMin';
export function getDefaultEventDurationMin() {
    try {
        const saved = parseInt(localStorage.getItem(DEFAULT_DURATION_KEY) || '60', 10);
        if (!isFinite(saved) || saved <= 0 || saved === 15) return 60;
        return saved;
    } catch (e) {
        console.error('An error occurred:', e);
        return 60;
    }
}
export function setDefaultEventDurationMin(mins) {
    try {
        const v = (!isFinite(mins) || mins <= 0 || mins === 15) ? 60 : mins;
        localStorage.setItem(DEFAULT_DURATION_KEY, String(v));
    } catch (e) {
        console.error('An error occurred:', e);
    }
}

// ---- Search query persistence ----
const SEARCH_KEY = 'calendarSearchQuery';
export function saveSearchQuery(q) {
    try {
        localStorage.setItem(SEARCH_KEY, q || '');
    } catch (e) {
        console.error('An error occurred:', e);
    }
}
export function loadSearchQuery() {
    try {
        return localStorage.getItem(SEARCH_KEY) || '';
    } catch (e) {
        console.error('An error occurred:', e);
        return '';
    }
}

// ---- Events in-memory cache (shared by main + mini) ----
export const sharedEventsCache = {
    key: null,     // string key for filters: dentists|includeUn|q
    start: null,   // Date coverage start (inclusive)
    end: null,     // Date coverage end (exclusive)
    events: []     // array of event objects as returned by server
};
export const pendingEventsFetches = new Map(); // de-duplication: key -> Promise

export function buildCacheKey() {
    const ids = (loadSelectedDentists() || []).slice();
    const includeUn = loadIncludeUnassigned() ? '1' : '';
    const q = loadSearchQuery() || '';
    ids.sort((a, b) => a - b);
    return `${ids.join(',')}|${includeUn}|${q}`;
}

export function storeEventsToCache(list, covStart, covEnd, key) {
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

export function cacheCoversRange(rangeStart, rangeEnd, key) {
    if (sharedEventsCache.key !== key) return false;
    if (!sharedEventsCache.start || !sharedEventsCache.end) return false;
    return sharedEventsCache.start <= rangeStart && sharedEventsCache.end >= rangeEnd;
}

export function eventsFromCache(rangeStart, rangeEnd, key) {
    if (sharedEventsCache.key !== key) return [];
    const rs = rangeStart.getTime();
    const re = rangeEnd.getTime();
    return (sharedEventsCache.events || []).filter(ev => {
        try {
            const s = ev.start ? new Date(String(ev.start).replace(' ', 'T')) : null;
            const e = ev.end ? new Date(String(ev.end).replace(' ', 'T')) : null;
            if (s && e) return e.getTime() >= rs && s.getTime() < re;
            if (s && !e) return s.getTime() < re; // open-ended
            return false;
        } catch (e) {
            console.error('An error occurred:', e);
            return false;
        }
    });
}

export function updateEventInCacheById(id, changes) {
    try {
        const list = sharedEventsCache.events || [];
        const idx = list.findIndex(e => String(e.id) === String(id));
        if (idx === -1) return null;
        const old = list[idx] || {};
        const updated = { ...old, ...changes };
        if (old.extendedProps || changes?.extendedProps) {
            updated.extendedProps = { ...(old.extendedProps || {}), ...(changes.extendedProps || {}) };
        }
        list[idx] = updated;
        sharedEventsCache.events = list;
        return updated;
    } catch (e) {
        console.error('An error occurred:', e);
        return null;
    }
}
export function removeEventFromCacheById(id) {
    try {
        if (!sharedEventsCache.events) return;
        sharedEventsCache.events = sharedEventsCache.events.filter(e => String(e.id) !== String(id));
    } catch (e) {
        console.error('An error occurred:', e);
    }
}
export function addEventToCache(ev) {
    try {
        if (!sharedEventsCache.events) sharedEventsCache.events = [];
        const id = ev && ev.id != null ? String(ev.id) : null;
        if (id) {
            const exists = sharedEventsCache.events.some(e => String(e.id) === id);
            if (exists) return;
        }
        sharedEventsCache.events.push(ev);
    } catch (e) {
        console.error('An error occurred:', e);
    }
}

// ---- Dentists cache (memory + localStorage TTL) ----
export const dentistsCache = { list: [], map: {} };
const DENTISTS_CACHE_KEY = 'dentistsCacheV1';
const DENTISTS_CACHE_TTL_MS = 5 * 60 * 1000;
let dentistsPending = null; // in-flight Promise

function loadDentistsFromStorageRaw() {
    try {
        const raw = localStorage.getItem(DENTISTS_CACHE_KEY);
        if (!raw) return null;
        const obj = JSON.parse(raw);
        if (!obj || !Array.isArray(obj.list) || !obj.at) return null;
        if ((Date.now() - obj.at) > DENTISTS_CACHE_TTL_MS) return null;
        return obj.list;
    } catch (e) {
        console.error('An error occurred:', e);
        return null;
    }
}
function saveDentistsToStorageRaw(list) {
    try {
        localStorage.setItem(DENTISTS_CACHE_KEY, JSON.stringify({ list, at: Date.now() }));
    } catch (e) {
        console.error('An error occurred:', e);
    }
}
export function fetchDentistsOnce(force = false) {
    if (!force && dentistsCache.list && dentistsCache.list.length) {
        return Promise.resolve(dentistsCache.list);
    }
    if (!force) {
        const fromStorage = loadDentistsFromStorageRaw();
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
        .then(r => (r.status === 304 ? (dentistsCache.list || []) : r.json()))
        .then(list => {
            const norm = Array.isArray(list) ? list.map(d => ({ id: Number(d.id), nome: d.nome || String(d.id), color: d.color || null })) : [];
            dentistsCache.list = norm;
            dentistsCache.map = Object.fromEntries(norm.map(d => [d.id, d]));
            try { saveDentistsToStorageRaw(norm); } catch (e) { console.error('An error occurred:', e); }
            // Default selection to all dentists on first load
            try {
                const saved = loadSelectedDentists();
                if (!saved || saved.length === 0) saveSelectedDentists(norm.map(d => d.id));
            } catch (e) { console.error('An error occurred:', e); }
            return norm;
        })
        .finally(() => { dentistsPending = null; });
    return dentistsPending;
}

export function clearDentistsCache() {
    try { localStorage.removeItem(DENTISTS_CACHE_KEY); } catch (e) { console.error('An error occurred:', e); }
    dentistsCache.list = [];
    dentistsCache.map = {};
}

// ---- Holidays cache (by year, memory only) ----
export const holidaysYearCache = {}; // { [year]: { dates:Set, meta:{[date]:meta} } }
export const holidaysYearPending = {}; // { [year]: Promise }

export function ensureYearCached(year) {
    if (holidaysYearCache[year]) return Promise.resolve();
    if (holidaysYearPending[year]) return holidaysYearPending[year];
    const p = fetch(`${BASE}/holidays/year?year=${year}`)
        .then(r => r.json())
        .then(list => {
            const dates = new Set(list.map(h => h.date));
            const meta = {};
            list.forEach(h => { meta[h.date] = { name: h.name, type: h.type, level: h.level }; });
            holidaysYearCache[year] = { dates, meta };
        })
        .catch((e) => { console.error('An error occurred:', e); })
        .finally(() => { delete holidaysYearPending[year]; });
    holidaysYearPending[year] = p;
    return p;
}

export function ensureRangeCached(startDate, endDateInclusive) {
    const ys = [];
    const y1 = startDate.getFullYear();
    const y2 = endDateInclusive.getFullYear();
    for (let y = y1; y <= y2; y++) ys.push(y);
    return Promise.all(ys.map(y => ensureYearCached(y)));
}

export function buildVisibleHolidaysFromCache(startDate, endDateInclusive) {
    const resDates = new Set();
    const resMeta = {};
    let d = new Date(startDate);
    while (d <= endDateInclusive) {
        const y = d.getFullYear();
        const yc = holidaysYearCache[y];
        const pad = (n) => String(n).padStart(2, '0');
        const key = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
        if (yc && yc.dates.has(key)) {
            resDates.add(key);
            if (yc.meta[key]) resMeta[key] = yc.meta[key];
        }
        d.setDate(d.getDate() + 1);
    }
    return { dates: resDates, meta: resMeta };
}

export function clearHolidaysCache() {
    Object.keys(holidaysYearCache).forEach(y => delete holidaysYearCache[y]);
    Object.keys(holidaysYearPending).forEach(y => delete holidaysYearPending[y]);
}

