from pathlib import Path
from dotenv import load_dotenv
import os


# ── Chemins ──
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "data" / "edidact_phase0_dataset.json"
LOG_PATH = BASE_DIR / "logs" / "indexation.log"
load_dotenv(BASE_DIR / ".env")
LOG_ECHECS_PATH = BASE_DIR / "logs" / "echecs_generation.jsonl"
LOG_APPELS_PATH = BASE_DIR / "logs" / "appels_llm.jsonl"

POOL_CANDIDATS = 8
LOG_EXEMPLES_MONTRES = BASE_DIR / "logs" / "exemples_montres.jsonl"

LOG_CORRECTIONS_PATH = BASE_DIR / "logs" / "corrections_professeur.jsonl"

# ── Connexion Qdrant ──
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))

# ── OpenAI ──
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ── Collection ──
COLLECTION_NAME = "edidact_exercices"
COLLECTION_HYBRID = "edidact_exercices_hybrid"
VECTOR_SIZE = 1024
DISTANCE_METRIC = "Cosine"

# ── Modèle d'embedding ──
EMBEDDING_MODEL = "BAAI/bge-m3"

# ── Champs utilisés pour construire le texte à vectoriser ──
CHAMPS_EMBEDDING = ["category", "sub_category", "sub_sub_sub_category", "degree", "consigne"]

# ── Champs indexés comme filtres dans le payload Qdrant ──
CHAMPS_PAYLOAD_INDEXES = ["degree", "category", "sub_category", "sub_sub_category", "sub_sub_sub_category"]

# ── Traitement par batch ──
BATCH_SIZE = 100

# ── Seuils de déduplication (barrière 3, cohérent avec ta doc) ──
SEUIL_DOUBLON_EXACT = 1.0
SEUIL_DOUBLON_SEMANTIQUE = 0.95
SEUIL_VARIANTE_A_VERIFIER = 0.85