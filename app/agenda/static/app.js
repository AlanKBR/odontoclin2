/* eslint-env browser */
// Minimal ESM entrypoint for Agenda calendar
import { initCalendarApp } from './calendar.js';

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCalendarApp);
} else {
    initCalendarApp();
}
