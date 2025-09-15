"""
Model Manager Service
Gerencia download, remoção e busca de modelos do Hugging Face
"""

import gc
import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

try:
    from huggingface_hub import HfApi, hf_hub_download, model_info, snapshot_download
    from huggingface_hub.errors import RepositoryNotFoundError, RevisionNotFoundError

    HUGGINGFACE_HUB_AVAILABLE = True
except ImportError:
    HUGGINGFACE_HUB_AVAILABLE = False
    HfApi = None
    hf_hub_download = None
    model_info = None
    snapshot_download = None
    RepositoryNotFoundError = Exception
    RevisionNotFoundError = Exception


class ModelManager:
    """
    Gerenciador de modelos de linguagem com integração ao Hugging Face
    """

    def __init__(self, cache_dir: str = "./models_cache/"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if HUGGINGFACE_HUB_AVAILABLE and HfApi is not None:
            self.api = HfApi()
        else:
            self.api = None

        # Sistema de progresso de download
        self.download_progress = {}

        # Sistema de cancelamento de downloads
        self.active_downloads = {}  # model_name -> {"process": subprocess, "thread": thread}

        # Filtros de modelos recomendados para aplicações médicas/odontológicas
        self.medical_keywords = [
            "medical",
            "bio",
            "clinical",
            "health",
            "medicina",
            "odonto",
            "dental",
            "saude",
            "clinica",
            "biomedical",
            "biomed",
        ]

        # Modelos populares e compatíveis
        self.recommended_models = [
            "microsoft/DialoGPT-small",
            "microsoft/DialoGPT-medium",
            "pierreguillou/gpt2-small-portuguese",
            "neuralmind/bert-base-portuguese-cased",
            "BioMistral/BioMistral-7B",
            "BioMistral/BioMistral-7B-AWQ-QGS128-W4-GEMV",
            "microsoft/BioGPT-Large",
            "allenai/scibert_scivocab_uncased",
        ]

    def is_available(self) -> bool:
        """Verifica se o gerenciador está disponível"""
        return HUGGINGFACE_HUB_AVAILABLE and REQUESTS_AVAILABLE

    def get_installed_models(self) -> List[Dict[str, Any]]:
        """Obtém lista de modelos instalados localmente"""
        models = []

        try:
            for item in self.cache_dir.iterdir():
                if item.is_dir() and item.name.startswith("models--"):
                    model_info = self._analyze_local_model(item)
                    if model_info:
                        models.append(model_info)
        except Exception as e:
            logger.error(f"Erro ao listar modelos instalados: {e}")

        return sorted(models, key=lambda x: x.get("name", ""))

    def _analyze_local_model(self, model_path: Path) -> Optional[Dict[str, Any]]:
        """Analisa um modelo local e extrai informações"""
        try:
            # Converter nome da pasta para nome do modelo
            model_name = model_path.name.replace("models--", "").replace("--", "/")

            # Calcular tamanho (ignorar arquivos corrompidos)
            total_size = 0
            file_count = 0
            actual_model_files = 0
            size_type = "actual"

            try:
                for file_path in model_path.rglob("*"):
                    if file_path.is_file():
                        try:
                            file_size = file_path.stat().st_size
                            total_size += file_size
                            file_count += 1

                            # Contar arquivos de modelo reais (não metadados)
                            if (
                                file_path.suffix.lower()
                                in [".gguf", ".bin", ".safetensors", ".pt", ".pth"]
                                or file_size > 1024 * 1024
                            ):  # Arquivos > 1MB são provavelmente modelos
                                actual_model_files += 1

                        except (OSError, PermissionError) as e:
                            logger.debug(f"Erro ao acessar arquivo {file_path}: {e}")
                            continue
            except Exception as e:
                logger.debug(f"Erro ao calcular tamanho de {model_path}: {e}")

            size_mb = round(total_size / (1024 * 1024), 1)
            size_gb = round(total_size / (1024 * 1024 * 1024), 2)

            # Detectar se o modelo está incompleto ou corrompido
            is_incomplete = False
            status_info = ""

            if total_size == 0:
                size_type = "unavailable"
                is_incomplete = True
                status_info = "Download incompleto ou corrompido"
            elif (
                actual_model_files == 0 and total_size < 10 * 1024 * 1024
            ):  # Menos de 10MB sem arquivos de modelo
                size_type = "incomplete"
                is_incomplete = True
                status_info = "Apenas metadados - download incompleto"
            elif actual_model_files == 0:
                size_type = "metadata_only"
                status_info = "Contém apenas metadados"

            # Tentar ler configuração do modelo (sem gerar erro se falhar)
            config_info = {}
            try:
                config_info = self._read_model_config(model_path)
            except Exception as e:
                logger.debug(f"Erro ao ler config de {model_name}: {e}")

            # Determinar tipo baseado no nome e configuração
            model_type = self._determine_model_type(model_name, config_info)

            # Melhor formatação do tamanho
            if total_size == 0:
                size_display = "Download incompleto"
            elif is_incomplete and actual_model_files == 0:
                size_display = f"{size_mb} MB (apenas metadados)"
            elif size_gb >= 1:
                size_display = f"{size_gb} GB"
            else:
                size_display = f"{size_mb} MB"

            return {
                "name": model_name,
                "display_name": model_name.split("/")[-1],
                "organization": (model_name.split("/")[0] if "/" in model_name else "local"),
                "path": str(model_path),
                "size_mb": size_mb,
                "size_gb": size_gb,
                "size_display": size_display,
                "size_type": size_type,
                "is_incomplete": is_incomplete,
                "status_info": status_info,
                "actual_model_files": actual_model_files,
                "type": model_type,
                "config": config_info,
                "installed": True,
                "can_remove": True,
                "file_count": file_count,
            }
        except Exception as e:
            logger.warning(f"Erro ao analisar modelo {model_path}: {e}")
            # Retornar informações básicas mesmo se houver erro
            try:
                model_name = model_path.name.replace("models--", "").replace("--", "/")
                return {
                    "name": model_name,
                    "display_name": model_name.split("/")[-1],
                    "organization": (model_name.split("/")[0] if "/" in model_name else "local"),
                    "path": str(model_path),
                    "size_mb": 0,
                    "size_gb": 0,
                    "size_display": "Tamanho desconhecido",
                    "type": "unknown",
                    "config": {},
                    "installed": True,
                    "can_remove": True,
                    "error": str(e),
                }
            except Exception:
                return None

    def _read_model_config(self, model_path: Path) -> Dict[str, Any]:
        """Lê configuração de um modelo local"""
        config = {}

        try:
            # Procurar config.json nos snapshots (ignorar .no_exist)
            for config_file in model_path.rglob("config.json"):
                # Ignorar arquivos na pasta .no_exist (contém configs vazios/corrompidos)
                if ".no_exist" in str(config_file):
                    logger.debug(f"Ignorando config em .no_exist: {config_file}")
                    continue

                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if not content:
                            logger.debug(f"Config vazio ignorado: {config_file}")
                            continue

                        config = json.loads(content)
                        logger.debug(f"Config lido com sucesso: {config_file}")
                        break
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.debug(f"Erro ao ler config {config_file}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Erro geral ao ler config de {model_path}: {e}")

        return config

    def _determine_model_type(self, model_name: str, config: Dict[str, Any]) -> str:
        """Determina o tipo do modelo baseado no nome e configuração"""
        name_lower = model_name.lower()

        # Verificar palavras-chave médicas
        if any(keyword in name_lower for keyword in self.medical_keywords):
            return "medical"

        # Verificar por arquitetura
        architectures = config.get("architectures", [])
        if architectures:
            arch = architectures[0].lower()
            if "gpt" in arch or "causal" in arch:
                return "conversational"
            elif "bert" in arch:
                return "language_model"

        # Verificar por nome específico
        if "dialog" in name_lower or "chat" in name_lower:
            return "conversational"
        elif "bert" in name_lower:
            return "language_model"
        elif "gpt" in name_lower:
            return "conversational"

        return "general"

    def search_huggingface_models(
        self, query: str = "", filter_type: str = "all", limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Busca modelos no Hugging Face Hub, incluindo variantes quantizadas de repositórios GGUF"""
        if not self.is_available():
            logger.warning("ModelManager not available for HF search")
            return []

        try:
            models = []

            # Se não há query, usar modelos recomendados
            if not query.strip():
                logger.info("No query provided, returning recommended models")
                models.extend(self._get_recommended_models())
            else:
                logger.info(
                    f"Searching HF Hub for: '{query}' with filter: '{filter_type}', limit: {limit}"
                )

                if not self.api:
                    logger.error("HuggingFace Hub not available")
                    return []

                try:
                    # Buscar no HF Hub com parâmetros otimizados
                    search_results = self.api.list_models(
                        search=query,
                        limit=max(limit, 50),  # Garantir pelo menos 50 resultados para filtrar
                        sort="downloads",
                        direction=-1,
                        library=["transformers", "gguf"],  # Incluir modelos GGUF também
                    )

                    logger.info(f"Found {len(list(search_results))} raw results from HF Hub")

                    # Recriar iterator para processar os resultados
                    search_results = self.api.list_models(
                        search=query,
                        limit=max(limit, 50),
                        sort="downloads",
                        direction=-1,
                        library=["transformers", "gguf"],
                    )

                    processed_count = 0
                    for model in search_results:
                        # Verificar se é um repositório GGUF que deve ter suas variantes listadas
                        model_name = model.id
                        is_gguf_repo = self._is_gguf_repository(model)

                        if is_gguf_repo:
                            # Para repositórios GGUF, listar todas as variantes quantizadas
                            logger.info(
                                f"Found GGUF repository: {model_name}, fetching variants..."
                            )
                            gguf_variants = self._get_gguf_variants(model_name)

                            for variant in gguf_variants:
                                if self._filter_model(variant, filter_type):
                                    models.append(variant)
                                    processed_count += 1

                                    # Parar quando tivermos modelos suficientes
                                    if len(models) >= limit:
                                        break
                        else:
                            # Para modelos normais, processar como antes
                            model_info = self._format_huggingface_model(model)
                            if model_info:
                                if self._filter_model(model_info, filter_type):
                                    models.append(model_info)
                                    processed_count += 1

                                    # Parar quando tivermos modelos suficientes
                                    if len(models) >= limit:
                                        break

                        # Parar quando tivermos modelos suficientes
                        if len(models) >= limit:
                            break

                    logger.info(
                        f"Processed {processed_count} models, returning {len(models)} results"
                    )

                except Exception as search_error:
                    logger.error(f"Error during HF search: {search_error}")
                    # Fallback para modelos recomendados se a busca falhar
                    if query.lower() in ["bio", "medical", "mistral", "biomistral"]:
                        logger.info("Falling back to recommended medical models")
                        models.extend(
                            [
                                m
                                for m in self._get_recommended_models()
                                if query.lower() in m.get("name", "").lower()
                            ]
                        )

            return models[:limit]

        except Exception as e:
            logger.error(f"Erro ao buscar modelos no HF: {e}")
            return []

    def _get_recommended_models(self) -> List[Dict[str, Any]]:
        """Retorna modelos recomendados com informações básicas"""
        models = []

        for model_name in self.recommended_models:
            try:
                # Verificar se já está instalado
                installed = self._is_model_installed(model_name)

                # Tentar obter tamanho real
                size_info = self._get_model_size(model_name)

                models.append(
                    {
                        "name": model_name,
                        "display_name": model_name.split("/")[-1],
                        "organization": model_name.split("/")[0],
                        "description": f"Modelo recomendado: {model_name}",
                        "type": "recommended",
                        "installed": installed,
                        "can_download": not installed,
                        "downloads": "N/A",
                        "size_estimate": size_info["formatted"],
                        "size_bytes": size_info["bytes"],
                        "size_type": size_info["type"],
                        "last_modified": None,
                        "created_at": None,
                        "file_count": size_info.get("file_count", 0),
                    }
                )
            except Exception as e:
                logger.error(f"Erro ao processar modelo recomendado {model_name}: {e}")

        return models

    def _format_huggingface_model(self, model) -> Optional[Dict[str, Any]]:
        """Formata informações de um modelo do HF Hub"""
        try:
            model_name = model.id  # Corrigido: usar model.id em vez de model.modelId
            installed = self._is_model_installed(model_name)

            # Extrair descrição de forma segura
            description = model_name
            if hasattr(model, "card_data") and model.card_data:
                description = model.card_data.get("title", model_name)

            # Obter tamanho do modelo de forma mais precisa
            size_info = self._get_model_size(model_name)

            # Formatação da data de modificação
            last_modified = None
            if hasattr(model, "last_modified") and model.last_modified:
                last_modified = model.last_modified

            return {
                "name": model_name,
                "display_name": model_name.split("/")[-1],
                "organization": model_name.split("/")[0] if "/" in model_name else "",
                "description": description,
                "type": self._classify_model_type(model_name),
                "installed": installed,
                "can_download": not installed,
                "downloads": getattr(model, "downloads", 0),
                "size_estimate": size_info["formatted"],
                "size_bytes": size_info["bytes"],
                "size_type": size_info["type"],  # "actual", "unknown", "error", "unavailable"
                "last_modified": last_modified,
                "created_at": getattr(model, "created_at", None),
                "file_count": size_info.get("file_count", 0),
            }
        except Exception as e:
            logger.error(f"Erro ao formatar modelo {model}: {e}")
            return None

    def _classify_model_type(self, model_name: str) -> str:
        """Classifica tipo do modelo baseado no nome"""
        name_lower = model_name.lower()

        if any(keyword in name_lower for keyword in self.medical_keywords):
            return "medical"
        elif "dialog" in name_lower or "chat" in name_lower:
            return "conversational"
        elif "bert" in name_lower:
            return "language_model"
        elif "gpt" in name_lower:
            return "conversational"
        else:
            return "general"

    def _filter_model(self, model_info: Dict[str, Any], filter_type: str) -> bool:
        """Filtra modelos baseado no tipo"""
        if filter_type == "all":
            return True
        return model_info.get("type") == filter_type

    def _is_model_installed(self, model_name: str) -> bool:
        """Verifica se um modelo está instalado"""
        model_path = self.cache_dir / f"models--{model_name.replace('/', '--')}"
        return model_path.exists()

    def download_model(self, model_name: str, progress_callback=None) -> Dict[str, Any]:
        """Baixa um modelo do Hugging Face com progresso, incluindo variantes GGUF específicas"""
        if not self.is_available():
            return {"success": False, "error": "Hugging Face Hub não disponível"}

        # Verificar se é uma variante GGUF específica (formato: model_name:file_name)
        is_gguf_variant = ":" in model_name
        if is_gguf_variant:
            base_model_name, file_name = model_name.split(":", 1)
            display_name = f"{base_model_name} ({file_name})"

            if self._is_gguf_variant_installed(base_model_name, file_name):
                return {
                    "success": False,
                    "error": f"Variante GGUF {display_name} já está instalada",
                }
        else:
            base_model_name = model_name
            file_name = None
            display_name = model_name

            if self._is_model_installed(model_name):
                return {"success": False, "error": "Modelo já está instalado"}

        try:
            logger.info(f"Iniciando download: {display_name}")

            # Verificar espaço em disco
            disk_space = self._get_available_disk_space()
            if disk_space < 1024 * 1024 * 1024:  # 1GB mínimo
                return {
                    "success": False,
                    "error": "Espaço em disco insuficiente (mínimo 1GB)",
                }

            # Inicializar progresso
            self._update_download_progress(model_name, 0, "Iniciando download...")

            # Callback de progresso
            if progress_callback:
                progress_callback(0, "Iniciando download...")

            # Download com progresso customizado
            try:
                if is_gguf_variant:
                    local_path = self._download_gguf_variant(
                        base_model_name, file_name, progress_callback
                    )
                else:
                    local_path = self._download_with_progress(model_name, progress_callback)

                # Não atualizar progresso aqui - já foi feito nos métodos específicos
                logger.info(f"{display_name} baixado com sucesso em {local_path}")

                # Limpar progresso após sucesso
                self._clear_download_progress(model_name)

                return {
                    "success": True,
                    "message": f"{display_name} baixado com sucesso",
                    "path": local_path,
                }

            except Exception as download_error:
                self._clear_download_progress(model_name)
                raise download_error

        except RepositoryNotFoundError:
            self._clear_download_progress(model_name)
            return {
                "success": False,
                "error": f"Modelo {base_model_name} não encontrado no Hugging Face",
            }
        except RevisionNotFoundError:
            self._clear_download_progress(model_name)
            return {
                "success": False,
                "error": f"Versão do modelo {base_model_name} não encontrada",
            }
        except Exception as e:
            self._clear_download_progress(model_name)
            logger.error(f"Erro ao baixar {display_name}: {e}")
            return {"success": False, "error": f"Erro no download: {str(e)}"}

    def _download_with_progress(self, model_name: str, progress_callback=None) -> str:
        """Download com progresso usando callback nativo do HuggingFace Hub"""
        if not snapshot_download:
            raise RuntimeError("HuggingFace Hub not available")

        try:
            from .download_progress import download_manager

            logger.info(f"Iniciando download com progresso nativo: {model_name}")

            # Inicializar progresso
            self._update_download_progress(model_name, 5, "Iniciando download...")
            if progress_callback:
                progress_callback(5, "Iniciando download...")

            # Callback para sincronizar com o sistema antigo
            def sync_progress_callback(progress_info):
                """Sincroniza progresso com o sistema antigo para compatibilidade"""
                progress_pct = progress_info.get("progress", 0)
                status = progress_info.get("status", "Baixando...")

                # Atualizar sistema antigo
                self._update_download_progress(
                    model_name,
                    progress_pct,
                    status,
                    downloaded_bytes=progress_info.get("downloaded_bytes", 0),
                    total_bytes=progress_info.get("total_bytes", 0),
                    speed=progress_info.get("speed", 0),
                    eta=progress_info.get("eta", 0),
                )

                # Chamar callback externo se fornecido
                if progress_callback:
                    progress_callback(progress_pct, status)

            # Iniciar download usando o novo sistema
            success = download_manager.start_download(model_name, sync_progress_callback)

            if not success:
                raise Exception("Falha ao iniciar download - já em andamento")

            # Aguardar conclusão do download
            while download_manager.is_downloading(model_name):
                time.sleep(0.5)

                # Verificar se foi cancelado
                if self._is_download_cancelled(model_name):
                    download_manager.cancel_download(model_name)
                    raise Exception("Download cancelado pelo usuário")

            # Verificar resultado final
            final_progress = download_manager.get_progress(model_name)

            if final_progress.get("error"):
                raise Exception(f"Erro no download: {final_progress['error']}")

            local_path = final_progress.get("local_path")
            if not local_path:
                # Fallback para download simples
                logger.warning("Caminho local não encontrado, fazendo fallback")
                local_path = snapshot_download(
                    repo_id=model_name, cache_dir=str(self.cache_dir), local_files_only=False
                )

            logger.info(f"Download concluído: {model_name}")
            return local_path

        except Exception as e:
            logger.error(f"Erro no download: {e}")
            raise

    def _download_gguf_variant(
        self, model_name: str, file_name: str, progress_callback=None
    ) -> str:
        """Download de uma variante GGUF específica com progresso real"""
        if not hf_hub_download:
            raise RuntimeError("HuggingFace Hub not available")

        try:
            logger.info(f"Downloading GGUF variant: {model_name}/{file_name}")

            # Usar o nome completo para progresso
            full_model_name = f"{model_name}:{file_name}"

            import time
            from datetime import timedelta

            # Inicializar progresso
            self._update_download_progress(
                full_model_name, 1, f"Preparando download de {file_name}..."
            )
            if progress_callback:
                progress_callback(1, f"Preparando download de {file_name}...")

            # Tentar interceptar progresso com tqdm para GGUF
            try:
                import tqdm

                logger.info(f"Iniciando download GGUF com monitoramento: {file_name}")

                start_time = time.time()
                original_tqdm = tqdm.tqdm

                def gguf_tqdm(*args, **kwargs):
                    """tqdm personalizado para downloads GGUF"""
                    pbar = original_tqdm(*args, **kwargs)

                    if hasattr(pbar, "total") and pbar.total and pbar.total > 0:
                        original_update = pbar.update

                        def update_wrapper(n=1):
                            result = original_update(n)

                            # Capturar progresso real do arquivo GGUF
                            if pbar.total > 0:
                                downloaded = pbar.n
                                total = pbar.total
                                progress = int((downloaded / total) * 100)

                                # Calcular velocidade real
                                current_time = time.time()
                                elapsed = current_time - start_time
                                speed = downloaded / elapsed if elapsed > 0 else 0

                                # ETA
                                remaining = total - downloaded
                                eta = remaining / speed if speed > 0 else 0

                                # Formatar informações
                                downloaded_mb = downloaded / (1024 * 1024)
                                total_mb = total / (1024 * 1024)
                                speed_mb = speed / (1024 * 1024)

                                if eta > 0:
                                    eta_str = str(timedelta(seconds=int(eta)))
                                    status = (
                                        f"Baixando {file_name}: "
                                        f"{downloaded_mb:.1f}/{total_mb:.1f} MB "
                                        f"({speed_mb:.1f} MB/s, ETA: {eta_str})"
                                    )
                                else:
                                    status = (
                                        f"Baixando {file_name}: "
                                        f"{downloaded_mb:.1f}/{total_mb:.1f} MB "
                                        f"({speed_mb:.1f} MB/s)"
                                    )

                                # Ajustar progresso para dar espaço para finalização
                                adjusted_progress = max(5, min(95, progress))

                                self._update_download_progress(
                                    full_model_name,
                                    adjusted_progress,
                                    status,
                                    downloaded_bytes=downloaded,
                                    total_bytes=total,
                                    speed=speed,
                                    eta=int(eta),
                                )

                                if progress_callback:
                                    progress_callback(adjusted_progress, status)

                            return result

                        pbar.update = update_wrapper  # type: ignore[attr-defined]

                    return pbar

                # Substituir tqdm
                tqdm.tqdm = gguf_tqdm

                try:
                    # Download do arquivo específico com progresso real
                    local_path = hf_hub_download(
                        repo_id=model_name,
                        filename=file_name,
                        cache_dir=str(self.cache_dir),
                        local_files_only=False,
                        resume_download=True,
                    )
                finally:
                    # Restaurar tqdm
                    tqdm.tqdm = original_tqdm

            except ImportError:
                # Fallback sem tqdm - download direto
                logger.info("tqdm não disponível, usando download direto")

                self._update_download_progress(full_model_name, 10, f"Baixando {file_name}...")
                if progress_callback:
                    progress_callback(10, f"Baixando {file_name}...")

                # Download do arquivo
                local_path = hf_hub_download(
                    repo_id=model_name,
                    filename=file_name,
                    cache_dir=str(self.cache_dir),
                    local_files_only=False,
                    resume_download=True,
                )

            # Progresso final
            self._update_download_progress(full_model_name, 100, "Download concluído!", eta=0)
            if progress_callback:
                progress_callback(100, "Download concluído!")

            logger.info(f"GGUF variant downloaded to: {local_path}")
            return local_path

        except Exception as e:
            logger.error(f"Error downloading GGUF variant {model_name}/{file_name}: {e}")
            raise

    def remove_model(self, model_name: str) -> Dict[str, Any]:
        """Remove um modelo instalado"""
        try:
            logger.info(f"Iniciando remoção do modelo: {model_name}")

            model_path = self.cache_dir / f"models--{model_name.replace('/', '--')}"

            if not model_path.exists():
                logger.warning(f"Modelo {model_name} não encontrado em {model_path}")
                return {"success": False, "error": "Modelo não está instalado"}

            # Calcular espaço que será liberado
            size_bytes = sum(f.stat().st_size for f in model_path.rglob("*") if f.is_file())
            size_mb = round(size_bytes / (1024 * 1024), 1)

            # Tentar remover com várias estratégias
            success = self._remove_model_directory(model_path)

            if success:
                logger.info(f"Modelo {model_name} removido. Espaço liberado: {size_mb} MB")
                return {
                    "success": True,
                    "message": f"Modelo {model_name} removido com sucesso",
                    "space_freed": f"{size_mb} MB",
                }
            else:
                return {
                    "success": False,
                    "error": "Não foi possível remover completamente o modelo. Alguns arquivos podem estar em uso por outro processo.",
                }

        except Exception as e:
            logger.error(f"Erro ao remover modelo {model_name}: {e}")
            return {"success": False, "error": f"Erro ao remover: {str(e)}"}

    def get_model_details(self, model_name: str) -> Dict[str, Any]:
        """Obtém detalhes completos de um modelo"""
        try:
            # Verificar se está instalado localmente
            if self._is_model_installed(model_name):
                model_path = self.cache_dir / f"models--{model_name.replace('/', '--')}"
                local_info = self._analyze_local_model(model_path)
                if local_info:
                    local_info["source"] = "local"
                    return local_info

            # Buscar informações no HF Hub
            if self.is_available() and model_info is not None:
                info = model_info(model_name)
                return {
                    "name": model_name,
                    "display_name": model_name.split("/")[-1],
                    "organization": model_name.split("/")[0],
                    "description": (
                        getattr(info, "cardData", {}).get("title", model_name)
                        if hasattr(info, "cardData")
                        else model_name
                    ),
                    "type": self._classify_model_type(model_name),
                    "downloads": getattr(info, "downloads", 0),
                    "last_modified": getattr(info, "lastModified", None),
                    "installed": False,
                    "source": "huggingface",
                }

            return {"error": "Modelo não encontrado"}

        except Exception as e:
            logger.error(f"Erro ao obter detalhes do modelo {model_name}: {e}")
            return {"error": str(e)}

    def get_disk_usage(self) -> Dict[str, Any]:
        """Obtém informações de uso de disco"""
        try:
            total_size = sum(f.stat().st_size for f in self.cache_dir.rglob("*") if f.is_file())
            model_count = len(
                [
                    d
                    for d in self.cache_dir.iterdir()
                    if d.is_dir() and d.name.startswith("models--")
                ]
            )
            available_space = self._get_available_disk_space()

            return {
                "cache_dir": str(self.cache_dir),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 1),
                "total_size_gb": round(total_size / (1024 * 1024 * 1024), 2),
                "model_count": model_count,
                "available_space_bytes": available_space,
                "available_space_gb": round(available_space / (1024 * 1024 * 1024), 1),
            }
        except Exception as e:
            logger.error(f"Erro ao obter uso de disco: {e}")
            return {"error": str(e)}

    def _get_available_disk_space(self) -> int:
        """Obtém espaço disponível em disco"""
        try:
            if os.name == "nt":  # Windows
                import ctypes

                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(str(self.cache_dir)),
                    ctypes.pointer(free_bytes),
                    None,
                    None,
                )
                return free_bytes.value
            else:  # Unix/Linux
                statvfs = os.statvfs(str(self.cache_dir))
                return statvfs.f_frsize * statvfs.f_bavail
        except Exception:
            return 0

    def cleanup_cache(self) -> Dict[str, Any]:
        """Limpa arquivos temporários e locks"""
        try:
            cleaned_files = 0
            cleaned_size = 0

            # Limpar pasta .locks
            locks_dir = self.cache_dir / ".locks"
            if locks_dir.exists():
                for lock_file in locks_dir.rglob("*"):
                    if lock_file.is_file():
                        cleaned_size += lock_file.stat().st_size
                        lock_file.unlink()
                        cleaned_files += 1

            return {
                "success": True,
                "cleaned_files": cleaned_files,
                "cleaned_size_mb": round(cleaned_size / (1024 * 1024), 2),
            }

        except Exception as e:
            logger.error(f"Erro na limpeza de cache: {e}")
            return {"success": False, "error": str(e)}

    def cleanup_incomplete_downloads(self) -> Dict[str, Any]:
        """Remove arquivos incompletos ou corrompidos de downloads"""
        try:
            cleaned_files = []
            cleaned_size = 0

            for model_dir in self.cache_dir.glob("models--*"):
                if model_dir.is_dir():
                    # Procurar arquivos .incomplete
                    for incomplete_file in model_dir.rglob("*.incomplete"):
                        try:
                            size = incomplete_file.stat().st_size
                            incomplete_file.unlink()
                            cleaned_files.append(incomplete_file.name)
                            cleaned_size += size
                            logger.info(f"Arquivo incompleto removido: {incomplete_file}")
                        except Exception as e:
                            logger.warning(f"Não foi possível remover {incomplete_file}: {e}")

                    # Procurar arquivos .lock
                    for lock_file in model_dir.rglob("*.lock"):
                        try:
                            if lock_file.exists():
                                lock_file.unlink()
                                cleaned_files.append(lock_file.name)
                                logger.info(f"Arquivo de lock removido: {lock_file}")
                        except Exception as e:
                            logger.warning(f"Não foi possível remover lock {lock_file}: {e}")

            size_mb = round(cleaned_size / (1024 * 1024), 1)

            return {
                "success": True,
                "cleaned_files": len(cleaned_files),
                "space_freed": f"{size_mb} MB",
                "message": f"Limpeza concluída: {len(cleaned_files)} arquivos removidos",
            }

        except Exception as e:
            logger.error(f"Erro na limpeza de arquivos incompletos: {e}")
            return {"success": False, "error": str(e)}

    def _remove_model_directory(self, model_path: Path) -> bool:
        """Remove diretório do modelo com várias estratégias"""
        try:
            # Primeira tentativa: remoção simples
            logger.info(f"Tentativa 1: Removendo diretório {model_path}")
            shutil.rmtree(model_path)
            return True
        except OSError as e:
            logger.warning(f"Tentativa 1 falhou: {e}")

        try:
            # Segunda tentativa: aguardar e tentar novamente
            logger.info("Tentativa 2: Aguardando 2 segundos e tentando novamente")
            time.sleep(2)
            gc.collect()  # Forçar garbage collection
            shutil.rmtree(model_path)
            return True
        except OSError as e:
            logger.warning(f"Tentativa 2 falhou: {e}")

        try:
            # Terceira tentativa: remover arquivos individualmente
            logger.info("Tentativa 3: Removendo arquivos individualmente")
            removed_count = 0
            total_count = 0

            for root, dirs, files in os.walk(model_path, topdown=False):
                for file in files:
                    total_count += 1
                    file_path = os.path.join(root, file)
                    try:
                        # Tentar remover atributo readonly se houver
                        os.chmod(file_path, 0o777)
                        os.remove(file_path)
                        removed_count += 1
                    except OSError as file_error:
                        logger.warning(
                            f"Não foi possível remover arquivo {file_path}: {file_error}"
                        )

                # Tentar remover diretórios vazios
                for dir in dirs:
                    dir_path = os.path.join(root, dir)
                    try:
                        os.rmdir(dir_path)
                    except OSError:
                        pass

            # Tentar remover o diretório principal
            try:
                os.rmdir(model_path)
                logger.info(
                    f"Remoção parcial concluída: {removed_count}/{total_count} arquivos removidos"
                )
                return removed_count > 0
            except OSError:
                logger.info(
                    f"Remoção parcial concluída: {removed_count}/{total_count} arquivos removidos, diretório principal não pôde ser removido"
                )
                return removed_count > 0

        except Exception as e:
            logger.error(f"Tentativa 3 falhou: {e}")

        # Quarta tentativa: usar comando del do Windows
        try:
            if os.name == "nt":  # Windows
                logger.info("Tentativa 4: Usando comando do sistema para remoção forçada")
                import subprocess

                result = subprocess.run(
                    ["rmdir", "/s", "/q", str(model_path)],
                    capture_output=True,
                    text=True,
                    shell=True,
                )
                if result.returncode == 0:
                    return True
                else:
                    logger.warning(f"Comando rmdir falhou: {result.stderr}")
        except Exception as e:
            logger.warning(f"Tentativa 4 falhou: {e}")

        return False

    def _format_size(self, size_bytes: int) -> str:
        """Formata tamanho em bytes para formato legível"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _extract_params_info(self, model_info) -> Optional[Dict[str, Any]]:
        """Extrai informações de parâmetros do modelo do HuggingFace"""
        try:
            # Verificar se há informações de card_data com parâmetros
            if hasattr(model_info, "card_data") and model_info.card_data:
                card_data = model_info.card_data

                # Procurar por diferentes campos que podem conter informação de parâmetros
                param_fields = ["model_size", "parameters", "params", "model_parameters"]

                for field in param_fields:
                    if field in card_data and card_data[field]:
                        param_value = card_data[field]

                        # Tentar converter para número se for string
                        if isinstance(param_value, str):
                            size_bytes = self._parse_param_string(param_value)
                            if size_bytes > 0:
                                return {
                                    "bytes": size_bytes,
                                    "formatted": self._format_size(size_bytes),
                                    "type": "actual",
                                    "source": f"params ({field})",
                                }
                        elif isinstance(param_value, (int, float)):
                            # Assumir que está em milhões de parâmetros
                            # Aproximadamente 4 bytes por parâmetro (float32)
                            size_bytes = int(param_value * 1_000_000 * 4)
                            return {
                                "bytes": size_bytes,
                                "formatted": self._format_size(size_bytes),
                                "type": "actual",
                                "source": f"params ({param_value}M)",
                            }

                # Verificar em tags também
                if "tags" in card_data and isinstance(card_data["tags"], list):
                    for tag in card_data["tags"]:
                        if isinstance(tag, str) and any(
                            keyword in tag.lower() for keyword in ["param", "size", "b", "m"]
                        ):
                            size_bytes = self._parse_param_string(tag)
                            if size_bytes > 0:
                                return {
                                    "bytes": size_bytes,
                                    "formatted": self._format_size(size_bytes),
                                    "type": "actual",
                                    "source": f"tag ({tag})",
                                }

            # Verificar nas tags diretas do modelo
            if hasattr(model_info, "tags") and model_info.tags:
                for tag in model_info.tags:
                    if isinstance(tag, str):
                        size_bytes = self._parse_param_string(tag)
                        if size_bytes > 0:
                            return {
                                "bytes": size_bytes,
                                "formatted": self._format_size(size_bytes),
                                "type": "actual",
                                "source": f"model_tag ({tag})",
                            }

            return None

        except Exception as e:
            logger.warning(f"Erro ao extrair informações de parâmetros: {e}")
            return None

    def _parse_param_string(self, param_str: str) -> int:
        """Converte string de parâmetros para bytes estimados"""
        try:
            param_str = param_str.lower().strip()

            # Padrões comuns: "7b", "13b", "70b", "1.3b", "110m", etc.
            import re

            # Procurar por padrões como "7b", "1.5b", "110m", etc.
            patterns = [
                r"(\d+\.?\d*)\s*b(?:illion)?",  # 7b, 1.5b, etc.
                r"(\d+\.?\d*)\s*m(?:illion)?",  # 110m, 1.5m, etc.
                r"(\d+\.?\d*)\s*k(?:ilo)?",  # 500k, etc.
                r"(\d+\.?\d*)\s*params?",  # 7params, etc.
            ]

            for pattern in patterns:
                match = re.search(pattern, param_str)
                if match:
                    number = float(match.group(1))

                    if "b" in pattern:  # Bilhões
                        # Bilhões de parâmetros * 4 bytes por parâmetro
                        return int(number * 1_000_000_000 * 4)
                    elif "m" in pattern:  # Milhões
                        return int(number * 1_000_000 * 4)
                    elif "k" in pattern:  # Milhares
                        return int(number * 1_000 * 4)
                    else:  # params direto
                        return int(number * 4)

            return 0

        except Exception as e:
            logger.warning(f"Erro ao parsear string de parâmetros '{param_str}': {e}")
            return 0

    def _get_model_size(self, model_name: str) -> Dict[str, Any]:
        """Obtém o tamanho do modelo do HF Hub de forma mais precisa"""
        try:
            if not self.is_available() or not model_info:
                return {"formatted": "Não disponível", "bytes": 0, "type": "unavailable"}

            # Tentar obter informações do modelo
            info = model_info(model_name)

            # Primeiro, tentar obter informações de parâmetros se disponível
            params_info = self._extract_params_info(info)
            if params_info:
                return params_info

            # Fallback: calcular tamanho pelos arquivos
            if hasattr(info, "siblings") and info.siblings:
                total_size = 0
                file_count = 0

                for sibling in info.siblings:
                    if hasattr(sibling, "size") and sibling.size:
                        total_size += sibling.size
                        file_count += 1

                if total_size > 0:
                    return {
                        "bytes": total_size,
                        "formatted": self._format_size(total_size),
                        "type": "actual",
                        "file_count": file_count,
                    }

            # Se não conseguir obter tamanho real, indicar claramente
            return {"formatted": "Tamanho não informado", "bytes": 0, "type": "unknown"}

        except Exception as e:
            logger.warning(f"Erro ao obter tamanho do modelo {model_name}: {e}")
            return {"formatted": "Erro ao obter tamanho", "bytes": 0, "type": "error"}

    def _estimate_model_size(self, model_name: str) -> Dict[str, Any]:
        """Estima o tamanho do modelo baseado no nome"""
        name_lower = model_name.lower()

        # Estimativas baseadas em modelos conhecidos
        if "gpt2" in name_lower:
            if "medium" in name_lower:
                return {"bytes": 1400000000, "formatted": "1.4 GB"}  # ~1.4GB
            elif "large" in name_lower:
                return {"bytes": 3200000000, "formatted": "3.2 GB"}  # ~3.2GB
            elif "xl" in name_lower:
                return {"bytes": 6400000000, "formatted": "6.4 GB"}  # ~6.4GB
            else:
                return {"bytes": 500000000, "formatted": "500 MB"}  # ~500MB (base)

        elif "bert" in name_lower:
            if "large" in name_lower:
                return {"bytes": 1300000000, "formatted": "1.3 GB"}  # ~1.3GB
            else:
                return {"bytes": 400000000, "formatted": "400 MB"}  # ~400MB (base)

        elif "t5" in name_lower:
            if "small" in name_lower:
                return {"bytes": 240000000, "formatted": "240 MB"}  # ~240MB
            elif "base" in name_lower:
                return {"bytes": 850000000, "formatted": "850 MB"}  # ~850MB
            elif "large" in name_lower:
                return {"bytes": 3000000000, "formatted": "3.0 GB"}  # ~3GB
            elif "3b" in name_lower:
                return {"bytes": 11000000000, "formatted": "11 GB"}  # ~11GB
            elif "11b" in name_lower:
                return {"bytes": 42000000000, "formatted": "42 GB"}  # ~42GB

        elif "7b" in name_lower:
            return {"bytes": 14000000000, "formatted": "14 GB"}  # ~14GB
        elif "13b" in name_lower:
            return {"bytes": 26000000000, "formatted": "26 GB"}  # ~26GB
        elif "30b" in name_lower:
            return {"bytes": 60000000000, "formatted": "60 GB"}  # ~60GB
        elif "70b" in name_lower:
            return {"bytes": 140000000000, "formatted": "140 GB"}  # ~140GB

        # Padrão para modelos desconhecidos
        return {"bytes": 1000000000, "formatted": "~1 GB"}

    def get_download_progress(self, model_name: str) -> Dict[str, Any]:
        """Obtém o progresso atual do download de um modelo"""
        progress = self.download_progress.get(model_name, {})
        return {
            "downloading": progress.get("downloading", False),
            "progress": progress.get("progress", 0),
            "status": progress.get("status", ""),
            "downloaded_bytes": progress.get("downloaded_bytes", 0),
            "total_bytes": progress.get("total_bytes", 0),
            "speed": progress.get("speed", 0),
            "eta": progress.get("eta", 0),
        }

    def _update_download_progress(
        self,
        model_name: str,
        progress: int,
        status: str,
        downloaded_bytes: int = 0,
        total_bytes: int = 0,
        speed: float = 0,
        eta: int = 0,
    ):
        """Atualiza o progresso do download com informações detalhadas"""
        self.download_progress[model_name] = {
            "downloading": progress < 100,
            "progress": progress,
            "status": status,
            "downloaded_bytes": downloaded_bytes,
            "total_bytes": total_bytes,
            "speed": speed,
            "eta": eta,
            "timestamp": time.time(),
        }

    def _clear_download_progress(self, model_name: str):
        """Limpa o progresso do download"""
        if model_name in self.download_progress:
            del self.download_progress[model_name]

    def cancel_download(self, model_name: str) -> Dict[str, Any]:
        """Cancela um download em andamento"""
        try:
            if model_name not in self.active_downloads:
                return {"success": False, "error": "Nenhum download ativo encontrado"}

            download_info = self.active_downloads[model_name]
            process = download_info.get("process")

            if process and process.poll() is None:  # Processo ainda está rodando
                logger.info(f"🛑 Cancelando download: {model_name}")

                # Marcar como cancelado
                self._update_download_progress(model_name, 0, "Cancelando download...")

                # Terminar processo
                try:
                    process.terminate()
                    # Aguardar terminação graceful
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("Processo não terminou graciosamente, forçando...")
                    process.kill()
                    process.wait()

                self._cleanup_download(model_name)

                return {
                    "success": True,
                    "message": f"Download de {model_name} cancelado com sucesso",
                }
            else:
                self._cleanup_download(model_name)
                return {"success": False, "error": "Download já terminou"}

        except Exception as e:
            logger.error(f"Erro ao cancelar download de {model_name}: {e}")
            return {"success": False, "error": f"Erro no cancelamento: {str(e)}"}

    def _is_download_cancelled(self, model_name: str) -> bool:
        """Verifica se um download foi marcado para cancelamento"""
        # Verificar se o download ainda está na lista de ativos
        if model_name not in self.active_downloads:
            return True

        # Verificar se o progresso indica cancelamento
        progress = self.download_progress.get(model_name, {})
        status = progress.get("status", "")
        return "cancelando" in status.lower() or "cancelado" in status.lower()

    def _cleanup_download(self, model_name: str):
        """Limpa recursos de um download finalizado ou cancelado"""
        try:
            # Remover da lista de downloads ativos
            if model_name in self.active_downloads:
                del self.active_downloads[model_name]
                logger.debug(f"Download {model_name} removido da lista de ativos")

            # Manter o progresso por um tempo para que o frontend possa ler o status final
            # O progresso será limpo pela próxima operação ou reinicialização

        except Exception as e:
            logger.error(f"Erro no cleanup de {model_name}: {e}")

    def get_active_downloads(self) -> List[str]:
        """Retorna lista de downloads atualmente ativos"""
        active = []
        for model_name, download_info in self.active_downloads.items():
            process = download_info.get("process")
            if process and process.poll() is None:  # Processo ainda rodando
                active.append(model_name)
            else:
                # Processo terminou, fazer cleanup
                self._cleanup_download(model_name)

        return active

    def _is_gguf_repository(self, model) -> bool:
        """Verifica se um repositório contém principalmente arquivos GGUF"""
        try:
            model_name = model.id

            # Verificação rápida baseada no nome
            if "gguf" in model_name.lower():
                return True

            # Verificar tags do modelo
            if hasattr(model, "tags") and model.tags:
                if "gguf" in [tag.lower() for tag in model.tags]:
                    return True

            # Verificar se tem biblioteca GGUF
            if hasattr(model, "library_name") and model.library_name == "gguf":
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking if {model} is GGUF repository: {e}")
            return False

    def _get_gguf_variants(self, model_name: str) -> List[Dict[str, Any]]:
        """Obtém todas as variantes GGUF de um repositório"""
        try:
            from huggingface_hub import list_repo_files

            logger.info(f"Fetching GGUF variants for {model_name}")

            # Listar todos os arquivos do repositório
            files = list_repo_files(model_name, repo_type="model")

            # Filtrar apenas arquivos .gguf
            gguf_files = [f for f in files if f.lower().endswith(".gguf")]

            logger.info(f"Found {len(gguf_files)} GGUF files in {model_name}")

            variants = []
            base_info = self._get_model_base_info(model_name)

            for gguf_file in gguf_files:
                # Extrair informações de quantização do nome do arquivo
                quant_info = self._parse_gguf_filename(gguf_file)

                # Criar entrada para cada variante
                variant = {
                    "name": f"{model_name}:{gguf_file}",  # Nome único para identificar o arquivo específico
                    "display_name": f"{model_name.split('/')[-1]} - {quant_info['display_name']}",
                    "organization": model_name.split("/")[0] if "/" in model_name else "",
                    "description": f"{base_info.get('description', model_name)} - {quant_info['description']}",
                    "type": self._classify_model_type(model_name),
                    "installed": self._is_gguf_variant_installed(model_name, gguf_file),
                    "can_download": not self._is_gguf_variant_installed(model_name, gguf_file),
                    "downloads": base_info.get("downloads", 0),
                    "size_estimate": quant_info.get("size_estimate", "Unknown"),
                    "size_bytes": 0,  # Seria necessário uma chamada adicional para obter o tamanho real
                    "size_type": "estimated",
                    "quantization": quant_info["quantization"],
                    "precision": quant_info["precision"],
                    "file_name": gguf_file,
                    "is_gguf_variant": True,
                    "base_model": model_name,
                }

                variants.append(variant)

            # Ordenar por precisão (maiores primeiro)
            variants.sort(
                key=lambda x: self._quantization_sort_key(x["quantization"]), reverse=True
            )

            return variants

        except Exception as e:
            logger.error(f"Error fetching GGUF variants for {model_name}: {e}")
            # Em caso de erro, retornar pelo menos o modelo base
            base_model = self._format_huggingface_model_by_name(model_name)
            return [base_model] if base_model else []

    def _get_model_base_info(self, model_name: str) -> Dict[str, Any]:
        """Obtém informações básicas de um modelo"""
        try:
            if self.api:
                model_info = self.api.model_info(model_name)
                return {
                    "description": getattr(model_info, "id", model_name),
                    "downloads": getattr(model_info, "downloads", 0),
                }
        except Exception as e:
            logger.debug(f"Could not get base info for {model_name}: {e}")

        return {"description": model_name, "downloads": 0}

    def _parse_gguf_filename(self, filename: str) -> Dict[str, Any]:
        """Extrai informações de quantização de um nome de arquivo GGUF"""
        import re

        # Padrões comuns de quantização GGUF
        quantization_patterns = {
            r"Q(\d+)_K_([SML])": lambda m: f"Q{m.group(1)}_K_{m.group(2)}",
            r"Q(\d+)_K": lambda m: f"Q{m.group(1)}_K",
            r"Q(\d+)_(\d+)": lambda m: f"Q{m.group(1)}_{m.group(2)}",
            r"Q(\d+)": lambda m: f"Q{m.group(1)}",
            r"F(\d+)": lambda m: f"F{m.group(1)}",
            r"fp(\d+)": lambda m: f"FP{m.group(1)}",
        }

        filename_upper = filename.upper()
        quantization = "Unknown"
        precision = "Unknown"

        for pattern, formatter in quantization_patterns.items():
            match = re.search(pattern, filename_upper)
            if match:
                quantization = formatter(match)
                break

        # Estimar tamanho baseado na quantização
        size_estimates = {
            "Q2_K": "~2.5GB",
            "Q3_K_S": "~3.5GB",
            "Q3_K_M": "~4GB",
            "Q3_K_L": "~4.5GB",
            "Q4_K_S": "~4.5GB",
            "Q4_K_M": "~5GB",
            "Q4_0": "~4.5GB",
            "Q4_1": "~5GB",
            "Q5_K_S": "~5.5GB",
            "Q5_K_M": "~6GB",
            "Q5_0": "~5.5GB",
            "Q5_1": "~6GB",
            "Q6_K": "~6.5GB",
            "Q8_0": "~7.5GB",
            "F16": "~14GB",
            "F32": "~28GB",
        }

        size_estimate = size_estimates.get(quantization, "Unknown")

        # Extrair precisão
        if "Q" in quantization:
            precision = "Quantized"
        elif "F16" in quantization:
            precision = "Half Precision"
        elif "F32" in quantization:
            precision = "Full Precision"

        return {
            "quantization": quantization,
            "precision": precision,
            "size_estimate": size_estimate,
            "display_name": quantization,
            "description": f"Quantization: {quantization}, Est. Size: {size_estimate}",
        }

    def _quantization_sort_key(self, quantization: str) -> int:
        """Retorna chave de ordenação para quantizações (maior precisão primeiro)"""
        order = {
            "F32": 100,
            "F16": 90,
            "Q8_0": 80,
            "Q6_K": 70,
            "Q5_K_M": 65,
            "Q5_K_S": 64,
            "Q5_1": 63,
            "Q5_0": 62,
            "Q4_K_M": 55,
            "Q4_K_S": 54,
            "Q4_1": 53,
            "Q4_0": 52,
            "Q3_K_L": 45,
            "Q3_K_M": 44,
            "Q3_K_S": 43,
            "Q2_K": 30,
        }
        return order.get(quantization, 0)

    def _is_gguf_variant_installed(self, model_name: str, gguf_file: str) -> bool:
        """Verifica se uma variante GGUF específica está instalada"""
        try:
            model_path = self.cache_dir / f"models--{model_name.replace('/', '--')}"
            if not model_path.exists():
                return False

            # Procurar pelo arquivo específico
            for root, dirs, files in os.walk(model_path):
                if gguf_file in files:
                    return True

            return False
        except Exception as e:
            logger.error(f"Error checking GGUF variant installation: {e}")
            return False

    def _format_huggingface_model_by_name(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Formata um modelo do HF Hub apenas pelo nome (fallback)"""
        try:
            installed = self._is_model_installed(model_name)
            size_info = self._get_model_size(model_name)

            return {
                "name": model_name,
                "display_name": model_name.split("/")[-1],
                "organization": model_name.split("/")[0] if "/" in model_name else "",
                "description": model_name,
                "type": self._classify_model_type(model_name),
                "installed": installed,
                "can_download": not installed,
                "downloads": 0,
                "size_estimate": size_info["formatted"],
                "size_bytes": size_info["bytes"],
                "size_type": size_info["type"],
                "last_modified": None,
                "created_at": None,
                "file_count": size_info.get("file_count", 0),
            }
        except Exception as e:
            logger.error(f"Error formatting model {model_name}: {e}")
            return None

    # ... (métodos existentes continuam aqui)
