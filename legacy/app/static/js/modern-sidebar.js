/**
 * Modern Responsive Sidebar with Dropdown Menu
 * Compatible with OdontoClinic System
 */

class ModernSidebar {
    constructor() {
        this.sidebar = document.querySelector('.modern-sidebar');
        this.toggleBtn = document.querySelector('.sidebar-toggle');
        this.mobileToggleBtn = document.querySelector('.mobile-menu-toggle');
        this.overlay = document.querySelector('.mobile-overlay');
        this.dropdownToggles = document.querySelectorAll('.menu-dropdown > .menu-link');
        this.isCollapsed = this.getStoredState();
        this.isMobile = window.innerWidth <= 768;

        this.init();
    }

    init() {
        this.bindEvents();
        this.setInitialState();
        this.handleResize();
        this.initializeDropdowns();
        this.setActiveMenuItem();
    }

    bindEvents() {
        // Toggle sidebar
        if (this.toggleBtn) {
            this.toggleBtn.addEventListener('click', () => this.toggleSidebar());
        }

        // Mobile menu toggle
        if (this.mobileToggleBtn) {
            this.mobileToggleBtn.addEventListener('click', () => this.toggleMobileSidebar());
        }

        // Mobile overlay click
        if (this.overlay) {
            this.overlay.addEventListener('click', () => this.closeMobileSidebar());
        }

        // Dropdown toggles agora são .menu-dropdown > .menu-link
        this.dropdownToggles = document.querySelectorAll('.menu-dropdown > .menu-link');
        this.dropdownToggles.forEach(toggle => {
            toggle.addEventListener('click', (e) => this.toggleDropdown(e));
            // Dropdown flyout no modo retraído: abre no hover
            toggle.addEventListener('mouseenter', (e) => {
                if (this.isCollapsed) {
                    this.openDropdown(e.currentTarget);
                }
            });
            toggle.addEventListener('mouseleave', (e) => {
                if (this.isCollapsed) {
                    this.closeDropdown(e.currentTarget);
                }
            });
        });

        // Window resize
        window.addEventListener('resize', () => this.handleResize());

        // Close mobile sidebar when clicking on a menu item
        document.querySelectorAll('.menu-link:not(.dropdown-toggle)').forEach(link => {
            link.addEventListener('click', () => {
                if (this.isMobile) {
                    this.closeMobileSidebar();
                }
            });
        });

        // Keyboard navigation
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
    }

    toggleSidebar() {
        if (this.isMobile) return;

        this.isCollapsed = !this.isCollapsed;
        this.sidebar.classList.toggle('collapsed', this.isCollapsed);
        this.saveState();

        // Close all dropdowns when collapsing
        if (this.isCollapsed) {
            this.closeAllDropdowns();
        }

        // Dispatch custom event
        window.dispatchEvent(new CustomEvent('sidebarToggle', {
            detail: { collapsed: this.isCollapsed }
        }));
    }

    toggleMobileSidebar() {
        if (!this.isMobile) return;

        const isOpen = this.sidebar.classList.contains('mobile-open');

        if (isOpen) {
            this.closeMobileSidebar();
        } else {
            this.openMobileSidebar();
        }
    }

    openMobileSidebar() {
        this.sidebar.classList.add('mobile-open');
        this.overlay.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    closeMobileSidebar() {
        this.sidebar.classList.remove('mobile-open');
        this.overlay.classList.remove('show');
        document.body.style.overflow = '';
    }

    toggleDropdown(e) {
        e.preventDefault();
        const toggle = e.currentTarget;
        const isExpanded = toggle.getAttribute('aria-expanded') === 'true';

        // Fecha outros dropdowns se não estiver colapsado
        if (!this.isCollapsed) {
            this.dropdownToggles.forEach(otherToggle => {
                if (otherToggle !== toggle) {
                    this.closeDropdown(otherToggle);
                }
            });
        }

        // Alterna o dropdown atual
        if (isExpanded) {
            this.closeDropdown(toggle);
        } else {
            this.openDropdown(toggle);
        }
    }

    openDropdown(toggle) {
        const submenu = toggle.parentElement.querySelector('.submenu');
        toggle.setAttribute('aria-expanded', 'true');
        if (submenu) submenu.classList.add('show');
        const dropdownId = toggle.getAttribute('data-dropdown');
        if (dropdownId) {
            localStorage.setItem(`dropdown-${dropdownId}`, 'open');
        }
    }
    closeDropdown(toggle) {
        const submenu = toggle.parentElement.querySelector('.submenu');
        toggle.setAttribute('aria-expanded', 'false');
        if (submenu) submenu.classList.remove('show');
        const dropdownId = toggle.getAttribute('data-dropdown');
        if (dropdownId) {
            localStorage.setItem(`dropdown-${dropdownId}`, 'closed');
        }
    }
    initializeDropdowns() {
        this.dropdownToggles.forEach(toggle => {
            const dropdownId = toggle.getAttribute('data-dropdown');
            const savedState = localStorage.getItem(`dropdown-${dropdownId}`);
            if (savedState === 'open' || this.hasActiveSubmenuItem(toggle)) {
                this.openDropdown(toggle);
            } else {
                this.closeDropdown(toggle);
            }
        });
    }
    hasActiveSubmenuItem(toggle) {
        const submenu = toggle.parentElement.querySelector('.submenu');
        return submenu && submenu.querySelector('.menu-link.active');
    }

    setActiveMenuItem() {
        // Remove existing active states
        document.querySelectorAll('.menu-link.active').forEach(link => {
            link.classList.remove('active');
        });

        // Set active based on current page
        const currentPath = window.location.pathname;
        const menuLinks = document.querySelectorAll('.menu-link');

        menuLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && (currentPath === href || currentPath.startsWith(href + '/'))) {
                link.classList.add('active');

                // Open parent dropdown if this is a submenu item
                const submenu = link.closest('.submenu');
                if (submenu) {
                    const parentToggle = submenu.previousElementSibling;
                    if (parentToggle && parentToggle.classList.contains('dropdown-toggle')) {
                        this.openDropdown(parentToggle);
                    }
                }
            }
        });
    }

    handleResize() {
        const newIsMobile = window.innerWidth <= 768;

        if (newIsMobile !== this.isMobile) {
            this.isMobile = newIsMobile;

            if (this.isMobile) {
                // Switch to mobile mode
                this.sidebar.classList.remove('collapsed');
                this.closeMobileSidebar();
            } else {
                // Switch to desktop mode
                this.sidebar.classList.remove('mobile-open');
                this.overlay.classList.remove('show');
                document.body.style.overflow = '';

                // Restore collapsed state
                this.sidebar.classList.toggle('collapsed', this.isCollapsed);
            }
        }
    }

    handleKeyboard(e) {
        // ESC key to close mobile sidebar
        if (e.key === 'Escape' && this.isMobile) {
            this.closeMobileSidebar();
        }

        // Alt + S to toggle sidebar
        if (e.altKey && e.key === 's') {
            e.preventDefault();
            if (this.isMobile) {
                this.toggleMobileSidebar();
            } else {
                this.toggleSidebar();
            }
        }
    }

    getStoredState() {
        const stored = localStorage.getItem('sidebar-collapsed');
        return stored === 'true';
    }

    saveState() {
        localStorage.setItem('sidebar-collapsed', this.isCollapsed);
    }

    setInitialState() {
        if (!this.isMobile) {
            this.sidebar.classList.toggle('collapsed', this.isCollapsed);
        }
    }

    closeAllDropdowns() {
        this.dropdownToggles.forEach(toggle => {
            this.closeDropdown(toggle);
        });
    }

    // Public methods for external use
    collapse() {
        if (!this.isMobile && !this.isCollapsed) {
            this.toggleSidebar();
        }
    }

    expand() {
        if (!this.isMobile && this.isCollapsed) {
            this.toggleSidebar();
        }
    }

    isCollapsedState() {
        return this.isCollapsed;
    }
}

// Initialize sidebar when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.modernSidebar = new ModernSidebar();
});

// Utility functions for menu management
const SidebarUtils = {
    // Add badge/notification to menu item
    addBadge(menuSelector, text, type = 'primary') {
        const menuItem = document.querySelector(menuSelector);
        if (menuItem) {
            const badge = document.createElement('span');
            badge.className = `badge badge-${type} ms-auto`;
            badge.textContent = text;
            menuItem.appendChild(badge);
        }
    },

    // Remove badge from menu item
    removeBadge(menuSelector) {
        const menuItem = document.querySelector(menuSelector);
        if (menuItem) {
            const badge = menuItem.querySelector('.badge');
            if (badge) {
                badge.remove();
            }
        }
    },

    // Highlight menu item temporarily
    highlightMenuItem(menuSelector, duration = 3000) {
        const menuItem = document.querySelector(menuSelector);
        if (menuItem) {
            menuItem.classList.add('highlight');
            setTimeout(() => {
                menuItem.classList.remove('highlight');
            }, duration);
        }
    },

    // Update user profile info
    updateUserProfile(name, role, avatarText) {
        const userName = document.querySelector('.user-name');
        const userRole = document.querySelector('.user-role');
        const userAvatar = document.querySelector('.user-avatar');

        if (userName) userName.textContent = name;
        if (userRole) userRole.textContent = role;
        if (userAvatar) userAvatar.textContent = avatarText;
    }
};

// Make utils available globally
window.SidebarUtils = SidebarUtils;
