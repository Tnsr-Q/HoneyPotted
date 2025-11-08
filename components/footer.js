class CustomFooter extends HTMLElement {
    connectedCallback() {
        this.attachShadow({ mode: 'open' });
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    width: 100%;
                }
                
                .footer {
                    background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
                    border-top: 1px solid rgba(55, 65, 81, 0.5);
                }
                
                .footer-link {
                    transition: all 0.3s ease;
                }
                
                .footer-link:hover {
                    color: #60a5fa;
                    transform: translateY(-2px);
                }
            </style>
            <footer class="footer py-12">
                <div class="container mx-auto px-6">
                    <div class="grid grid-cols-1 md:grid-cols-4 gap-8">
                        <div class="col-span-1 md:col-span-2">
                            <div class="flex items-center mb-4">
                                <i data-feather="shield" class="w-8 h-8 text-blue-400 mr-3"></i>
                                <span class="text-xl font-bold gradient-text">Quantum Deception Nexus</span>
                            </div>
                            <p class="text-gray-400 max-w-md">
                                Advanced bot manipulation honeypot system with cutting-edge quantum-resistant deception technology and AI-powered behavioral prediction.
                            </p>
                        </div>
                        
                        <div>
                            <h4 class="text-lg font-semibold mb-4 text-white">Modules</h4>
                            <ul class="space-y-2">
                                <li><a href="#modules" class="footer-link text-gray-400 hover:text-blue-400">Quantum Resistance</a></li>
                                <li><a href="#modules" class="footer-link text-gray-400 hover:text-blue-400">Behavior Prediction</a></li>
                                <li><a href="#modules" class="footer-link text-gray-400 hover:text-blue-400">Computational Tasks</a></li>
                            </ul>
                        </div>
                        
                        <div>
                            <h4 class="text-lg font-semibold mb-4 text-white">Resources</h4>
                            <ul class="space-y-2">
                                <li><a href="/documentation" class="footer-link text-gray-400 hover:text-blue-400">Documentation</a></li>
                                <li><a href="/api" class="footer-link text-gray-400 hover:text-blue-400">API Reference</a></li>
                                <li><a href="/github" class="footer-link text-gray-400 hover:text-blue-400">GitHub</a></li>
                                <li><a href="/blog" class="footer-link text-gray-400 hover:text-blue-400">Blog</a></li>
                            </ul>
                        </div>
                    </div>
                    
                    <div class="border-t border-gray-700 mt-8 pt-8 flex flex-col md:flex-row justify-between items-center">
                        <p class="text-gray-400 mb-4 md:mb-0">
                                © 2024 Quantum Deception Nexus. All rights reserved.
                            </p>
                            <div class="flex space-x-6">
                                <a href="#" class="footer-link text-gray-400 hover:text-blue-400">
                                    <i data-feather="github" class="w-5 h-5"></i>
                                </a>
                                <a href="#" class="footer-link text-gray-400 hover:text-blue-400">
                                    <i data-feather="twitter" class="w-5 h-5"></i>
                                </a>
                                <a href="#" class="footer-link text-gray-400 hover:text-blue-400">
                                    <i data-feather="linkedin" class="w-5 h-5"></i>
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </footer>
        `;
        
        // Initialize feather icons in shadow DOM
        setTimeout(() => {
            const icons = this.shadowRoot.querySelectorAll('[data-feather]');
            icons.forEach(icon => {
                feather.replace(icon);
            });
        }, 100);
    }
}

customElements.define('custom-footer', CustomFooter);