"""
Custom Simple AI Provider - Provides dental-specific responses
"""

import logging
import random
from typing import Any, Dict, Optional

from app.services.ai_providers.base_provider import BaseAIProvider

logger = logging.getLogger(__name__)


class CustomDentalProvider(BaseAIProvider):
    """
    Custom dental AI provider with pre-defined responses
    Provides reliable, dental-specific responses in Portuguese
    """

    def __init__(self, settings: Dict[str, Any]):
        super().__init__(settings)
        self.responses = {
            # Saudações
            "saudacao": [
                "Olá! Sou seu assistente especializado em odontologia. Como posso ajudá-lo hoje?",
                "Olá! Estou aqui para ajudar com questões odontológicas. Em que posso ser útil?",
                "Oi! Sou seu assistente dental. Como posso auxiliá-lo?",
            ],
            # Dor de dente
            "dor_dente": [
                "Para dor de dente, recomendo: 1) Uso de analgésicos como paracetamol ou ibuprofeno conforme orientação médica; 2) Aplicação de gelo no local por 15-20 minutos; 3) Evitar alimentos muito quentes ou frios; 4) Procurar atendimento odontológico o mais rápido possível.",
                "A dor de dente pode ter várias causas. Como medida imediata, você pode tomar um analgésico e aplicar gelo. É importante procurar um dentista para diagnóstico e tratamento adequado.",
                "Dor de dente requer atenção profissional. Enquanto isso, mantenha a área limpa, evite mastigar do lado dolorido e procure atendimento odontológico urgente.",
            ],
            # Cárie
            "carie": [
                "A cárie é uma doença que causa deterioração dos dentes devido a bactérias que produzem ácidos. É causada principalmente pelo consumo excessivo de açúcar e má higiene bucal.",
                "Cárie é o resultado da ação de bactérias que transformam restos de alimentos em ácido, corroendo o esmalte dental. Prevenção: escovação adequada, uso de fio dental e consultas regulares.",
                "A cárie dental é uma infecção bacteriana que destrói o tecido dental. Pode ser prevenida com boa higiene bucal e redução do consumo de açúcar.",
            ],
            # Higiene bucal
            "higiene": [
                "A higiene bucal adequada inclui: escovação 3x ao dia, uso de fio dental diariamente, enxaguante bucal e visitas regulares ao dentista a cada 6 meses.",
                "Para uma boa higiene bucal: escove os dentes por pelo menos 2 minutos, use fio dental, escove a língua e troque a escova a cada 3 meses.",
                "Higiene bucal eficaz previne cáries e gengivite. Escove após as refeições, use fio dental e mantenha consultas regulares com seu dentista.",
            ],
            # Gengivite
            "gengivite": [
                "A gengivite é inflamação das gengivas causada por acúmulo de placa bacteriana. Sintomas incluem vermelhidão, inchaço e sangramento durante a escovação.",
                "Gengivite pode ser tratada com melhoria da higiene bucal, uso de enxaguante antisséptico e limpeza profissional. Se não tratada, pode evoluir para periodontite.",
                "A gengivite é reversível com cuidados adequados: escovação suave, fio dental diário e acompanhamento profissional.",
            ],
            # Emergências
            "emergencia": [
                "Em caso de emergência dental, procure atendimento imediato. Para dor intensa, trauma ou sangramento, vá ao pronto-socorro odontológico.",
                "Emergências dentais incluem: dor intensa, dente quebrado, trauma facial, sangramento persistente. Procure atendimento urgente.",
                "Se houver dor severa, inchaço facial ou trauma, procure atendimento de emergência imediatamente.",
            ],
            # Geral
            "geral": [
                "Para questões específicas sobre seu tratamento dental, é importante consultar seu dentista pessoalmente.",
                "Cada caso é único. Recomendo que consulte um profissional para avaliação adequada.",
                "Posso fornecer informações gerais, mas para diagnóstico preciso, consulte um dentista.",
            ],
        }

        self.keywords = {
            "saudacao": ["olá", "oi", "bom dia", "boa tarde", "boa noite", "como vai", "tudo bem"],
            "dor_dente": [
                "dor de dente",
                "dente doendo",
                "dente dói",
                "dor dental",
                "dor no dente",
            ],
            "carie": ["cárie", "carie", "buraco no dente", "dente furado", "cavidade"],
            "higiene": [
                "escovar",
                "escovação",
                "higiene",
                "limpeza",
                "fio dental",
                "pasta de dente",
            ],
            "gengivite": [
                "gengivite",
                "gengiva",
                "sangramento",
                "gengiva inflamada",
                "gengiva inchada",
            ],
            "emergencia": [
                "emergência",
                "urgente",
                "dor forte",
                "trauma",
                "sangramento",
                "quebrou",
            ],
        }

    def initialize(self) -> bool:
        """Initialize the custom provider"""
        self.is_initialized = True
        logger.info("Custom Dental Provider initialized successfully")
        return True

    def is_available(self) -> bool:
        """Check if provider is available"""
        return self.is_initialized

    def generate_response(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Generate a response based on keywords"""

        # Validate query
        validation = self.validate_query(query)
        if not validation["valid"]:
            return {"success": False, "error": validation["error"], "response": ""}

        if not self.is_available():
            return {
                "success": False,
                "error": "Custom Dental Provider not available",
                "response": "",
                "provider": "Custom Dental",
                "model": "Custom Dental Assistant",
            }

        try:
            query_lower = query.lower()

            # Check for keyword matches
            for category, keywords in self.keywords.items():
                for keyword in keywords:
                    if keyword in query_lower:
                        response = random.choice(self.responses[category])
                        return {
                            "success": True,
                            "response": response,
                            "model": "Custom Dental Assistant",
                            "provider": "Custom Dental",
                            "category": category,
                        }

            # Default response for unrecognized queries - provide helpful fallback
            fallback_responses = [
                "Posso ajudá-lo com questões relacionadas à odontologia. Para sua pergunta específica, recomendo consultar um dentista para orientação adequada.",
                "Embora eu seja especializado em odontologia, posso tentar ajudar. Para informações mais precisas sobre sua pergunta, consulte um profissional de saúde.",
                "Sou um assistente especializado em odontologia. Para questões fora da minha especialidade, recomendo buscar orientação profissional adequada.",
                "Posso fornecer informações gerais sobre odontologia. Para sua pergunta específica, um profissional qualificado seria a melhor fonte de informação.",
            ]

            response = random.choice(fallback_responses)
            return {
                "success": True,
                "response": response,
                "model": "Custom Dental Assistant",
                "provider": "Custom Dental",
                "category": "geral",
            }

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "",
                "provider": "Custom Dental",
                "model": "Custom Dental Assistant",
            }

    def cleanup(self):
        """Cleanup resources"""
        self.is_initialized = False

    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information"""
        info = super().get_provider_info()
        info.update(
            {
                "model_name": "Custom Dental Assistant",
                "categories": list(self.keywords.keys()),
                "total_responses": sum(len(responses) for responses in self.responses.values()),
            }
        )
        return info
