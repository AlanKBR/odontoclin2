/**
 * AI Configuration Panel JavaScript - Modern Interface
 * Unified model management with dashboard and grid view
 */

class AIConfigManager {
    constructor() {
        this.hardwareInfo = null;
        this.currentConfig = {};
        this.installedModels = [];
        this.searchResults = [];
        this.allModels = [];
        this.currentView = 'installed'; // 'installed' or 'search'
        this.isLoading = false;
        this.diskUsage = null;
        this.currentPage = 1;
        this.modelsPerPage = 6;
        
        // Sistema de progresso de download
        this.downloadingModels = new Set();
        this.downloadProgress = {};
        this.downloadIntervals = {};
        
        // Controle de busca
        this.searchController = null;
        this.lastSearchQuery = '';
        this.currentFilter = 'all';
        
        // Sistema de ordenação
        this.sortBy = 'downloads'; // 'downloads', 'name', 'size', 'date'
        this.sortDirection = 'desc'; // 'asc', 'desc'
        
        // Timeout para requisições
        this.requestTimeout = 15000; // 15 segundos
        
        this.initializeEventListeners();
        // Carregar dados automaticamente quando instanciado
        this.loadInitialData();
    }
    
    initializeEventListeners() {
        console.log('🔧 Inicializando event listeners...');
        
        // Status refresh button
        const btnRefreshStatus = document.getElementById('btn-refresh-status');
        if (btnRefreshStatus) {
            btnRefreshStatus.addEventListener('click', () => {
                this.userInitiatedStatusRefresh = true;
                this.refreshStatus();
            });
            console.log('✅ btn-refresh-status listener adicionado');
        } else {
            console.warn('⚠️ Elemento btn-refresh-status não encontrado');
        }
        
        // Test config button
        const btnTestConfig = document.getElementById('btn-test-config');
        if (btnTestConfig) {
            btnTestConfig.addEventListener('click', async () => {
                console.log('🔧 Teste: Carregando configuração...');
                await this.loadCurrentConfiguration();
            });
            console.log('✅ btn-test-config listener adicionado');
        } else {
            console.warn('⚠️ Elemento btn-test-config não encontrado');
        }
        
        // Model selector change
        const modelSelector = document.getElementById('model-selector');
        if (modelSelector) {
            modelSelector.addEventListener('change', (e) => {
                this.handleModelSelection(e.target.value);
            });
            console.log('✅ model-selector listener adicionado');
        } else {
            console.warn('⚠️ Elemento model-selector não encontrado');
        }
        
        // Configuration form
        const configForm = document.getElementById('config-form');
        if (configForm) {
            configForm.addEventListener('change', () => {
                this.validateConfiguration();
            });
            console.log('✅ config-form listener adicionado');
        } else {
            console.warn('⚠️ Elemento config-form não encontrado');
        }

        // Processing method change handler for GPU detection
        const processingMethodSelect = document.getElementById('processing-method');
        if (processingMethodSelect) {
            processingMethodSelect.addEventListener('change', () => {
                this.handleProcessingMethodChange();
            });
            console.log('✅ processing-method listener adicionado');
        } else {
            console.warn('⚠️ Elemento processing-method não encontrado');
        }
        
        // Temperature slider
        const temperatureSlider = document.getElementById('temperature');
        const temperatureValue = document.getElementById('temperature-value');
        if (temperatureSlider && temperatureValue) {
            temperatureSlider.addEventListener('input', (e) => {
                temperatureValue.textContent = e.target.value;
            });
            console.log('✅ temperature listener adicionado');
        } else {
            console.warn('⚠️ Elementos temperature ou temperature-value não encontrados');
        }
        
        // Advanced options toggle
        const advancedToggle = document.getElementById('advanced-toggle');
        const advancedContent = document.getElementById('advanced-content');
        const toggleIcon = document.getElementById('toggle-icon');
        
        if (advancedToggle && advancedContent && toggleIcon) {
            advancedToggle.addEventListener('click', () => {
                const isHidden = advancedContent.classList.contains('hidden');
                
                if (isHidden) {
                    advancedContent.classList.remove('hidden');
                    advancedToggle.classList.add('expanded');
                    toggleIcon.classList.remove('bi-chevron-down');
                    toggleIcon.classList.add('bi-chevron-up');
                } else {
                    advancedContent.classList.add('hidden');
                    advancedToggle.classList.remove('expanded');
                    toggleIcon.classList.remove('bi-chevron-up');
                    toggleIcon.classList.add('bi-chevron-down');
                }
            });
            console.log('✅ advanced-toggle listener adicionado');
        } else {
            console.warn('⚠️ Elementos advanced-toggle, advanced-content ou toggle-icon não encontrados');
        }
        
        // Action buttons
        const btnSaveConfig = document.getElementById('btn-save-config');
        if (btnSaveConfig) {
            btnSaveConfig.addEventListener('click', () => {
                this.saveConfiguration();
            });
            console.log('✅ btn-save-config listener adicionado');
        } else {
            console.warn('⚠️ Elemento btn-save-config não encontrado');
        }
        
        const btnStartAI = document.getElementById('btn-start-ai');
        if (btnStartAI) {
            btnStartAI.addEventListener('click', () => {
                this.startAI();
            });
            console.log('✅ btn-start-ai listener adicionado');
        } else {
            console.warn('⚠️ Elemento btn-start-ai não encontrado');
        }
        
        const btnStopAI = document.getElementById('btn-stop-ai');
        if (btnStopAI) {
            btnStopAI.addEventListener('click', () => {
                this.stopAI();
            });
            console.log('✅ btn-stop-ai listener adicionado');
        } else {
            console.warn('⚠️ Elemento btn-stop-ai não encontrado');
        }
        
        // Model management event listeners
        this.initializeModelManagementListeners();
        
        console.log('✅ Todos os event listeners principais inicializados');
    }
    
    initializeModelManagementListeners() {
        console.log('🔧 Inicializando listeners de gerenciamento de modelos...');
        
        // Smart search functionality
        const searchInput = document.getElementById('model-search-input');
        const searchBtn = document.getElementById('btn-search-models');
        const clearBtn = document.getElementById('btn-clear-search');
        
        if (searchInput) {
            // Busca apenas ao pressionar Enter
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performSearch();
                }
            });
            console.log('✅ model-search-input listener (Enter) adicionado');
        } else {
            console.warn('⚠️ Elemento model-search-input não encontrado');
        }
        
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                this.performSearch();
            });
            console.log('✅ btn-search-models listener adicionado');
        } else {
            console.warn('⚠️ Elemento btn-search-models não encontrado');
        }
        
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearSearch();
            });
            console.log('✅ btn-clear-search listener adicionado');
        } else {
            console.warn('⚠️ Elemento btn-clear-search não encontrado');
        }
        
        // Dashboard refresh buttons
        const refreshBtn = document.getElementById('btn-refresh-models');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshModelData();
            });
            console.log('✅ btn-refresh-models listener adicionado');
        } else {
            console.warn('⚠️ Elemento btn-refresh-models não encontrado');
        }
        
        const cleanupBtn = document.getElementById('btn-cleanup-cache');
        if (cleanupBtn) {
            cleanupBtn.addEventListener('click', () => {
                this.cleanupCache();
            });
            console.log('✅ btn-cleanup-cache listener adicionado');
        } else {
            console.warn('⚠️ Elemento btn-cleanup-cache não encontrado');
        }
        
        // Sort controls
        const sortSelect = document.getElementById('sort-models-select');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                const [sortBy, direction] = e.target.value.split('-');
                this.setSorting(sortBy, direction);
            });
            console.log('✅ sort-models-select listener adicionado');
        } else {
            console.warn('⚠️ Elemento sort-models-select não encontrado');
        }
        
        // Sort buttons (alternative UI)
        const sortButtons = document.querySelectorAll('.sort-btn');
        if (sortButtons.length > 0) {
            sortButtons.forEach(btn => {
                btn.addEventListener('click', () => {
                    const sortBy = btn.dataset.sort;
                    const currentDirection = this.sortBy === sortBy ? this.sortDirection : 'desc';
                    const newDirection = currentDirection === 'desc' ? 'asc' : 'desc';
                    this.setSorting(sortBy, newDirection);
                });
            });
            console.log(`✅ ${sortButtons.length} sort-btn listeners adicionados`);
        } else {
            console.warn('⚠️ Nenhum elemento .sort-btn encontrado');
        }
        
        console.log('✅ Todos os listeners de gerenciamento de modelos inicializados');
    }
    
    async loadInitialData() {
        console.log('🚀 Iniciando carregamento de dados...');
        this.showLoading('Carregando configurações...', 'Detectando hardware e modelos disponíveis');
        
        try {
            // Carregar hardware primeiro (mais importante)
            console.log('1️⃣ Carregando hardware...');
            await this.loadHardwareInfo();
            
            // Carregar modelos primeiro (necessário para validação)
            console.log('2️⃣ Carregando modelos instalados...');
            await this.loadInstalledModels();
            
            // Carregar o resto em paralelo
            console.log('3️⃣ Carregando demais dados...');
            await Promise.allSettled([
                this.loadCurrentConfiguration(),
                this.loadDiskUsage(),
                this.refreshStatus()
            ]);
            
            console.log('4️⃣ Aplicando configurações...');
            this.applyRecommendations();
            this.updateDashboard();
            this.renderCurrentView();
            
            console.log('✅ Dados iniciais carregados com sucesso');
            
        } catch (error) {
            console.error('❌ Error loading initial data:', error);
            this.showError('Erro ao carregar configurações iniciais: ' + error.message);
        } finally {
            // Garantir que o loading seja sempre removido
            console.log('🏁 Finalizando carregamento...');
            this.hideLoading();
        }
    }
    
    async refreshModelData() {
        this.showLoading('Atualizando modelos...', 'Carregando dados atualizados');
        
        try {
            await Promise.all([
                this.loadInstalledModels(),
                this.loadDiskUsage()
            ]);
            
            this.combineModelData();
            this.updateDashboardCards();
            this.renderCurrentView();
            this.showSuccess('Dados atualizados com sucesso!');
            
        } catch (error) {
            console.error('Error refreshing model data:', error);
            this.showError('Erro ao atualizar dados dos modelos');
        } finally {
            this.hideLoading();
        }
    }
    
    async loadHardwareInfo() {
        try {
            console.log('🔄 Carregando informações de hardware...');
            const response = await this.fetchWithTimeout('/ai/api/hardware-info');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('📊 Resposta do hardware-info:', data);
            
            if (data.success) {
                this.hardwareInfo = data.hardware;
                this.displayHardwareInfo();
                console.log('✅ Hardware info carregado:', this.hardwareInfo);
            } else {
                const errorMsg = data.error || 'Falha na detecção de hardware';
                console.error('❌ Hardware detection failed:', errorMsg);
                throw new Error(errorMsg);
            }
        } catch (error) {
            console.error('❌ Error loading hardware info:', error);
            this.displayHardwareError();
            
            // More detailed error message
            let errorMessage = 'Não foi possível detectar informações de hardware';
            if (error.message) {
                if (error.message.includes('undefined')) {
                    errorMessage += ': Dados de hardware inválidos';
                } else if (error.message.includes('HTTP')) {
                    errorMessage += ': Erro de comunicação com servidor';
                } else {
                    errorMessage += ': ' + error.message;
                }
            }
            
            this.showWarning(errorMessage);
        }
    }
      async loadInstalledModels() {
        try {
            console.log('🔄 Carregando modelos instalados...');
            const response = await this.fetchWithTimeout('/ai/api/models/installed');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.installedModels = data.models || [];
                console.log('✅ Modelos instalados carregados:', this.installedModels);
                this.populateModelSelector();
            } else {
                console.error('❌ Erro ao carregar modelos instalados:', data.error);
                this.installedModels = [];
                this.populateModelSelector();
                this.showWarning('Erro ao carregar modelos instalados: ' + data.error);
            }
        } catch (error) {
            console.error('❌ Erro na requisição de modelos instalados:', error);
            this.installedModels = [];
            this.populateModelSelector();
            this.showError('Falha na conexão ao carregar modelos: ' + error.message);
        }
    }

    populateModelSelector() {
        const modelSelector = document.getElementById('model-selector');
        if (!modelSelector) {
            console.warn('⚠️ Elemento model-selector não encontrado');
            return;
        }

        console.log('🔄 Populando seletor com modelos instalados:', this.installedModels);

        if (this.installedModels.length === 0) {
            modelSelector.innerHTML = `
                <option value="">Nenhum modelo instalado</option>
                <option value="" disabled>Baixe modelos na seção "Buscar Modelos" abaixo</option>
            `;
            console.warn('⚠️ Nenhum modelo instalado encontrado');
            return;
        }

        // Limpar opções existentes e adicionar opção padrão
        modelSelector.innerHTML = '<option value="">Selecione um modelo...</option>';

        // Adicionar modelos instalados
        this.installedModels.forEach(model => {
            const option = document.createElement('option');
            
            // Determinar o nome e valor do modelo
            let modelName = model.name || model.path || 'Modelo Desconhecido';
            let modelValue = model.name || model.path || '';
            
            // Se o nome contém uma barra, extrair a parte final para exibição mais limpa
            let displayName = modelName;
            if (modelName.includes('/')) {
                const parts = modelName.split('/');
                displayName = `${parts[0]}/${parts[1]}`;
            }
            
            // Adicionar informações extras se disponíveis
            if (model.size_display) {
                displayName += ` (${model.size_display})`;
            } else if (model.size) {
                displayName += ` (${model.size})`;
            }
            
            option.value = modelValue;
            option.textContent = displayName;
            option.title = `Modelo: ${modelName}${model.type ? ', Tipo: ' + model.type : ''}${model.size_display ? ', Tamanho: ' + model.size_display : ''}`;
            
            modelSelector.appendChild(option);
            
            console.log(`✅ Modelo adicionado ao seletor: ${displayName} (${modelValue})`);
        });

        console.log(`✅ Seletor populado com ${this.installedModels.length} modelos instalados`);
    }
    
    async loadCurrentConfiguration() {
        try {
            console.log('🔄 Carregando configuração atual...');
            const response = await fetch('/ai/api/config');
            const data = await response.json();
            
            if (data.success) {
                console.log('✅ Configuração carregada:', data.config);
                this.currentConfig = data.config.current_settings;
                this.applyConfigurationToForm();
            } else {
                console.error('❌ Erro ao carregar configuração:', data.error);
            }
        } catch (error) {
            console.error('❌ Erro na requisição de configuração:', error);
        }
    }
    
    applyConfigurationToForm() {
        try {
            console.log('🔄 Aplicando configuração ao formulário:', this.currentConfig);
            
            // Processing method
            if (this.currentConfig.processing_method) {
                const methodRadio = document.querySelector(`input[name="processing_method"][value="${this.currentConfig.processing_method}"]`);
                if (methodRadio) {
                    methodRadio.checked = true;
                    console.log('✅ Processing method aplicado:', this.currentConfig.processing_method);
                } else {
                    console.warn('⚠️ Radio button não encontrado para processing_method:', this.currentConfig.processing_method);
                }
            }
            
            // Max tokens
            if (this.currentConfig.max_tokens) {
                const maxTokensInput = document.getElementById('max-tokens');
                if (maxTokensInput) {
                    maxTokensInput.value = this.currentConfig.max_tokens;
                    console.log('✅ Max tokens aplicado:', this.currentConfig.max_tokens);
                } else {
                    console.warn('⚠️ Campo max-tokens não encontrado');
                }
            }
            
            // Temperature
            if (this.currentConfig.temperature !== undefined) {
                const temperatureInput = document.getElementById('temperature');
                const temperatureValue = document.getElementById('temperature-value');
                if (temperatureInput) {
                    temperatureInput.value = this.currentConfig.temperature;
                    if (temperatureValue) {
                        temperatureValue.textContent = this.currentConfig.temperature;
                    }
                    console.log('✅ Temperature aplicada:', this.currentConfig.temperature);
                } else {
                    console.warn('⚠️ Campo temperature não encontrado');
                }
            }
            
            // Selected model
            if (this.currentConfig.selected_model || this.currentConfig.model_name) {
                const selectedModel = this.currentConfig.selected_model || this.currentConfig.model_name;
                
                // Verificar se o modelo selecionado está instalado
                const isModelInstalled = this.installedModels.some(model => 
                    model.name === selectedModel || model.path?.includes(selectedModel)
                );
                
                // Update hidden field
                const modelInput = document.getElementById('selected-model');
                if (modelInput) {
                    modelInput.value = isModelInstalled ? selectedModel : '';
                }
                
                // Update model selector apenas se o modelo estiver instalado
                const modelSelector = document.getElementById('model-selector');
                if (modelSelector) {
                    if (isModelInstalled) {
                        modelSelector.value = selectedModel;
                        this.handleModelSelection(selectedModel);
                        console.log('✅ Selected model aplicado:', selectedModel);
                    } else {
                        modelSelector.value = '';
                        this.handleModelSelection('');
                        console.warn(`⚠️ Modelo "${selectedModel}" não está instalado - seleção resetada`);
                        this.showWarning(`Modelo "${selectedModel}" não está mais disponível. Selecione outro modelo.`);
                    }
                } else {
                    console.warn('⚠️ Campo model-selector não encontrado');
                }
            }
            
            // Apply advanced options
            this.applyAdvancedOptions();
            
            console.log('✅ Configuração aplicada ao formulário com sucesso');
            
        } catch (error) {
            console.error('❌ Erro ao aplicar configuração ao formulário:', error);
        }
    }
    
    applyAdvancedOptions() {
        try {
            console.log('🔄 Aplicando opções avançadas:', this.currentConfig);
            
            // System prompt
            const systemPromptTextarea = document.getElementById('system-prompt');
            if (systemPromptTextarea && this.currentConfig.system_prompt) {
                systemPromptTextarea.value = this.currentConfig.system_prompt;
                console.log('✅ System prompt aplicado');
            }
            
            // Request timeout
            const requestTimeoutInput = document.getElementById('request-timeout');
            if (requestTimeoutInput && this.currentConfig.request_timeout) {
                requestTimeoutInput.value = this.currentConfig.request_timeout;
                console.log('✅ Request timeout aplicado:', this.currentConfig.request_timeout);
            }
            
            // Safety settings
            if (this.currentConfig.safety_settings) {
                const contentFilterCheckbox = document.getElementById('enable-content-filter');
                if (contentFilterCheckbox) {
                    contentFilterCheckbox.checked = this.currentConfig.safety_settings.enable_content_filter || false;
                    console.log('✅ Content filter aplicado:', this.currentConfig.safety_settings.enable_content_filter);
                }
            }
            
            // UI settings
            if (this.currentConfig.ui_settings) {
                const chatHistoryCheckbox = document.getElementById('enable-chat-history');
                if (chatHistoryCheckbox) {
                    chatHistoryCheckbox.checked = this.currentConfig.ui_settings.enable_chat_history !== false;
                    console.log('✅ Chat history aplicado:', this.currentConfig.ui_settings.enable_chat_history);
                }
            }
            
        } catch (error) {
            console.error('❌ Erro ao aplicar opções avançadas:', error);
        }
    }
    
    handleModelSelection(modelName) {
        console.log('🔄 Modelo selecionado:', modelName);
        
        // Update hidden field
        const hiddenField = document.getElementById('selected-model');
        if (hiddenField) {
            hiddenField.value = modelName;
        }
        
        // Update model status and details
        this.updateModelStatus(modelName);
        this.updateModelDetails(modelName);
    }

    updateModelStatus(modelName) {
        const statusElement = document.getElementById('model-status');
        if (!statusElement) return;
        
        if (!modelName) {
            statusElement.innerHTML = '<span class="status-badge status-unknown">Nenhum modelo selecionado</span>';
            return;
        }
        
        // Check if model is installed
        const isInstalled = this.installedModels.some(model => 
            model.name === modelName || model.path?.includes(modelName)
        );
        
        if (isInstalled) {
            statusElement.innerHTML = '<span class="status-badge status-installed">Modelo Instalado</span>';
        } else {
            statusElement.innerHTML = '<span class="status-badge status-available">Disponível para Download</span>';
        }
    }

    updateModelDetails(modelName) {
        const detailsCard = document.getElementById('model-details');
        const contentElement = document.getElementById('model-info-content');
        
        if (!detailsCard || !contentElement) return;
        
        if (!modelName) {
            detailsCard.classList.add('hidden');
            return;
        }
        
        // Find model info
        let modelInfo = this.installedModels.find(model => 
            model.name === modelName || model.path?.includes(modelName)
        );
        
        if (!modelInfo) {
            modelInfo = this.availableModels.find(model => 
                model.name === modelName
            );
        }
        
        // Generate model details
        const details = this.generateModelDetails(modelName, modelInfo);
        contentElement.innerHTML = details;
        detailsCard.classList.remove('hidden');
    }

    generateModelDetails(modelName, modelInfo) {
        const isInstalled = this.installedModels.some(model => 
            model.name === modelName || model.path?.includes(modelName)
        );
        
        let html = `
            <div class="model-info-item">
                <span class="model-info-label">Nome:</span>
                <span class="model-info-value">${modelName}</span>
            </div>
            <div class="model-info-item">
                <span class="model-info-label">Status:</span>
                <span class="model-info-value">${isInstalled ? 'Instalado' : 'Disponível'}</span>
            </div>
        `;
        
        if (modelInfo) {
            if (modelInfo.size) {
                html += `
                    <div class="model-info-item">
                        <span class="model-info-label">Tamanho:</span>
                        <span class="model-info-value">${modelInfo.size}</span>
                    </div>
                `;
            }
            
            if (modelInfo.type) {
                html += `
                    <div class="model-info-item">
                        <span class="model-info-label">Tipo:</span>
                        <span class="model-info-value">${modelInfo.type}</span>
                    </div>
                `;
            }
            
            if (modelInfo.path) {
                html += `
                    <div class="model-info-item">
                        <span class="model-info-label">Caminho:</span>
                        <span class="model-info-value">${modelInfo.path}</span>
                    </div>
                `;
            }
        }
        
        // Add compatibility info
        html += `
            <div class="model-info-item">
                <span class="model-info-label">Recomendado para:</span>
                <span class="model-info-value">Textos em Português</span>
            </div>
        `;
        
        return html;
    }
    
    combineModelData() {
        // Combine installed models and search results into a unified list
        const installedNames = new Set(this.installedModels.map(m => m.name));
        
        // Mark installed models
        const markedInstalled = this.installedModels.map(model => ({
            ...model,
            installed: true,
            status: 'installed'
        }));
        
        // Add search results that aren't installed (if we have search results)
        const searchOnlyResults = this.searchResults.filter(model => 
            !installedNames.has(model.name)
        ).map(model => ({
            ...model,
            installed: false,
            status: 'available'
        }));
        
        // Combine: installed models + search results (if any)
        this.allModels = [...markedInstalled, ...searchOnlyResults];
    }
    
    async refreshStatus() {
        try {
            const response = await fetch('/ai/api/status');
            const data = await response.json();
            
            if (data.success) {
                this.updateStatusDisplay(data.status);
            } else {
                throw new Error(data.error || 'Falha ao atualizar status');
            }
        } catch (error) {
            console.error('Error refreshing status:', error);
            // Mostrar toast apenas se for uma ação do usuário (não em updates automáticos)
            if (this.userInitiatedStatusRefresh) {
                this.showError('Erro ao atualizar status da IA');
                this.userInitiatedStatusRefresh = false;
            }
        }
    }
    
    // ============ Dashboard Methods ============
    
    updateDashboard() {
        this.updateDashboardCards();
        this.updateDiskUsageCard();
    }
    
    updateDashboardCards() {
        // Cards removidos - mantendo apenas método vazio para compatibilidade
        // Os cards de contadores de modelos foram removidos da interface
    }
    
    updateDiskUsageCard() {
        const usedSpace = document.getElementById('disk-used-space');
        const freeSpace = document.getElementById('disk-free-space');
        const usageBar = document.getElementById('disk-usage-bar');
        
        if (!this.diskUsage || this.diskUsage.error) {
            // Exibir erro nos elementos
            if (usedSpace) {
                usedSpace.textContent = 'Erro';
                usedSpace.title = this.diskUsage?.error || 'Falha ao carregar dados de disco';
            }
            if (freeSpace) {
                freeSpace.textContent = 'N/A';
                freeSpace.title = this.diskUsage?.error || 'Falha ao carregar dados de disco';
            }
            if (usageBar) {
                usageBar.style.width = '0%';
                usageBar.className = 'progress-bar bg-secondary';
            }
            return;
        }
        
        // Atualizar espaço usado (cache dos modelos)
        if (usedSpace) {
            const used = this.diskUsage.total_size_gb >= 1 ? 
                `${this.diskUsage.total_size_gb} GB` : 
                `${this.diskUsage.total_size_mb} MB`;
            usedSpace.textContent = used;
            usedSpace.title = `Cache dos modelos: ${used} (${this.diskUsage.models_count} modelos)`;
        }
        
        // Atualizar espaço livre
        if (freeSpace) {
            freeSpace.textContent = `${this.diskUsage.available_space_gb} GB`;
            freeSpace.title = `Espaço livre no disco: ${this.diskUsage.available_space_gb} GB`;
        }
        
        // Atualizar barra de progresso
        if (usageBar) {
            const usedGB = this.diskUsage.total_size_gb || 0;
            const totalSpaceGB = this.diskUsage.total_space_gb || 1;
            const percentage = Math.round((usedGB / totalSpaceGB) * 100);
            
            usageBar.style.width = `${percentage}%`;
            usageBar.setAttribute('aria-valuenow', percentage);
            usageBar.title = `${percentage}% do disco usado pelos modelos (${usedGB} GB de ${totalSpaceGB} GB)`;
            
            // Cor baseada no uso
            usageBar.className = 'progress-bar disk-progress-fill';
            if (percentage > 80) {
                usageBar.classList.add('bg-danger');
            } else if (percentage > 60) {
                usageBar.classList.add('bg-warning');
            } else {
                usageBar.classList.add('bg-success');
            }
        }
        
        console.log('✅ Card de uso de disco atualizado:', this.diskUsage);
    }
    
    // ============ Search and Filter Methods ============
    
    performSearch() {
        const searchInput = document.getElementById('model-search-input');
        const query = searchInput ? searchInput.value.trim() : '';
        
        // Limpar busca se query estiver vazia
        if (query.length === 0) {
            this.clearSearch();
            return;
        }
        
        // Validar tamanho mínimo da query
        if (query.length < 2) {
            this.showWarning('Digite pelo menos 2 caracteres para buscar.');
            return;
        }
        
        // Salvar query para referência
        this.lastSearchQuery = query;
        
        // Sempre buscar no Hugging Face para resultados completos
        this.searchHuggingFace(query);
    }
    
    async searchHuggingFace(query) {
        // Evitar múltiplas chamadas simultâneas
        if (this.isLoading) {
            console.log('Search already in progress, skipping...');
            return;
        }
        
        // Cancelar busca anterior se existir
        if (this.searchController) {
            this.searchController.abort();
        }
        
        // Criar novo controller para esta busca
        this.searchController = new AbortController();
        this.isLoading = true;
        this.showSearchLoading();
        
        try {
            console.log(`🔍 Buscando modelos para: "${query}"`);
            
            const params = new URLSearchParams({
                query: query,
                filter: this.currentFilter || 'all',
                limit: '30'
            });
            
            const response = await fetch(`/ai/api/models/search?${params}`, {
                signal: this.searchController.signal,
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('📡 Dados recebidos:', data);
            
            if (data.success) {
                console.log(`✅ Encontrados ${data.models.length} modelos para "${query}"`);
                
                // Garantir que installedModels está inicializado
                if (!this.installedModels) {
                    this.installedModels = [];
                }
                
                this.searchResults = data.models.map(model => ({
                    ...model,
                    installed: this.installedModels.some(im => im.name === model.name),
                    status: this.installedModels.some(im => im.name === model.name) ? 'installed' : 'available'
                }));
                
                this.currentView = 'search';
                this.renderSearchResults(query);
                
                if (this.searchResults.length === 0) {
                    this.showWarning(`Nenhum modelo encontrado para "${query}". Tente termos mais específicos ou verifique a ortografia.`);
                }
                
            } else {
                const errorMsg = data.error || 'Falha na busca de modelos';
                console.error('❌ Erro reportado pelo servidor:', errorMsg);
                throw new Error(errorMsg);
            }
        } catch (error) {
            // Não mostrar erro se foi cancelamento
            if (error.name !== 'AbortError') {
                console.error('❌ Erro na busca de modelos:', error);
                this.showError(`Erro ao buscar modelos: ${error.message}`);
                
                // Mostrar estado de erro no grid
                const container = document.getElementById('models-grid');
                if (container) {
                    container.innerHTML = `
                        <div class="empty-state text-center">
                            <i class="fas fa-exclamation-triangle fa-3x mb-3 text-warning"></i>
                            <h5>Erro na Busca</h5>
                            <p>Não foi possível buscar modelos no momento.</p>
                            <p class="text-muted">Verifique sua conexão e tente novamente.</p>
                        </div>
                    `;
                }
            }
        } finally {
            // Garantir que o estado seja sempre limpo
            this.isLoading = false;
            this.searchController = null;
            this.hideSearchLoading();
        }
    }
    
    filterLocalModels(query) {
        const filtered = this.allModels.filter(model => 
            model.name.toLowerCase().includes(query.toLowerCase()) ||
            (model.display_name && model.display_name.toLowerCase().includes(query.toLowerCase())) ||
            (model.description && model.description.toLowerCase().includes(query.toLowerCase()))
        );
        
        this.searchResults = filtered;
        this.currentView = 'search';
        this.renderSearchResults(query);
    }
    
    clearSearch() {
        const searchInput = document.getElementById('model-search-input');
        if (searchInput) {
            searchInput.value = '';
        }
        
        this.searchResults = [];
        this.currentView = 'installed';
        this.renderCurrentView();
    }
    
    // ============ Rendering Methods ============

    renderCurrentView() {
        const container = document.getElementById('models-grid');
        if (!container) return;
        
        if (this.currentView === 'search') {
            // Show search results
            this.renderSearchResults(this.lastSearchQuery || '');
        } else {
            // Show installed models by default
            const modelsToShow = this.installedModels.map(model => ({
                ...model,
                installed: true,
                status: 'installed',
                // Ensure size information is properly formatted for display
                size_estimate: model.size_display || model.size_estimate || 'Tamanho desconhecido',
                size_type: 'actual' // Mark as actual size since it's installed
            }));
            
            if (modelsToShow.length === 0) {
                container.innerHTML = this.createEmptyState('Nenhum Modelo Instalado');
                this.updateResultsInfo(0, 'Modelos Instalados');
                this.hidePagination();
                return;
            }
            
            const sortedModels = this.sortModels(modelsToShow);
            this.renderModelsGrid(sortedModels, 'Modelos Instalados', container);
            this.updateResultsInfo(modelsToShow.length, 'Modelos Instalados');
        }
    }
    
    renderSearchResults(query) {
        const container = document.getElementById('models-grid');
        if (!container) return;
        
        const title = `Resultados para "${query}"`;
        this.renderModelsGrid(this.searchResults, title, container);
        this.updateResultsInfo(this.searchResults.length, title);
    }

    // Funções de sorting para corrigir erro "this.sortModels is not a function"
    setSorting(sortBy, direction) {
        this.sortBy = sortBy;
        this.sortDirection = direction;
        console.log(`Sorting changed to: ${sortBy} ${direction}`);
        
        // Re-renderizar current view with new sorting
        this.renderCurrentView();
    }

    sortModels(models) {
        if (!models || models.length === 0) return models;
        
        return models.slice().sort((a, b) => {
            let aValue, bValue;
            
            switch (this.sortBy) {
                case 'downloads':
                    aValue = parseInt(a.downloads) || 0;
                    bValue = parseInt(b.downloads) || 0;
                    break;
                case 'name':
                    aValue = (a.name || '').toLowerCase();
                    bValue = (b.name || '').toLowerCase();
                    break;
                case 'size':
                    aValue = this.parseSize(a.size_estimate) || 0;
                    bValue = this.parseSize(b.size_estimate) || 0;
                    break;
                case 'date':
                    aValue = new Date(a.lastModified || a.created_at || 0);
                    bValue = new Date(b.lastModified || b.created_at || 0);
                    break;
                default:
                    return 0;
            }
            
            // Handle string vs number comparison
            if (typeof aValue === 'string' && typeof bValue === 'string') {
                const comparison = aValue.localeCompare(bValue);
                return this.sortDirection === 'asc' ? comparison : -comparison;
            } else {
                const comparison = aValue - bValue;
                return this.sortDirection === 'asc' ? comparison : -comparison;
            }
        });
    }

    parseSize(sizeString) {
        if (!sizeString || sizeString === 'N/A') return 0;
        
        const match = sizeString.match(/(\d+(?:\.\d+)?)\s*(GB|MB|KB)/i);
        if (!match) return 0;
        
        const value = parseFloat(match[1]);
        const unit = match[2].toUpperCase();
        
        switch (unit) {
            case 'GB': return value * 1024 * 1024 * 1024;
            case 'MB': return value * 1024 * 1024;
            case 'KB': return value * 1024;
            default: return value;
        }
    }
    
    renderModelsGrid(models, title, container) {
        if (models.length === 0) {
            container.innerHTML = this.createEmptyState(title);
            return;
        }
        
        // Pagination
        const startIndex = (this.currentPage - 1) * this.modelsPerPage;
        const endIndex = startIndex + this.modelsPerPage;
        const paginatedModels = models.slice(startIndex, endIndex);
        
        let html = '';
        paginatedModels.forEach(model => {
            html += this.createModelCard(model);
        });
        
        container.innerHTML = html;
        
        // Render pagination if needed
        if (models.length > this.modelsPerPage) {
            this.renderPagination(models.length);
        } else {
            this.hidePagination();
        }
    }
    
    createModelCard(model) {
        const isInstalled = model.installed;
        const canDownload = !isInstalled;
        const canRemove = isInstalled;
        
        let typeClass = `model-type-${model.type || 'general'}`;
        let typeBadge = this.getTypeBadge(model.type);
        
        // Melhor exibição do tamanho com informações de status
        let sizeInfo = '';
        const sizeDisplay = model.size_display || model.size_estimate || 'Tamanho desconhecido';
        const sizeType = model.size_type || 'unknown';
        const isIncomplete = model.is_incomplete || false;
        const statusInfo = model.status_info || '';
        
        if (sizeDisplay && sizeDisplay !== 'Desconhecido' && sizeDisplay !== 'Tamanho desconhecido') {
            const sizeClass = this.getSizeClass(model.size_bytes || model.size_mb * 1024 * 1024 || 0);
            
            let sizeIcon = 'fas fa-hdd';
            let sizeTitle = sizeDisplay;
            let sizeClass2 = '';
            
            // Diferentes ícones e estilos baseados no tipo e status
            if (isIncomplete) {
                sizeIcon = 'fas fa-exclamation-triangle text-warning';
                sizeClass2 = 'incomplete';
                sizeTitle = `${statusInfo}: ${sizeDisplay}`;
            } else {
                switch(sizeType) {
                    case 'actual':
                        sizeIcon = 'fas fa-check-circle text-success';
                        sizeTitle = `Tamanho real: ${sizeDisplay}`;
                        if (model.file_count > 0) {
                            sizeTitle += ` (${model.file_count} arquivos)`;
                        }
                        if (model.actual_model_files !== undefined) {
                            sizeTitle += ` - ${model.actual_model_files} arquivo(s) de modelo`;
                        }
                        break;
                    case 'estimated':
                        sizeIcon = 'fas fa-chart-line text-info';
                        sizeTitle = `Tamanho estimado: ${sizeDisplay}`;
                        break;
                    case 'incomplete':
                        sizeIcon = 'fas fa-exclamation-circle text-warning';
                        sizeClass2 = 'incomplete';
                        sizeTitle = `Incompleto: ${sizeDisplay}`;
                        break;
                    case 'metadata_only':
                        sizeIcon = 'fas fa-info-circle text-info';
                        sizeClass2 = 'metadata-only';
                        sizeTitle = `Apenas metadados: ${sizeDisplay}`;
                        break;
                    case 'unavailable':
                        sizeIcon = 'fas fa-times-circle text-danger';
                        sizeClass2 = 'unavailable';
                        sizeTitle = 'Download incompleto ou corrompido';
                        break;
                    case 'unknown':
                    default:
                        sizeIcon = 'fas fa-question-circle text-muted';
                        sizeTitle = statusInfo || 'Tamanho não informado';
                        break;
                }
            }
            
            sizeInfo = `<span class="model-size ${sizeClass} size-${sizeType} ${sizeClass2}" title="${sizeTitle}">
                <i class="${sizeIcon}"></i> <strong>${sizeDisplay}</strong>
            </span>`;
        } else {
            sizeInfo = `<span class="model-size size-unknown" title="Tamanho não disponível">
                <i class="fas fa-question-circle text-muted"></i> Tamanho não disponível
            </span>`;
        }
        
        let downloads = '';
        if (model.downloads && model.downloads !== 'N/A' && model.downloads > 0) {
            downloads = `<span class="model-downloads">
                <i class="fas fa-download"></i> ${model.downloads.toLocaleString()}
            </span>`;
        }
        
        // Informações de quantização para variantes GGUF
        let ggufInfo = '';
        if (model.is_gguf_variant && model.quantization) {
            const quantClass = this.getQuantizationClass(model.quantization);
            ggufInfo = `<span class="gguf-quantization ${quantClass}" title="${model.precision || 'Quantization'}: ${model.quantization}">
                <i class="fas fa-compress-alt"></i> ${model.quantization}
            </span>`;
        }
        
        // Verificar se está em download
        const isDownloading = this.downloadingModels.has(model.name);
        let progressBar = '';
        let actions = '';
        
        if (isDownloading) {
            const progress = this.downloadProgress[model.name] || { 
                progress: 0, 
                status: 'Iniciando...', 
                downloaded_bytes: 0, 
                total_bytes: 0, 
                speed: 0, 
                eta: 0 
            };
            
            // Formatear informações de download
            let downloadInfo = '';
            if (progress.total_bytes > 0) {
                const downloadedMB = (progress.downloaded_bytes / (1024 * 1024)).toFixed(1);
                const totalMB = (progress.total_bytes / (1024 * 1024)).toFixed(1);
                const speedMB = (progress.speed / (1024 * 1024)).toFixed(1);
                
                downloadInfo = `<div class="download-info">
                    <small class="text-muted">
                        ${downloadedMB}/${totalMB} MB`;
                        
                if (progress.speed > 0) {
                    downloadInfo += ` • ${speedMB} MB/s`;
                }
                
                if (progress.eta > 0) {
                    const etaMinutes = Math.floor(progress.eta / 60);
                    const etaSeconds = progress.eta % 60;
                    if (etaMinutes > 0) {
                        downloadInfo += ` • ETA: ${etaMinutes}min ${etaSeconds}s`;
                    } else {
                        downloadInfo += ` • ETA: ${etaSeconds}s`;
                    }
                }
                
                downloadInfo += `</small></div>`;
            }
            
            progressBar = `
                <div class="download-progress">
                    <div class="progress-header">
                        <span class="progress-text">${progress.status}</span>
                        <span class="progress-percent">${progress.progress}%</span>
                    </div>
                    <div class="progress mb-2">
                        <div class="progress-bar progress-bar-animated" role="progressbar" 
                             style="width: ${progress.progress}%" 
                             aria-valuenow="${progress.progress}" 
                             aria-valuemin="0" aria-valuemax="100">
                        </div>
                    </div>
                    ${downloadInfo}
                    <button class="btn btn-sm btn-outline-secondary mt-2" onclick="aiConfigManager.cancelDownload('${model.name}')">
                        <i class="fas fa-times"></i> Cancelar
                    </button>
                </div>
            `;
        } else {
            if (canDownload) {
                actions += `<button class="btn btn-primary btn-sm model-action-btn" onclick="aiConfigManager.downloadModel('${model.name}')">
                    <i class="fas fa-download"></i> Instalar
                </button>`;
            }
            if (canRemove) {
                actions += `<button class="btn btn-danger btn-sm model-action-btn" onclick="aiConfigManager.removeModel('${model.name}')">
                    <i class="fas fa-trash"></i> Remover
                </button>`;
            }
        }
        
        // Exibir nome do arquivo GGUF se for uma variante específica
        let modelDisplayName = model.display_name || model.name;
        let fileInfo = '';
        if (model.is_gguf_variant && model.file_name) {
            fileInfo = `<div class="gguf-file-name" title="Arquivo: ${model.file_name}">
                <i class="fas fa-file"></i> ${model.file_name}
            </div>`;
        }
        
        const cardClass = isInstalled ? 'model-card installed' : 'model-card available';
        
        return `
            <div class="${cardClass}" data-model="${model.name}">
                <div class="model-card-header">
                    <div class="model-info">
                        <h6 class="model-name">${modelDisplayName}</h6>
                        ${model.organization ? `<div class="model-org">${model.organization}</div>` : ''}
                        ${fileInfo}
                    </div>
                    <div class="model-badges">
                        <span class="model-type-badge ${typeClass}">${typeBadge}</span>
                        ${isInstalled ? '<span class="model-status-badge installed"><i class="fas fa-check"></i> Instalado</span>' : ''}
                    </div>
                </div>
                
                <p class="model-description">${model.description || model.name}</p>
                
                <div class="model-meta">
                    ${sizeInfo}
                    ${ggufInfo}
                    ${downloads}
                </div>
                
                ${progressBar}
                ${actions ? `<div class="model-actions">${actions}</div>` : ''}
            </div>
        `;
    }
    
    getTypeBadge(type) {
        const typeMap = {
            'medical': 'Médico',
            'conversational': 'Conversacional',
            'code': 'Código',
            'language_model': 'Linguagem',
            'recommended': 'Recomendado'
        };
        return typeMap[type] || 'Geral';
    }
    
    getSizeClass(sizeBytes) {
        if (!sizeBytes || sizeBytes === 0) {
            return 'size-unknown';
        }
        
        // Converter bytes para MB
        const sizeMB = sizeBytes / (1024 * 1024);
        
        // Classificar por tamanho conforme CSS existente
        if (sizeMB < 100) {
            return 'size-small';     // < 100MB - Verde
        } else if (sizeMB < 500) {
            return 'size-medium';    // 100MB-500MB - Amarelo
        } else if (sizeMB < 2000) {
            return 'size-large';     // 500MB-2GB - Vermelho
        } else {
            return 'size-huge';      // > 2GB - Azul
        }
    }
    
    getQuantizationClass(quantization) {
        // Classificar quantizações por qualidade/tamanho
        if (quantization.includes('F32') || quantization.includes('F16')) {
            return 'quant-high'; // Precisão alta
        } else if (quantization.includes('Q8') || quantization.includes('Q6')) {
            return 'quant-medium-high'; // Precisão média-alta
        } else if (quantization.includes('Q5') || quantization.includes('Q4')) {
            return 'quant-medium'; // Precisão média
        } else if (quantization.includes('Q3') || quantization.includes('Q2')) {
            return 'quant-low'; // Precisão baixa (menor tamanho)
        }
        return 'quant-unknown';
    }
    
    createEmptyState(title) {
        let message = '';
        let icon = 'fas fa-search';
        
        if (this.currentView === 'installed' || title.includes('Instalado')) {
            message = 'Nenhum modelo instalado. Use a busca para encontrar e instalar modelos.';
            icon = 'fas fa-download';
        } else if (this.currentView === 'search') {
            message = 'Nenhum resultado encontrado. Tente termos diferentes.';
        } else {
            message = 'Nenhum modelo disponível no momento.';
        }
        
        return `
            <div class="empty-state">
                <i class="${icon} fa-3x mb-3"></i>
                <h5>${title}</h5>
                <p>${message}</p>
            </div>
        `;
    }
    
    updateResultsInfo(count, title) {
        const infoElement = document.getElementById('results-info');
        if (infoElement) {
            infoElement.textContent = `${title} (${count} modelo${count !== 1 ? 's' : ''})`;
        }
    }
    
    showSearchLoading() {
        const container = document.getElementById('models-grid');
        if (container) {
            container.innerHTML = `
                <div class="loading-state">
                    <div class="spinner-border text-primary" role="status">
                        <span class="sr-only">Carregando...</span>
                    </div>
                    <p class="mt-3">Buscando modelos...</p>
                </div>
            `;
        }
    }
    
    hideSearchLoading() {
        // Will be replaced by the results
    }
    
    renderPagination(totalItems) {
        const totalPages = Math.ceil(totalItems / this.modelsPerPage);
        const paginationContainer = document.getElementById('pagination-container');
        
        if (!paginationContainer || totalPages <= 1) {
            this.hidePagination();
            return;
        }
        
        let html = '<nav aria-label="Model pagination"><ul class="pagination justify-content-center">';
        
        // Previous button
        html += `<li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="aiConfigManager.goToPage(${this.currentPage - 1}); return false;">Anterior</a>
        </li>`;
        
        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            if (i === this.currentPage || i === 1 || i === totalPages || 
                (i >= this.currentPage - 2 && i <= this.currentPage + 2)) {
                html += `<li class="page-item ${i === this.currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="aiConfigManager.goToPage(${i}); return false;">${i}</a>
                </li>`;
            } else if (i === this.currentPage - 3 || i === this.currentPage + 3) {
                html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
        }
        
        // Next button
        html += `<li class="page-item ${this.currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="aiConfigManager.goToPage(${this.currentPage + 1}); return false;">Próxima</a>
        </li>`;
        
        html += '</ul></nav>';
        
        paginationContainer.innerHTML = html;
        paginationContainer.style.display = 'block';
    }
    
    hidePagination() {
        const paginationContainer = document.getElementById('pagination-container');
        if (paginationContainer) {
            paginationContainer.style.display = 'none';
        }
    }
    
    goToPage(page) {
        this.currentPage = page;
        this.renderCurrentView();
    }
    
    // ============ Model Actions ============

    async downloadModel(modelName) {
        try {
            console.log(`🚀 Iniciando download: ${modelName}`);
            
            // Verificar se já está baixando
            if (this.downloadingModels.has(modelName)) {
                console.warn(`⚠️ Download já em andamento para: ${modelName}`);
                return;
            }
            
            // Marcar como em download
            this.downloadingModels.add(modelName);
            this.downloadProgress[modelName] = { progress: 1, status: 'Iniciando download...' };
            
            // Re-renderizar para mostrar a barra de progresso
            this.renderCurrentView();
            
            // Usar sistema de monitoramento simplificado
            if (window.progressMonitor) {
                // Iniciar download via API
                const response = await fetch(`/ai/api/models/download`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ model_name: modelName })
                });
                
                if (!response.ok) {
                    throw new Error(`Falha ao iniciar download: ${response.status}`);
                }
                
                // Iniciar monitoramento de progresso
                window.progressMonitor.startMonitoring(modelName, (progress) => {
                    this.downloadProgress[modelName] = progress;
                    this.renderCurrentView();
                    
                    // Download concluído
                    if (!progress.downloading) {
                        this.downloadingModels.delete(modelName);
                        console.log(`✅ Download concluído: ${modelName}`);
                    }
                });
            } else {
                throw new Error('Sistema de monitoramento não disponível');
            }
            
            console.log(`📡 Download iniciado com sucesso: ${modelName}`);
        } catch (error) {
            console.error(`❌ Erro ao iniciar download: ${modelName}`, error);
            this.downloadingModels.delete(modelName);
            this.downloadProgress[modelName] = { 
                progress: 0, 
                status: `Erro: ${error.message || 'Falha no download'}` 
            };
            this.renderCurrentView();
        }
    }

    startProgressMonitoring(modelName) {
        console.log(`🔄 Iniciando monitoramento de progresso para: ${modelName}`);
        
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/ai/api/models/${encodeURIComponent(modelName)}/progress`);
                
                if (!response.ok) {
                    console.warn(`Erro na resposta de progresso: ${response.status}`);
                    return;
                }
                
                const data = await response.json();
                
                if (data.success && data.progress) {
                    // Atualizar progresso local
                    this.downloadProgress[modelName] = data.progress;
                    
                    // Atualizar interface
                    this.updateProgressBar(modelName, data.progress);
                    
                    console.log(`📊 Progresso ${modelName}: ${data.progress.progress}% - ${data.progress.status}`);
                    
                    // Se o download terminou, parar o monitoramento e mostrar sucesso
                    if (!data.progress.downloading || data.progress.progress >= 100) {
                        console.log(`✅ Download concluído: ${modelName}`);
                        
                        // Mostrar notificação de sucesso
                        this.showSuccess(`✅ Modelo "${modelName}" instalado com sucesso!`);
                        
                        // Parar monitoramento
                        this.stopProgressMonitoring(modelName);
                        
                        // Aguardar um pouco antes de atualizar a lista de modelos
                        setTimeout(async () => {
                            await this.refreshModelData();
                            // Limpar estado de download após atualizar
                            this.downloadingModels.delete(modelName);
                            delete this.downloadProgress[modelName];
                        }, 2000);
                    }
                } else {
                    console.warn('Resposta de progresso sem dados válidos:', data);
                }
            } catch (error) {
                console.warn('Erro ao monitorar progresso:', error);
            }
        }, 800); // Atualizar a cada 800ms para melhor responsividade
        
        this.downloadIntervals[modelName] = interval;
    }
    
    stopProgressMonitoring(modelName) {
        if (this.downloadIntervals[modelName]) {
            clearInterval(this.downloadIntervals[modelName]);
            delete this.downloadIntervals[modelName];
        }
    }
    
    updateProgressBar(modelName, progress) {
        const modelCard = document.querySelector(`[data-model="${modelName}"]`);
        if (!modelCard) {
            console.warn(`❌ Card não encontrado para modelo: ${modelName}`);
            return;
        }
        
        const progressBar = modelCard.querySelector('.progress-bar');
        const progressText = modelCard.querySelector('.progress-text');
        const progressPercent = modelCard.querySelector('.progress-percent');
        const downloadInfo = modelCard.querySelector('.download-info');
        
        if (progressBar) {
            progressBar.style.width = `${progress.progress}%`;
            progressBar.setAttribute('aria-valuenow', progress.progress);
            
            // Adicionar classe de animação se o progresso mudou
            progressBar.classList.add('progress-bar-animated');
        }
        
        if (progressText) {
            progressText.textContent = progress.status || 'Baixando...';
        }
        
        if (progressPercent) {
            progressPercent.textContent = `${progress.progress}%`;
        }
        
        // Atualizar informações detalhadas de download
        if (downloadInfo) {
            let infoHtml = '';
            
            if (progress.total_bytes > 0) {
                const downloadedMB = (progress.downloaded_bytes / (1024 * 1024)).toFixed(1);
                const totalMB = (progress.total_bytes / (1024 * 1024)).toFixed(1);
                
                infoHtml = `<small class="text-muted">${downloadedMB}/${totalMB} MB`;
                
                if (progress.speed > 0) {
                    const speedMB = (progress.speed / (1024 * 1024)).toFixed(1);
                    infoHtml += ` • ${speedMB} MB/s`;
                }
                
                if (progress.eta > 0) {
                    const etaMinutes = Math.floor(progress.eta / 60);
                    const etaSeconds = progress.eta % 60;
                    if (etaMinutes > 0) {
                        infoHtml += ` • ETA: ${etaMinutes}min ${etaSeconds}s`;
                    } else {
                        infoHtml += ` • ETA: ${etaSeconds}s`;
                    }
                }
                
                infoHtml += '</small>';
            }
            
            downloadInfo.innerHTML = infoHtml;
        }
        
        // Log para debug
        console.log(`📊 UI atualizada - ${modelName}: ${progress.progress}% (${progress.status})`);
        if (progress.total_bytes > 0) {
            console.log(`📊 Detalhes - Downloaded: ${(progress.downloaded_bytes / (1024 * 1024)).toFixed(1)}MB/${(progress.total_bytes / (1024 * 1024)).toFixed(1)}MB, Speed: ${(progress.speed / (1024 * 1024)).toFixed(1)}MB/s, ETA: ${progress.eta}s`);
        }
    }
    
    async cancelDownload(modelName) {
        if (!confirm(`Cancelar download de "${modelName}"?`)) {
            return;
        }

        try {
            // Chamar o endpoint de cancelamento no backend
            const response = await fetch(`/ai/api/models/${encodeURIComponent(modelName)}/cancel`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                signal: AbortSignal.timeout(this.requestTimeout)
            });

            const result = await response.json();

            if (response.ok) {
                // Cancelamento bem-sucedido no backend
                if (window.progressMonitor) {
                    window.progressMonitor.stopMonitoring(modelName);
                }
                this.downloadingModels.delete(modelName);
                delete this.downloadProgress[modelName];
                this.renderCurrentView();
                this.showSuccess(result.message || `Download de "${modelName}" cancelado com sucesso`);
            } else {
                // Erro no cancelamento
                this.showError(result.error || `Erro ao cancelar download de "${modelName}"`);
            }
        } catch (error) {
            console.error('Erro ao cancelar download:', error);
            
            // Se houve erro na comunicação, ainda assim limpar o estado local
            if (window.progressMonitor) {
                window.progressMonitor.stopMonitoring(modelName);
            }
            this.downloadingModels.delete(modelName);
            delete this.downloadProgress[modelName];
            this.renderCurrentView();
            
            if (error.name === 'TimeoutError') {
                this.showWarning(`Timeout ao cancelar download de "${modelName}". O processo pode ter sido interrompido.`);
            } else {
                this.showWarning(`Erro na comunicação ao cancelar download de "${modelName}". O estado local foi limpo.`);
            }
        }
    }

    async removeModel(modelName) {
        if (!confirm(`Tem certeza que deseja remover o modelo "${modelName}"?\n\nIsso liberará espaço em disco mas você precisará instalar novamente se quiser usar.`)) {
            return;
        }
        
        try {
            const response = await fetch('/ai/api/models/remove', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ model_name: modelName })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess(`Modelo removido! Espaço liberado: ${data.space_freed}`);
                await this.refreshModelData();
            } else {
                if (data.error.includes('em uso por outro processo')) {
                    this.showError(`⚠️ Remoção parcial: ${data.error}\n\n💡 Dicas:\n• Feche o navegador e tente novamente\n• Reinicie o aplicativo\n• Alguns arquivos serão removidos automaticamente`);
                } else {
                    this.showError('Erro na remoção: ' + data.error);
                }
            }
        } catch (error) {
            console.error('Error removing model:', error);
            this.showError('Erro na remoção: ' + error.message);
        }
    }
    
    async cleanupCache() {
        if (!confirm('🧹 Limpar cache de modelos?\n\nIsso irá:\n• Remover arquivos temporários e incompletos\n• Remover arquivos de lock (.locks)\n• Liberar espaço em disco\n• Resolver problemas de remoção de modelos\n\nContinuar?')) {
            return;
        }
        
        try {
            const response = await fetch('/ai/api/models/cleanup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess(`✅ Cache limpo com sucesso!\n📁 ${data.cleaned_files} arquivos removidos\n💾 Espaço liberado: ${data.space_freed}`);
                await this.refreshModelData();
            } else {
                this.showError('Erro na limpeza: ' + data.error);
            }
        } catch (error) {
            console.error('Error cleaning cache:', error);
            this.showError('Erro na limpeza: ' + error.message);
        }
    }
    
    // ============ Hardware and Configuration Methods ============

    displayHardwareInfo() {
        console.log('🔄 Exibindo informações de hardware...', this.hardwareInfo);
        
        // CPU Info
        const cpuElement = document.getElementById('cpu-details');
        if (!cpuElement) {
            console.error('❌ Elemento cpu-details não encontrado!');
            return;
        }
        
        if (!this.hardwareInfo || !this.hardwareInfo.cpu) {
            cpuElement.innerHTML = '<span class="text-danger">Erro ao detectar CPU</span>';
        } else {
            const cpu = this.hardwareInfo.cpu;
            cpuElement.innerHTML = `
                <strong>${cpu.cores || 'N/A'} cores, ${cpu.threads || 'N/A'} threads</strong><br>
                <small class="text-muted">Performance IA: ${cpu.ai_performance || 'Desconhecida'}</small>
            `;
            console.log('✅ CPU info exibida');
        }
        
        // Memory Info
        const memoryElement = document.getElementById('memory-details');
        if (!memoryElement) {
            console.error('❌ Elemento memory-details não encontrado!');
            return;
        }
        
        if (!this.hardwareInfo || !this.hardwareInfo.memory) {
            memoryElement.innerHTML = '<span class="text-danger">Erro ao detectar memória</span>';
        } else {
            const memory = this.hardwareInfo.memory;
            memoryElement.innerHTML = `
                <strong>${memory.total_gb || 'N/A'} GB total</strong><br>
                <small class="text-muted">Performance IA: ${memory.ai_performance || 'Desconhecida'}</small>
            `;
            console.log('✅ Memory info exibida');
        }
        
        // GPU Info
        this.displayGPUInfo();
        
        // Show recommendations
        this.displayRecommendations();
    }
    
    displayHardwareError() {
        ['cpu-details', 'memory-details', 'gpu-details'].forEach(id => {
            document.getElementById(id).innerHTML = '<span class="text-danger">Erro na detecção</span>';
        });
    }
    
    displayRecommendations() {
        console.log('🔄 Exibindo recomendações...');
        
        const recommendationsSection = document.getElementById('recommendations-section');
        const recommendationsList = document.getElementById('recommendations-list');
        
        if (!recommendationsList) {
            console.error('❌ Elemento recommendations-list não encontrado!');
            return;
        }
        
        if (!this.hardwareInfo || !this.hardwareInfo.recommendations) {
            recommendationsList.innerHTML = '<div class="recommendation warning">Erro ao carregar recomendações</div>';
            if (recommendationsSection) recommendationsSection.style.display = 'block';
            return;
        }
        
        recommendationsList.innerHTML = '';
        
        this.hardwareInfo.recommendations.forEach(recommendation => {
            const div = document.createElement('div');
            
            // Determine recommendation type based on emoji/content
            let className = 'recommendation info';
            if (recommendation.includes('✅')) className = 'recommendation success';
            else if (recommendation.includes('⚠️') || recommendation.includes('🟡')) className = 'recommendation warning';
            
            div.className = className;
            div.textContent = recommendation;
            recommendationsList.appendChild(div);
        });
        
        if (recommendationsSection) recommendationsSection.style.display = 'block';
        console.log('✅ Recomendações exibidas:', this.hardwareInfo.recommendations.length);
    }
    
    displayModelsError() {
        const container = document.getElementById('models-grid');
        if (container) {
            container.innerHTML = `
                <div class="text-center text-danger py-4">
                    <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
                    <p>Erro ao carregar modelos</p>
                </div>
            `;
        }
    }
    
    validateConfiguration() {
        const form = document.getElementById('config-form');
        const formData = new FormData(form);
        const method = formData.get('processing_method');
        
        // Enable/disable start button based on selection
        const startButton = document.getElementById('btn-start-ai');
        startButton.disabled = !method;
        
        // Show warnings for specific configurations
        this.showConfigurationWarnings();
    }
    
    showConfigurationWarnings() {
        // Implementation can be added here for specific warnings
    }
    
    async saveConfiguration() {
        this.showLoading('Salvando configuração...', 'Aplicando novas configurações');
        
        try {
            console.log('🔄 Iniciando salvamento da configuração...');
            const config = this.collectConfiguration();
            
            console.log('📤 Enviando configuração para o servidor:', config);
            
            const response = await fetch('/ai/api/update-config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config)
            });
            
            const data = await response.json();
            console.log('📥 Resposta do servidor:', data);
            
            if (data.success) {
                console.log('✅ Configuração salva com sucesso!');
                this.showSuccess('Configuração salva com sucesso!');
                
                // Recarregar configuração do servidor para garantir sincronização
                console.log('🔄 Recarregando configuração do servidor...');
                await this.loadCurrentConfiguration();
                
                // Atualizar interface
                this.validateConfiguration();
                console.log('🔄 Interface atualizada com nova configuração');
            } else {
                throw new Error(data.error || 'Falha ao salvar configuração');
            }
        } catch (error) {
            console.error('❌ Erro ao salvar configuração:', error);
            this.showError('Erro ao salvar configuração: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    async startAI() {
        this.showLoading('Iniciando IA...', 'Carregando modelo e inicializando sistema');
        
        try {
            // Save configuration first
            await this.saveConfiguration();
            
            // Then start AI
            const response = await fetch('/ai/api/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('IA iniciada com sucesso!');
                await this.refreshStatus();
            } else {
                throw new Error(data.error || 'Falha ao iniciar IA');
            }
        } catch (error) {
            console.error('Error starting AI:', error);
            this.showError('Erro ao iniciar IA: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    async stopAI() {
        console.log('🛑 Iniciando parada da IA...');
        this.showLoading('Parando IA...', 'Liberando recursos do sistema');
        
        try {
            console.log('📡 Fazendo requisição para /ai/api/stop');
            const response = await fetch('/ai/api/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            console.log(`📡 Resposta recebida: ${response.status} ${response.statusText}`);
            const data = await response.json();
            console.log('📡 Dados da resposta:', data);
            
            if (data.success) {
                console.log('✅ IA parada com sucesso, atualizando interface...');
                this.showSuccess('IA parada com sucesso!');
                console.log('🔄 Atualizando status...');
                await this.refreshStatus();
                console.log('✅ Status atualizado com sucesso');
            } else {
                console.error('❌ Erro reportado pelo servidor:', data.error);
                throw new Error(data.error || 'Falha ao parar IA');
            }
        } catch (error) {
            console.error('❌ Erro durante parada da IA:', error);
            console.error('📋 Stack trace:', error.stack);
            this.showError('Erro ao parar IA: ' + error.message);
        } finally {
            this.hideLoading();
            console.log('🏁 Processo de parada finalizado');
        }
    }
    
    collectConfiguration() {
        try {
            console.log('🔄 Coletando configuração do formulário...');
            
            const form = document.getElementById('config-form');
            const formData = new FormData(form);
            
            // Get processing method
            const processingMethod = formData.get('processing_method');
            console.log('📋 Processing method coletado:', processingMethod);
            
            // Get selected model from selector
            const modelSelector = document.getElementById('model-selector');
            const selectedModel = modelSelector ? modelSelector.value : null;
            console.log('📋 Selected model coletado:', selectedModel);
            
            // Get advanced options
            const systemPrompt = document.getElementById('system-prompt')?.value || 'Você é um assistente útil e prestativo.';
            const requestTimeout = parseInt(document.getElementById('request-timeout')?.value) || 30;
            const enableContentFilter = document.getElementById('enable-content-filter')?.checked || false;
            const enableChatHistory = document.getElementById('enable-chat-history')?.checked || true;
            
            console.log('📋 Advanced options coletadas:', {
                systemPrompt: systemPrompt.substring(0, 50) + '...',
                requestTimeout,
                enableContentFilter,
                enableChatHistory
            });
            
            const config = {
                processing_method: processingMethod || 'cpu',
                selected_model: selectedModel || null,
                model_name: selectedModel || null, // Para compatibilidade
                max_tokens: parseInt(document.getElementById('max-tokens')?.value) || 2048,
                temperature: parseFloat(document.getElementById('temperature')?.value) || 0.7,
                system_prompt: systemPrompt,
                request_timeout: requestTimeout,
                safety_settings: {
                    enable_content_filter: enableContentFilter,
                    max_query_length: 2000,
                    medical_disclaimer: false
                },
                ui_settings: {
                    enable_chat_history: enableChatHistory,
                    show_in_sidebar: true,
                    max_history_items: 50
                },
                provider_change: true
            };
            
            console.log('✅ Configuração coletada:', config);
            return config;
            
        } catch (error) {
            console.error('❌ Erro ao coletar configuração:', error);
            return {
                processing_method: 'cpu',
                selected_model: null,
                model_name: null,
                max_tokens: 2048,
                temperature: 0.7,
                system_prompt: 'Você é um assistente útil e prestativo.',
                request_timeout: 30,
                safety_settings: {
                    enable_content_filter: false,
                    max_query_length: 2000,
                    medical_disclaimer: false
                },
                ui_settings: {
                    enable_chat_history: true,
                    show_in_sidebar: true,
                    max_history_items: 50
                },
                provider_change: true
            };
        }
    }
    
    async fetchWithTimeout(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.requestTimeout);
        
        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
           
            });
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('Requisição cancelada por timeout (15s)');
            }
            throw error;
        }
    }
    
    updateStatusDisplay(status) {
        console.log('🔄 Atualizando display de status:', status);
        
        const statusElement = document.getElementById('current-status');
        const startButton = document.getElementById('btn-start-ai');
        const stopButton = document.getElementById('btn-stop-ai');
        
        // Verificar se elementos existem
        if (!statusElement) {
            console.error('❌ Elemento current-status não encontrado');
            return;
        }
        if (!startButton) {
            console.error('❌ Botão start não encontrado');
            return;
        }
        if (!stopButton) {
            console.error('❌ Botão stop não encontrado');
            return;
        }
        
        if (status.initialized) {
            console.log('🟢 IA inicializada - mostrando como ativa');
            statusElement.textContent = 'Ativo';
            statusElement.className = 'status-indicator status-active';
            
            startButton.style.display = 'none';
            stopButton.style.display = 'inline-block';
        } else {
            console.log('🔴 IA não inicializada - mostrando como inativa');
            statusElement.textContent = 'Não Inicializado';
            statusElement.className = 'status-indicator status-inactive';
            
            startButton.style.display = 'inline-block';
            stopButton.style.display = 'none';
        }
        
        console.log('✅ Display de status atualizado com sucesso');
    }
    
    applyRecommendations() {
        // Não aplicar recomendações automaticamente
        // O usuário deve escolher manualmente o método de processamento
        console.log('💡 Recomendações disponíveis, mas não aplicadas automaticamente');
        
        // Apenas mostrar as recomendações para o usuário decidir
        if (this.hardwareInfo && this.hardwareInfo.gpu) {
            const recommendedBackend = this.hardwareInfo.gpu.recommended_backend;
            console.log(`💡 Backend recomendado: ${recommendedBackend}, mas mantendo escolha do usuário`);
        }
    }

    // ============ Dynamic GPU Detection ============
    
    async detectGPUOnDemand() {
        const loadingElement = document.createElement('div');
        loadingElement.className = 'gpu-detection-loading';
        loadingElement.innerHTML = `
            <div class="text-center p-3">
                <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                <span>Detectando GPUs disponíveis...</span>
            </div>
        `;
        
        const gpuCard = document.querySelector('.gpu-info-card');
        if (gpuCard) {
            gpuCard.appendChild(loadingElement);
            
            try {
                // Force fresh hardware detection
                const response = await fetch('/ai/api/hardware-info?refresh=true');
                const data = await response.json();
                
                if (data.success && data.hardware.gpu) {
                    this.hardwareInfo.gpu = data.hardware.gpu;
                    this.updateGPUDisplay();
                    this.updateProcessingMethodOptions();
                    
                    // Show detection results
                    this.showGPUDetectionResults(data.hardware.gpu);
                } else {
                    throw new Error(data.error || 'Falha na detecção de GPU');
                }
            } catch (error) {
                console.error('Error detecting GPU:', error);
                this.showError('Erro na detecção de GPU: ' + error.message);
            } finally {
                loadingElement.remove();
            }
        }
    }
    
    updateGPUDisplay() {
        const gpuElement = document.getElementById('gpu-details');
        if (!gpuElement) return;
        
        const { gpu } = this.hardwareInfo;
        const gpuTypes = [];
        
        if (gpu.nvidia && gpu.nvidia.available) {
            gpuTypes.push(`NVIDIA (${gpu.nvidia.devices.length} dispositivo(s))`);
        }
        if (gpu.amd && gpu.amd.available) {
            gpuTypes.push(`AMD (${gpu.amd.devices.length} dispositivo(s))`);
        }
        if (gpu.integrated && gpu.integrated.available) {
            gpuTypes.push(`Integrada (${gpu.integrated.devices.length} dispositivo(s))`);
        }
        
        if (gpuTypes.length > 0) {
            gpuElement.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${gpuTypes.join(', ')}</strong><br>
                        <small class="text-muted">Backend recomendado: ${gpu.recommended_backend}</small>
                    </div>
                    <button class="btn btn-sm btn-outline-primary" onclick="aiConfigManager.showGPUDetails()">
                        <i class="fas fa-info-circle"></i> Detalhes
                    </button>
                </div>
            `;
            document.getElementById('gpu-info').classList.remove('hardware-unavailable');
            document.getElementById('gpu-info').classList.add('hardware-available');
        } else {
            gpuElement.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <span class="text-muted">Nenhuma GPU dedicada detectada</span><br>
                        <small class="text-muted">Usar processamento por CPU</small>
                    </div>
                    <button class="btn btn-sm btn-outline-secondary" onclick="aiConfigManager.detectGPUOnDemand()">
                        <i class="fas fa-search"></i> Re-detectar
                    </button>
                </div>
            `;
            document.getElementById('gpu-info').classList.remove('hardware-available');
            document.getElementById('gpu-info').classList.add('hardware-unavailable');
        }
    }
    
    // GPU Info com detalhes expandidos
    displayGPUInfo() {
        console.log('🔄 Exibindo informações de GPU...');
        
        const gpuElement = document.getElementById('gpu-details');
        if (!gpuElement) {
            console.error('❌ Elemento gpu-details não encontrado!');
            return;
        }
        
        if (!this.hardwareInfo || !this.hardwareInfo.gpu) {
            gpuElement.innerHTML = '<span class="text-danger">Erro ao detectar GPU</span>';
            console.log('❌ GPU info não disponível');
            return;
        }
        
        const gpu = this.hardwareInfo.gpu;
        let gpuText = '';
        
        try {
            if (gpu.nvidia && gpu.nvidia.available) {
                const devices = this.formatDeviceList(gpu.nvidia.devices);
                gpuText = `<strong>NVIDIA GPU Detectada</strong><br><small>${devices}</small>`;
            } else if (gpu.amd && gpu.amd.available) {
                const devices = this.formatDeviceList(gpu.amd.devices);
                gpuText = `<strong>AMD GPU Detectada</strong><br><small>${devices}</small>`;
            } else if (gpu.integrated && gpu.integrated.available) {
                const devices = this.formatDeviceList(gpu.integrated.devices);
                gpuText = `<strong>GPU Integrada</strong><br><small>${devices}</small>`;
            } else {
                gpuText = '<span class="text-muted">Nenhuma GPU dedicada detectada</span>';
            }
        } catch (error) {
            console.error('❌ Erro ao formatar informações de GPU:', error);
            gpuText = '<span class="text-warning">Erro ao exibir detalhes da GPU</span>';
        }
        
        gpuElement.innerHTML = gpuText;
        console.log('✅ GPU info exibida:', gpuText);
    }
    
    formatDeviceList(devices) {
        if (!devices || !Array.isArray(devices)) {
            return 'Dispositivos não detectados';
        }
        
        try {
            // Clean up device names by removing large numbers (likely RAM amounts)
            const cleanedDevices = devices.map(device => {
                if (typeof device !== 'string') {
                    return 'Dispositivo desconhecido';
                }
                
                // Remove large numbers at the end (like RAM amounts)
                return device.replace(/\s+\d{8,}$/, '').trim();
            }).filter(device => device.length > 0);
            
            return cleanedDevices.length > 0 ? cleanedDevices.join(', ') : 'Nenhum dispositivo válido';
        } catch (error) {
            console.error('❌ Erro ao limpar lista de dispositivos:', error, devices);
            return 'Erro ao processar dispositivos';
        }
    }
    
    showGPUDetectionResults(gpuInfo) {
        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-microchip text-primary me-2"></i>
                            Detecção de GPU
                        </h5>
                        <button type="button" class="btn-close" onclick="this.closest('.modal').remove()"></button>
                    </div>
                    <div class="modal-body">
                        ${this.generateGPUDetailsHTML(gpuInfo)}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').remove()">Fechar</button>
                        <button type="button" class="btn btn-primary" onclick="aiConfigManager.applyGPUSettings(); this.closest('.modal').remove();">
                            Aplicar Configurações
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }
    
    generateGPUDetailsHTML(gpuInfo) {
        let html = '<div class="row">';
        
        // NVIDIA GPUs
        if (gpuInfo.nvidia && gpuInfo.nvidia.available) {
            html += `
                <div class="col-md-6 mb-3">
                    <div class="card border-success">
                        <div class="card-header bg-success text-white">
                            <i class="fab fa-nvidia me-2"></i>NVIDIA GPUs
                        </div>
                        <div class="card-body">
                            <ul class="list-unstyled">
                                ${gpuInfo.nvidia.devices.map(device => `<li><i class="fas fa-check text-success me-2"></i>${device}</li>`).join('')}
                            </ul>
                            <div class="alert alert-info mb-0">
                                <strong>Recomendação:</strong> Use backend CUDA para melhor performance
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // AMD GPUs
        if (gpuInfo.amd && gpuInfo.amd.available) {
            html += `
                <div class="col-md-6 mb-3">
                    <div class="card border-warning">
                        <div class="card-header bg-warning text-dark">
                            <i class="fab fa-amd me-2"></i>AMD GPUs
                        </div>
                        <div class="card-body">
                            <ul class="list-unstyled">
                                ${gpuInfo.amd.devices.map(device => `<li><i class="fas fa-check text-warning me-2"></i>${device}</li>`).join('')}
                            </ul>
                            <div class="alert alert-warning mb-0">
                                <strong>Recomendação:</strong> Use ROCm (Linux) ou DirectML (Windows)
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Integrated GPUs
        if (gpuInfo.integrated && gpuInfo.integrated.available) {
            html += `
                <div class="col-md-6 mb-3">
                    <div class="card border-info">
                        <div class="card-header bg-info text-white">
                            <i class="fas fa-microchip me-2"></i>GPU Integrada
                        </div>
                        <div class="card-body">
                            <ul class="list-unstyled">
                                ${gpuInfo.integrated.devices.map(device => `<li><i class="fas fa-info text-info me-2"></i>${device}</li>`).join('')}
                            </ul>
                            <div class="alert alert-info mb-0">
                                <strong>Nota:</strong> Performance limitada para IA
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // No GPU found
        if (!gpuInfo.nvidia?.available && !gpuInfo.amd?.available && !gpuInfo.integrated?.available) {
            html += `
                <div class="col-12">
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        <strong>Nenhuma GPU detectada</strong><br>
                        O sistema usará processamento por CPU. Considere usar um servidor externo para melhor performance.
                    </div>
                </div>
            `;
        }
        
        html += '</div>';
        return html;
    }
    
    showGPUDetails() {
        if (this.hardwareInfo && this.hardwareInfo.gpu) {
            this.showGPUDetectionResults(this.hardwareInfo.gpu);
        } else {
            this.detectGPUOnDemand();
        }
    }
    
    applyGPUSettings() {
        const { gpu } = this.hardwareInfo;
        if (!gpu) return;
        
        console.log('🔧 GPU Settings: Aplicando configurações sugeridas (não forçadas)');
        
        // Para AMD, não forçar ROCm - apenas sugerir
        if (gpu.amd?.available) {
            console.log('💡 GPU AMD detectada - ROCm disponível como opção avançada');
            
            // Verificar se usuário tem ROCm habilitado
            const rocmOption = document.getElementById('rocm-option');
            if (rocmOption && rocmOption.checked) {
                console.log('✅ Usuário escolheu ROCm - aplicando configuração');
                
                const deviceSelect = document.getElementById('device-selection');
                if (deviceSelect) {
                    deviceSelect.value = 'cuda'; // ROCm uses CUDA API
                    deviceSelect.dispatchEvent(new Event('change'));
                }
            } else {
                console.log('💻 Mantendo CPU como padrão para AMD (ROCm não selecionado)');
            }
        } else if (gpu.nvidia?.available) {
            // Para NVIDIA, pode aplicar CUDA automaticamente
            const processingMethodSelect = document.getElementById('processing-method');
            if (processingMethodSelect) {
                // Sugerir CUDA mas não forçar
                console.log('💡 GPU NVIDIA detectada - CUDA recomendado');
            }
            
            const deviceSelect = document.getElementById('device-selection');
            if (deviceSelect) {
                deviceSelect.value = 'cuda';
                deviceSelect.dispatchEvent(new Event('change'));
            }
        }
        
        this.showSuccess('Configurações de GPU aplicadas com sucesso!');
        
        // Close modal
        const modal = document.querySelector('.modal.show');
        if (modal) modal.remove();
    }
    
    updateProcessingMethodOptions() {
        const { gpu } = this.hardwareInfo;
        const processingMethodSelect = document.getElementById('processing-method');
        
        if (processingMethodSelect && gpu) {
            // Add GPU option if available
            if ((gpu.nvidia?.available || gpu.amd?.available) && !processingMethodSelect.querySelector('option[value="gpu"]')) {
                const gpuOption = document.createElement('option');
                gpuOption.value = 'gpu';
                gpuOption.textContent = `GPU (${gpu.recommended_backend.toUpperCase()})`;
                processingMethodSelect.appendChild(gpuOption);
            }
 }
    }

    // ============ Processing Method Change Handler ============

    handleProcessingMethodChange() {
        const processingMethod = document.getElementById('processing-method')?.value;
        
        if (processingMethod === 'local' || processingMethod === 'gpu') {
            // Show device selection and trigger GPU detection if needed
            const deviceSection = document.getElementById('device-selection-section');
            if (deviceSection) {
                deviceSection.style.display = 'block';
            }
            
            // If user selected GPU but we don't have reliable GPU info, trigger detection
            if (processingMethod === 'gpu' && (!this.hardwareInfo?.gpu || 
                (!this.hardwareInfo.gpu.nvidia?.available && !this.hardwareInfo.gpu.amd?.available))) {
                this.detectGPUOnDemand();
            }
        } else {
            // Hide device selection for other methods
            const deviceSection = document.getElementById('device-selection-section');
            if (deviceSection) {
                deviceSection.style.display = 'none';
            }
        }
    }

    async loadDiskUsage() {
        try {
            console.log('🔄 Carregando uso de disco...');
            const response = await this.fetchWithTimeout('/ai/api/disk-usage');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.diskUsage = {
                    total_space_gb: data.total_space_gb,
                    used_space_gb: data.used_space_gb,
                    free_space_gb: data.free_space_gb,
                    available_space_gb: data.available_space_gb,
                    total_size_gb: data.models_cache_size_gb,
                    total_size_mb: data.models_cache_size_mb,
                    models_count: data.models_count,
                    cache_path: data.cache_path
                };
                console.log('✅ Uso de disco carregado:', this.diskUsage);
                this.updateDiskUsageCard();
            } else {
                console.error('❌ Erro ao carregar uso de disco:', data.error);
                this.diskUsage = { error: data.error };
                this.updateDiskUsageCard();
                this.showWarning('Erro ao carregar informações de disco: ' + data.error);
            }
        } catch (error) {
            console.error('❌ Erro na requisição de uso de disco:', error);
            this.diskUsage = { error: error.message };
            this.updateDiskUsageCard();
            this.showError('Falha na conexão ao carregar uso de disco: ' + error.message);
        }
    }
    
    // ============ Loading Management ============
    
    showLoading(title = 'Carregando...', subtitle = '') {
        console.log('🔄 Mostrando loading:', title, subtitle);
        this.isLoading = true;
        
        let overlay = document.getElementById('loading-overlay');
        if (!overlay) {
            // Criar overlay se não existir
            overlay = document.createElement('div');
            overlay.id = 'loading-overlay';
            overlay.className = 'loading-overlay';
            overlay.innerHTML = `
                <div class="loading-content">
                    <div class="spinner-border text-primary mb-3" role="status">
                        <span class="visually-hidden">Carregando...</span>
                    </div>
                    <h5 class="loading-title">${title}</h5>
                    <p class="loading-subtitle text-muted">${subtitle}</p>
                </div>
            `;
            document.body.appendChild(overlay);
        } else {
            // Atualizar conteúdo existente
            const titleElement = overlay.querySelector('.loading-title');
            const subtitleElement = overlay.querySelector('.loading-subtitle');
            if (titleElement) titleElement.textContent = title;
            if (subtitleElement) subtitleElement.textContent = subtitle;
        }
        
        // Mostrar overlay
        overlay.classList.remove('hidden');
        overlay.style.display = 'flex';
    }
    
    hideLoading() {
        console.log('✅ Ocultando loading');
        this.isLoading = false;
        
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
            overlay.style.display = 'none';
        }
    }
    
    showError(message) {
        console.error('❌ Erro:', message);
        // Implementar notificação de erro (pode usar alert temporariamente)
        alert('Erro: ' + message);
    }
    
    showWarning(message) {
        console.warn('⚠️ Aviso:', message);
        // Implementar notificação de aviso (pode usar alert temporariamente)
        alert('Aviso: ' + message);
    }
    
    showSuccess(message) {
        console.log('✅ Sucesso:', message);
        // Implementar notificação de sucesso (pode usar alert temporariamente)
        alert('Sucesso: ' + message);
    }

}

// Instancia e exporta para uso global
const aiConfigManager = new AIConfigManager();
window.aiConfigManager = aiConfigManager;
