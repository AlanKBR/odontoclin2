/* eslint-env browser */
// utils.js: generic helpers and UI-related logic not tied to Calendar instantiation

// Small base helpers
export function debounce(fn, wait = 200) {
    let t;
    return function (...args) {
        clearTimeout(t);
        t = setTimeout(() => fn.apply(this, args), wait);
    };
}
export function rafThrottle(fn) {
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
export function showToast(message, variant = 'success', delay = 2500) {
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
            const t = new window.bootstrap.Toast(toastEl, { delay, autohide: true });
            t.show();
            toastEl.addEventListener('hidden.bs.toast', () => { try { toastEl.remove(); } catch (e) { console.error('An error occurred:', e); } });
        } else {
            toastEl.style.display = 'block';
            setTimeout(() => { try { toastEl.remove(); } catch (e) { console.error('An error occurred:', e); } }, delay);
        }
    } catch (e) { console.error('An error occurred:', e); }
}

// Date helpers
export function formatLocalYmdHm(d) {
    const pad = (n) => String(n).padStart(2, '0');
    const y = d.getFullYear();
    const m = pad(d.getMonth() + 1);
    const day = pad(d.getDate());
    const h = pad(d.getHours());
    const min = pad(d.getMinutes());
    return `${y}-${m}-${day}T${h}:${min}`;
}
export function toLocalISO(date) {
    const pad = (n) => String(n).padStart(2, '0');
    return [date.getFullYear(), pad(date.getMonth() + 1), pad(date.getDate())].join('-');
}
export function ymdFromDate(d) {
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// UI: compute popup position near last mouse position or anchor
let __lastMousePos = { x: null, y: null };
try {
    document.addEventListener('mousedown', (e) => { __lastMousePos = { x: e.clientX, y: e.clientY }; }, true);
} catch (e) { console.error('An error occurred:', e); }

export function computePopupPosition(w, h, anchorEl) {
    let x = (typeof __lastMousePos?.x === 'number') ? __lastMousePos.x : null;
    let y = (typeof __lastMousePos?.y === 'number') ? __lastMousePos.y : null;
    if (x == null || y == null) {
        try {
            const rect = anchorEl?.getBoundingClientRect();
            if (rect) { x = rect.left; y = rect.bottom + 6; }
        } catch (e) { console.error('An error occurred:', e); }
    }
    if (x == null || y == null) { x = Math.round(window.innerWidth / 2); y = Math.round(window.innerHeight / 2); }
    let left = x; let top = y;
    try {
        if (left + w > window.innerWidth) left = window.innerWidth - w - 10;
        if (left < 10) left = 10;
        if (top + h > window.innerHeight) top = window.innerHeight - h - 10;
        if (top < 10) top = 10;
    } catch (e) { console.error('An error occurred:', e); }
    return { left, top };
}

// Extract first brazilian phone number found in free text
export function extractPhoneFromText(text) {
    if (!text) return null;
    try {
        const re = /(?:\+?55[\s\-.]?)?(?:\(?\d{2}\)?[\s\-.]?)?(?:9\d{4}|\d{4})[\s\-.]?\d{4}\b/;
        const m = String(text).match(re);
        return m ? m[0].trim() : null;
    } catch (e) { console.error('An error occurred:', e); return null; }
}

// Settings / Search menus toggling, wiring done in calendar.js but helpers are here
export function toggleMenu(el, anchorEl, onOpen, onClose) {
    if (!el) return;
    const isVisible = el.style.display === 'block';
    const outsideListener = (e) => {
        if (!el.contains(e.target)) {
            try { el.style.display = 'none'; el.classList.add('visually-hidden'); } catch (err) { console.error('An error occurred:', err); }
            document.removeEventListener('mousedown', outsideListener);
            if (typeof onClose === 'function') onClose();
        }
    };
    if (isVisible) {
        el.style.display = 'none';
        el.classList.add('visually-hidden');
        document.removeEventListener('mousedown', outsideListener);
        if (typeof onClose === 'function') onClose();
        return;
    }
    el.style.display = 'block';
    el.classList.remove('visually-hidden');
    setTimeout(() => {
        try {
            const r = el.getBoundingClientRect();
            const pos = computePopupPosition(r.width, r.height, anchorEl);
            el.style.position = 'fixed';
            el.style.left = pos.left + 'px';
            el.style.top = pos.top + 'px';
            el.style.zIndex = '10000';
        } catch (e) { console.error('An error occurred:', e); }
    }, 10);
    if (typeof onOpen === 'function') onOpen();
    setTimeout(() => document.addEventListener('mousedown', outsideListener), 10);
}

// Dentist color utilities used by calendar rendering
export function colorForDentist(d) {
    if (d && d.color) return d.color;
    const palette = ['#2563eb', '#16a34a', '#dc2626', '#9333ea', '#ea580c', '#0891b2', '#4f46e5', '#059669'];
    const id = d && d.id ? Number(d.id) : 0;
    return palette[Math.abs(id) % palette.length];
}
export function repaintDentistBarsForEvent(eventId, pid, dentistsMap) {
    try {
        const els = document.querySelectorAll(`[data-eid="${eventId}"]`);
        let col = null;
        if (pid != null && dentistsMap && dentistsMap[pid]) {
            const d = dentistsMap[pid];
            col = colorForDentist(d);
        }
        els.forEach(el => {
            if (col) {
                el.classList.add('dentist-rightbar');
                el.classList.add('dentist-leftbar');
                el.style.borderRight = `6px solid ${col}`;
                el.style.borderLeft = `2px solid ${col}`;
                try { el.style.boxShadow = `inset -6px 0 0 0 ${col}`; } catch (e) { console.error('An error occurred:', e); }
            } else {
                el.style.borderRight = '';
                el.style.borderLeft = '';
                try { el.style.boxShadow = ''; } catch (e) { console.error('An error occurred:', e); }
                el.classList.remove('dentist-rightbar');
                el.classList.remove('dentist-leftbar');
            }
        });
    } catch (e) { console.error('An error occurred:', e); }
}

