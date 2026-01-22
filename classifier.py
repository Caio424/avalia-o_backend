from typing import Dict
from transformers import pipeline
import logging

# Configuração de log básica
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Definição das categorias e soluções (Metadados)
CATEGORY_DATA = {
    "Financeiro/Vendas": {
        "solucao_tecnica": "Verificar tabela de preços e encaminhar ao vendas.",
        "solucao_cliente": "Um consultor enviará uma proposta em breve."
    },
    "Suporte Técnico": {
        "solucao_tecnica": "Verificar logs (Splunk) e abrir ticket Jira.",
        "solucao_cliente": "Nossa equipe técnica já está analisando o problema."
    },
    "Saudação": {
        "solucao_tecnica": "Responder cordialmente.",
        "solucao_cliente": "Olá! Como podemos ajudar?"
    },
    "Outros": {
        "solucao_tecnica": "Triagem manual necessária.",
        "solucao_cliente": "Um atendente irá analisar sua mensagem."
    }
}

# Lista de rótulos para o modelo
CANDIDATE_LABELS = list(CATEGORY_DATA.keys())
if "Outros" in CANDIDATE_LABELS:
    CANDIDATE_LABELS.remove("Outros")

# Inicialização Global do Modelo (Singleton pattern implícito pelo módulo)
# Usando um modelo multilíngue menor para equilibrar performance/precisão
# facebook/bart-large-mnli é o padrão excelente, mas pesado (~1.6GB).
# valhalla/distilbart-mnli-12-1 é muito mais leve (~300MB) e rápido, ideal para testes/dev.
MODEL_NAME = "valhalla/distilbart-mnli-12-1" 

logger.info(f"Carregando modelo de classificação Zero-Shot ({MODEL_NAME})...")
logger.info("ATENÇÃO: Na primeira execução, será feito o download do modelo (aprox. 300MB). Aguarde...")

try:
    classifier_pipeline = pipeline("zero-shot-classification", model=MODEL_NAME)
    logger.info("Modelo carregado com sucesso.")
except Exception as e:
    logger.error(f"FATAL: Erro ao carregar o modelo: {e}")
    raise e

def predict_category(text: str) -> Dict:
    """
    Classifica o texto usando um modelo Zero-Shot Transformer.
    """
    try:
        # Inferência
        result = classifier_pipeline(text, candidate_labels=CANDIDATE_LABELS)
        
        # O resultado vem ordenado por score decrescente
        labels = result['labels']
        scores = result['scores']
        
        top_label = labels[0]
        top_score = scores[0]

        # Lógica de Re-ranking para Priorizar Intenção Real sobre Saudação
        # Se a categoria principal for "Saudação", mas houver outra categoria relevante
        # com score razoável (ex: > 0.15), priorizamos a categoria relevante.
        # Motivo: "Olá, estou com problemas" -> Saudação (0.6), Suporte (0.3).
        # Queremos que suporte vença.
        
        PRIORITY_THRESHOLD = 0.15 # Se Financeiro/Suporte tiver > 15%, vence Saudação
        OPERATIONAL_CATEGORIES = ["Financeiro/Vendas", "Suporte Técnico"]
        
        if top_label == "Saudação":
            for i, label in enumerate(labels):
                if label in OPERATIONAL_CATEGORIES:
                    if scores[i] > PRIORITY_THRESHOLD:
                        top_label = label
                        top_score = scores[i]
                        # Ajustamos a confiança para refletir que fizemos uma re-classificação forçada
                        # ou mantemos o score original da categoria.
                        break
        
        # Lógica de fallback se a confiança for muito baixa
        # 0.3 é o threshold original, mas podemos ser mais lenientes se for uma categoria prioritária
        if top_score < 0.2:
            category = "Outros"
            confidence_level = "baixa"
        else:
            category = top_label
            confidence_level = "alta" if top_score > 0.6 else "média"

        data = CATEGORY_DATA.get(category, CATEGORY_DATA["Outros"])
        
        return {
            "categoria": category,
            "explicacao": f"Classificação semântica (IA) com score: {top_score:.2f}",
            "solucao_cliente": data["solucao_cliente"],
            "solucao_tecnica": data["solucao_tecnica"],
            "confianca": confidence_level
        }
        
    except Exception as e:
        logger.error(f"Erro na classificação: {e}")
        # Fallback seguro em caso de erro no modelo
        return {
            "categoria": "Outros",
            "explicacao": "Erro interno na classificação IA.",
            "solucao_cliente": CATEGORY_DATA["Outros"]["solucao_cliente"],
            "solucao_tecnica": CATEGORY_DATA["Outros"]["solucao_tecnica"],
            "confianca": "erro"
        }
