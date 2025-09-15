"""
Serviço simples para gerenciamento de progresso de download com HuggingFace Hub.
Implementação minimalista usando apenas dependências essenciais.
"""

import threading
import time
from typing import Any, Dict


class DownloadProgressManager:
    """Gerenciador simples de progresso de downloads."""

    def __init__(self):
        self.progress_data: Dict[str, Dict[str, Any]] = {}
        self.active_downloads: Dict[str, threading.Thread] = {}
        self.cancel_flags: Dict[str, bool] = {}
        self.cancel_events: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def start_download(self, model_name: str) -> bool:
        """Inicia o download de um modelo com monitoramento de progresso."""
        with self._lock:
            if model_name in self.active_downloads:
                return False

            self.cancel_flags[model_name] = False
            self.cancel_events[model_name] = threading.Event()
            self.progress_data[model_name] = {
                "status": "Iniciando download...",
                "progress": 0,
                "downloaded_bytes": 0,
                "total_bytes": 0,
                "downloading": True,
                "error": None,
                "timestamp": time.time(),
            }

            # Criar thread para download
            download_thread = threading.Thread(
                target=self._download_worker, args=(model_name,), daemon=True
            )

            self.active_downloads[model_name] = download_thread
            download_thread.start()

            return True

    def _download_worker(self, model_name: str):
        """Worker thread para executar o download com progresso."""
        try:
            import time

            from huggingface_hub import snapshot_download
            from tqdm.auto import tqdm

            # Função para atualizar progresso
            def update_progress(
                status: str, progress: int = 0, downloaded: int = 0, total: int = 0
            ):
                if (
                    self.cancel_flags.get(model_name, False)
                    or self.cancel_events.get(model_name, threading.Event()).is_set()
                ):
                    raise KeyboardInterrupt("Download cancelado")

                with self._lock:
                    self.progress_data[model_name].update(
                        {
                            "status": status,
                            "progress": progress,
                            "downloaded_bytes": downloaded,
                            "total_bytes": total,
                            "timestamp": time.time(),
                        }
                    )

            # Verificar cancelamento periodicamente
            def check_cancellation():
                if (
                    self.cancel_flags.get(model_name, False)
                    or self.cancel_events.get(model_name, threading.Event()).is_set()
                ):
                    raise KeyboardInterrupt("Download cancelado pelo usuário")

            # Criar diretório de cache
            import os

            cache_dir = "models_cache"
            os.makedirs(cache_dir, exist_ok=True)

            # Atualizar status inicial
            update_progress("Conectando ao HuggingFace Hub...", 5)

            # Verificar cancelamento antes de prosseguir
            check_cancellation()

            # Extrair repo_id e filename do model_name
            # Formato: "unsloth/gemma-3n-E4B-it-GGUF:gemma-3n-E4B-it-Q8_0.gguf"
            if ":" in model_name:
                repo_id, filename = model_name.split(":", 1)
            else:
                repo_id = model_name
                filename = None

            # Verificar cancelamento antes de iniciar download
            check_cancellation()

            # Classe tqdm personalizada para capturar progresso do snapshot_download
            class SnapshotProgressTqdm(tqdm):
                def __init__(self, *args, **kwargs):
                    # Configurar para mostrar progresso em bytes
                    kwargs["unit"] = "B"
                    kwargs["unit_scale"] = True
                    kwargs["unit_divisor"] = 1024

                    # Inicializar atributos personalizados ANTES do super().__init__
                    self.last_update = time.time()
                    self.is_closing = False

                    super().__init__(*args, **kwargs)

                def update(self, n=1):
                    # Verificar cancelamento apenas se não estiver fechando
                    if not self.is_closing:
                        check_cancellation()

                    super().update(n)
                    current_time = time.time()

                    # Atualizar a cada 0.5 segundos para não sobrecarregar
                    if current_time - self.last_update >= 0.5:
                        if self.total and self.total > 0:
                            progress_pct = min(100, (self.n / self.total) * 100)

                            # Formatar bytes para exibição
                            downloaded_mb = self.n / (1024 * 1024)
                            total_mb = self.total / (1024 * 1024)

                            # Atualizar progresso apenas se não estiver fechando
                            if not self.is_closing:
                                try:
                                    update_progress(
                                        f"Baixando... {progress_pct:.1f}% ({downloaded_mb:.1f}MB / {total_mb:.1f}MB)",
                                        int(progress_pct),
                                        self.n,
                                        self.total,
                                    )
                                except KeyboardInterrupt:
                                    # Se foi cancelado, marcar como fechando
                                    self.is_closing = True
                                    raise

                            self.last_update = current_time

                def refresh(self, *args, **kwargs):
                    # Verificar cancelamento apenas se não estiver fechando
                    if not self.is_closing:
                        check_cancellation()

                    # Capturar atualizações do refresh também
                    super().refresh(*args, **kwargs)
                    current_time = time.time()

                    # Atualizar se passou tempo suficiente
                    if hasattr(self, "last_update") and current_time - self.last_update >= 0.5:
                        if self.total and self.total > 0:
                            progress_pct = min(100, (self.n / self.total) * 100)

                            # Formatar bytes para exibição
                            downloaded_mb = self.n / (1024 * 1024)
                            total_mb = self.total / (1024 * 1024)

                            # Atualizar progresso apenas se não estiver fechando
                            if not self.is_closing:
                                try:
                                    update_progress(
                                        f"Baixando... {progress_pct:.1f}% ({downloaded_mb:.1f}MB / {total_mb:.1f}MB)",
                                        int(progress_pct),
                                        self.n,
                                        self.total,
                                    )
                                except KeyboardInterrupt:
                                    # Se foi cancelado, marcar como fechando
                                    self.is_closing = True
                                    raise

                            self.last_update = current_time

                def close(self):
                    # Marcar como fechando para evitar verificações de cancelamento
                    self.is_closing = True

                    # Callback final apenas se completou com sucesso
                    try:
                        if self.total and self.n >= self.total:
                            downloaded_mb = self.n / (1024 * 1024)
                            # Tentar atualizar progresso final, mas não falhar se cancelado
                            try:
                                update_progress(
                                    f"Finalizando download... ({downloaded_mb:.1f}MB)",
                                    95,
                                    self.n,
                                    self.total,
                                )
                            except KeyboardInterrupt:
                                # Se foi cancelado, apenas ignorar
                                pass
                    except Exception:
                        # Ignorar qualquer erro no close
                        pass
                    finally:
                        super().close()

            # Executar download com progresso usando tqdm_class
            if filename:
                # Download de arquivo específico
                local_path = snapshot_download(
                    repo_id=repo_id,
                    cache_dir=cache_dir,
                    local_files_only=False,
                    tqdm_class=SnapshotProgressTqdm,
                    allow_patterns=[filename],  # Baixar apenas o arquivo específico
                )
            else:
                # Download do repositório completo
                local_path = snapshot_download(
                    repo_id=repo_id,
                    cache_dir=cache_dir,
                    local_files_only=False,
                    tqdm_class=SnapshotProgressTqdm,
                )

            # Download concluído
            update_progress("Download concluído!", 100)

            with self._lock:
                self.progress_data[model_name].update(
                    {"downloading": False, "local_path": local_path}
                )

        except KeyboardInterrupt:
            # Download foi cancelado pelo usuário
            import time as time_module

            with self._lock:
                self.progress_data[model_name].update(
                    {
                        "status": "Download cancelado",
                        "downloading": False,
                        "error": "Cancelado pelo usuário",
                        "timestamp": time_module.time(),
                    }
                )
        except Exception as e:
            import time as time_module

            with self._lock:
                self.progress_data[model_name].update(
                    {
                        "status": f"Erro: {str(e)}",
                        "downloading": False,
                        "error": str(e),
                        "timestamp": time_module.time(),
                    }
                )

        finally:
            # Limpar thread ativa e eventos
            with self._lock:
                if model_name in self.active_downloads:
                    del self.active_downloads[model_name]
                if model_name in self.cancel_events:
                    del self.cancel_events[model_name]

    def cancel_download(self, model_name: str) -> bool:
        """Cancela o download de um modelo."""
        with self._lock:
            if model_name not in self.active_downloads:
                return False

            # Marcar para cancelamento
            self.cancel_flags[model_name] = True

            # Sinalizar evento de cancelamento
            if model_name in self.cancel_events:
                self.cancel_events[model_name].set()

            # Atualizar status
            if model_name in self.progress_data:
                self.progress_data[model_name].update(
                    {
                        "status": "Cancelando download...",
                        "downloading": False,
                        "error": "Cancelado pelo usuário",
                        "timestamp": time.time(),
                    }
                )

            return True

    def get_progress(self, model_name: str) -> Dict[str, Any]:
        """Obtém o progresso atual de um download."""
        with self._lock:
            return self.progress_data.get(
                model_name,
                {
                    "status": "Não iniciado",
                    "progress": 0,
                    "downloaded_bytes": 0,
                    "total_bytes": 0,
                    "downloading": False,
                    "error": None,
                    "timestamp": time.time(),
                },
            )

    def get_all_progress(self) -> Dict[str, Dict[str, Any]]:
        """Obtém o progresso de todos os downloads."""
        with self._lock:
            return self.progress_data.copy()

    def cleanup_completed(self, max_age_seconds: int = 3600) -> int:
        """Remove dados de progresso antigos para downloads concluídos."""
        current_time = time.time()
        cleaned_count = 0

        with self._lock:
            to_remove = []
            for model_name, data in self.progress_data.items():
                # Remover se não está baixando e é antigo
                if (
                    not data.get("downloading", False)
                    and current_time - data.get("timestamp", 0) > max_age_seconds
                ):
                    to_remove.append(model_name)

            for model_name in to_remove:
                del self.progress_data[model_name]
                if model_name in self.cancel_flags:
                    del self.cancel_flags[model_name]
                cleaned_count += 1

        return cleaned_count

    def is_downloading(self, model_name: str) -> bool:
        """Verifica se um modelo está sendo baixado."""
        with self._lock:
            return model_name in self.active_downloads and self.progress_data.get(
                model_name, {}
            ).get("downloading", False)


# Instância global do gerenciador
download_manager = DownloadProgressManager()
