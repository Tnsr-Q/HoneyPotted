class CustomNavbar extends HTMLElement {
    connectedCallback() {
        this.attachShadow({ mode: 'open' });
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    width: 100%;
                    position: sticky;
                    top: 0;
                    z-index: 1000;
                }
                
                .navbar {
                    background: rgba(17, 24, 39, 0.95);
                    backdrop-filter: blur(10px);
                    border-bottom: 1px solid rgba(55, 65, 81, 0.5);
                    transition: all 0.3s ease;
                }
                
                .nav-link {
                    position: relative;
                    transition: all 0.3s ease;
                }
                
                .nav-link:hover {
                    color: #60a5fa;
                }
                
                .nav-link::after {
                    content: '';
                    position: absolute;
                    bottom: -2px;
                    left: 0;
                    width: 0;
                    height: 2px;
                    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
                    transition: width 0.3s ease;
                }
                
                .nav-link:hover::after {
                    width: 100%;
                }
                
                .mobile-menu {
                    transition: all 0.3s ease;
                }
                
                @media (max-width: 768px) {
                    .mobile-menu {
                        transform: translateY(-10px);
                        opacity: 0;
                    }
                    
                    .mobile-menu.open {
                        transform: translateY(0);
                        opacity: 1;
                    }
                }
            </style>
            <nav class="navbar py-4">
                <div class="container mx-auto px-6">
                    <div class="flex justify-between items-center">
                        <div class="flex items-center">
                            <i data-feather="shield" class="w-8 h-8 text-blue-400 mr-3"></i>
                            <span class="text-xl font-bold gradient-text">Quantum Nexus</span>
                        </div>
                        
                        <!-- Desktop Menu -->
                        <div class="hidden md:flex space-x-8">
                            <a href="#modules" class="nav-link text-gray-300 hover:text-white">Modules</a>
                            <a href="#dashboard" class="nav-link text-gray-300 hover:text-white">Dashboard</a>
                            <a href="/documentation" class="nav-link text-gray-300 hover:text-white">Documentation</a>
                            <a href="/api" class="nav-link text-gray-300 hover:text-white">API</a>
                        </div>
                        
                        <!-- Mobile Menu Button -->
                        <button class="md:hidden mobile-menu-btn p-2 rounded-lg hover:bg-gray-700 transition-colors">
                                <i data-feather="menu" class="w-6 h-6 text-gray-300"></i>
                        </button>
                    </div>
                    
                    <!-- Mobile Menu -->
                    <div class="mobile-menu hidden md:hidden mt-4 bg-gray-800 rounded-lg p-4">
                        <div class="flex flex-col space-y-4">
                            <a href="#modules" class="nav-link text-gray-300 hover:text-white">Modules</a>
                            <a href="#dashboard" class="nav-link text-gray-300 hover:text-white">Dashboard</a>
                            <a href="/documentation" class="nav-link text-gray-300 hover:text-white">Documentation</a>
                            <a href="/api" class="nav-link text-gray-300 hover:text-white">API</a>
                        </div>
                    </div>
                </div>
            </nav>
        `;
        
        // Add event listeners for mobile menu
        this.setupMobileMenu();
    }
    
    setupMobileMenu() {
        const mobileMenuBtn = this.shadowRoot.querySelector('.mobile-menu-btn');
        const mobileMenu = this.shadowRoot.querySelector('.mobile-menu');
        
        if (mobileMenuBtn && mobileMenu) {
            mobileMenuBtn.addEventListener('click', () => {
                mobileMenu.classList.toggle('hidden');
                mobileMenu.classList.toggle('open');
                
                // Update menu icon
                const menuIcon = mobileMenuBtn.querySelector('i');
                if (menuIcon) {
                    if (mobileMenu.classList.contains('hidden')) {
                        menuIcon.setAttribute('data-feather', 'menu');
                    } else {
                        menuIcon.setAttribute('data-feather', 'x');
                    }
                    feather.replace();
                }
            });
        }
    }
}

customElements.define('custom-navbar', CustomNavbar);