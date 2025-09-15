/**
 * Monitor simples de progresso de download
 * Usa apenas JavaScript nativo sem dependências
 */

class ProgressMonitor {
    constructor() {
        this.activeMonitors = new Map();
        this.pollInterval = 1000; // 1 segundo
    }

    /**
     * Inicia o monitoramento de progresso para um modelo
     * @param {string} modelName - Nome do modelo
     * @param {Function} callback - Função callback para updates
     */
    startMonitoring(modelName, callback) {
        // Parar monitoramento anterior se existir
        this.stopMonitoring(modelName);

        // Criar novo monitor
        const monitor = {
            modelName,
            callback,
            intervalId: null,
            isActive: true
        };

        this.activeMonitors.set(modelName, monitor);

        // Iniciar polling
        this._startPolling(monitor);

        console.log(`📊 Monitoramento iniciado para: ${modelName}`);
    }

    /**
     * Para o monitoramento de um modelo específico
     * @param {string} modelName - Nome do modelo
     */
    stopMonitoring(modelName) {
        const monitor = this.activeMonitors.get(modelName);
        if (monitor) {
            monitor.isActive = false;
            if (monitor.intervalId) {
                clearInterval(monitor.intervalId);
            }
            this.activeMonitors.delete(modelName);
            console.log(`⏹️ Monitoramento parado para: ${modelName}`);
        }
    }

    /**
     * Para todos os monitoramentos ativos
     */
    stopAllMonitoring() {
        for (const [modelName] of this.activeMonitors) {
            this.stopMonitoring(modelName);
        }
    }

    /**
     * Inicia o polling para um monitor
     * @param {Object} monitor - Objeto monitor
     */
    _startPolling(monitor) {
        const poll = async () => {
            if (!monitor.isActive) return;

            try {
                const response = await fetch(`/ai/api/models/${encodeURIComponent(monitor.modelName)}/progress`);
                const data = await response.json();

                if (response.ok) {
                    monitor.callback(data);
                    
                    // Parar se download terminou
                    if (!data.downloading) {
                        this.stopMonitoring(monitor.modelName);
                        return;
                    }
                }
            } catch (error) {
                console.error('Erro no polling:', error);
            }
        };

        // Primeira execução imediata
        poll();

        // Configurar intervalo
        monitor.intervalId = setInterval(poll, this.pollInterval);
    }

    /**
     * Verifica se um modelo está sendo monitorado
     * @param {string} modelName - Nome do modelo
     * @returns {boolean}
     */
    isMonitoring(modelName) {
        return this.activeMonitors.has(modelName);
    }
}

// Instância global
window.progressMonitor = new ProgressMonitor();
