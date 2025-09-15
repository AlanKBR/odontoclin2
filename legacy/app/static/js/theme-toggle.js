// Dark mode toggle logic

document.addEventListener('DOMContentLoaded', () => {
    const themeToggleButton = document.getElementById('theme-toggle-button');
    const darkModeToggle = document.getElementById('darkModeToggle');
    const currentTheme = localStorage.getItem('theme') ? localStorage.getItem('theme') : null;

    // Apply saved theme on page load
    if (currentTheme) {
        document.body.classList.add(currentTheme);

        // Update UI elements based on current theme
        if (currentTheme === 'dark-mode') {
            // Update theme toggle button in sidebar
            if(themeToggleButton) {
                const icon = themeToggleButton.querySelector('.menu-icon i');
                const text = themeToggleButton.querySelector('.menu-text');
                if(icon) icon.className = 'bi bi-sun';
                if(text) text.textContent = 'Modo Claro';
            }

            // Update settings page checkbox if present
            if(darkModeToggle) darkModeToggle.checked = true;
        } else {
            // Update theme toggle button in sidebar
            if(themeToggleButton) {
                const icon = themeToggleButton.querySelector('.menu-icon i');
                const text = themeToggleButton.querySelector('.menu-text');
                if(icon) icon.className = 'bi bi-moon';
                if(text) text.textContent = 'Modo Escuro';
            }

            // Update settings page checkbox if present
            if(darkModeToggle) darkModeToggle.checked = false;
        }
    }

    // Sidebar toggle button
    if (themeToggleButton) {
        themeToggleButton.addEventListener('click', () => {
            toggleTheme();
        });
    }

    // Settings page toggle checkbox
    if (darkModeToggle) {
        darkModeToggle.addEventListener('change', function() {
            if (this.checked) {
                setDarkTheme();
            } else {
                setLightTheme();
            }
        });
    }
});

// Function to toggle between themes
function toggleTheme() {
    if (document.body.classList.contains('dark-mode')) {
        setLightTheme();
    } else {
        setDarkTheme();
    }
}

// Function to set dark theme
function setDarkTheme() {
    document.body.classList.add('dark-mode');
    localStorage.setItem('theme', 'dark-mode');

    // Update UI elements
    const themeToggleButton = document.getElementById('theme-toggle-button');
    const darkModeToggle = document.getElementById('darkModeToggle');

    if(themeToggleButton) {
        const icon = themeToggleButton.querySelector('.menu-icon i');
        const text = themeToggleButton.querySelector('.menu-text');
        if(icon) icon.className = 'bi bi-sun';
        if(text) text.textContent = 'Modo Claro';
    }
    if(darkModeToggle) darkModeToggle.checked = true;
}

// Function to set light theme
function setLightTheme() {
    document.body.classList.remove('dark-mode');
    localStorage.setItem('theme', 'light-mode');

    // Update UI elements
    const themeToggleButton = document.getElementById('theme-toggle-button');
    const darkModeToggle = document.getElementById('darkModeToggle');

    if(themeToggleButton) {
        const icon = themeToggleButton.querySelector('.menu-icon i');
        const text = themeToggleButton.querySelector('.menu-text');
        if(icon) icon.className = 'bi bi-moon';
        if(text) text.textContent = 'Modo Escuro';
    }
    if(darkModeToggle) darkModeToggle.checked = false;
}
