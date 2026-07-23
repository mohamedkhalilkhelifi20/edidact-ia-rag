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
def _get_secret(key: str) -> str | None:
    """Lit une variable soit depuis st.secrets (Streamlit Cloud), soit depuis .env (local/script)."""
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)

QDRANT_URL = _get_secret("QDRANT_URL")
QDRANT_API_KEY = _get_secret("QDRANT_API_KEY")

# Connexion locale (pour la migration, host/port séparés)
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))

# ── OpenAI ──
OPENAI_API_KEY = _get_secret("OPENAI_API_KEY")

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

# ── Seuils de déduplication ──
SEUIL_DOUBLON_EXACT = 1.0
SEUIL_DOUBLON_SEMANTIQUE = 0.95
SEUIL_VARIANTE_A_VERIFIER = 0.85


# ── Types d'exercice ──
# Chaque type a :
#   - "description" : phrase d'explication (existant, inchangé)
#   - "format_reference" : squelette JSON structurel (contenu/correction),
#     validé manuellement par Mohamed exemple réel à l'appui, PAS deviné/
#     inventé par le modèle ou par Claude. Tant qu'un type n'a pas été validé,
#     "format_reference" reste None — prompt_builder.py doit gérer ce cas
#     sans planter (retombe sur la description seule, comportement d'avant).
#
# Types validés jusqu'ici : drag_and_drop_phrase, clavier_maths.
# Les autres restent à traiter un par un, même méthode (exemple réel +
# validation explicite), avant de remplir leur format_reference.
TYPES_EXERCICE = {
    "clavier_maths": {
        "description": "Calcul mathématique avec un seul champ de réponse numérique à taper au clavier.",
        "format_reference": {
            "contenu": {
                "calculs": [
                    {"id": 1, "question": "15 + 6"},
                    {"id": 2, "question": "23 - 9"}
                ]
            },
            "correction": [21, 14]
        }
    },
    "clavier2inputs": {
        "description": "Calcul mathématique nécessitant deux réponses numériques séparées, chacune tapée dans son propre champ.",
        "format_reference": {
            "contenu": {
                "calculs": [
                    {"id": 1, "question": "2 + 2 + 8 = ___ + ___"},
                    {"id": 2, "question": "5 + 4 + 1 = ___ + ___"}
                ]
            },
            "correction": [
                [10, 2],
                [7, 3]
            ]
        }
    },
    "clavier_langue": {
        "description": "Phrase à trou : l'élève tape la réponse (mot, conjugaison) au clavier dans un champ texte.",
        "format_reference": {
            "contenu": {
                "phrases": [
                    {"id": 1, "phrase": "Tu (finir) ______ ton exposé avant midi."},
                    {"id": 2, "phrase": "Nous (partir) ______ demain matin."}
                ]
            },
            "correction": ["finiras", "partirons"]
        }
    },
    "click": {
        "description": "Un support (une image, ou un mot/étiquette comme 'Vocabulaire') accompagné de 2 choix de réponse ; l'élève clique sur le bon.",
        "format_reference": {
            "contenu": {
                "items": [
                    {
                        "id": 1,
                        "support": "un garçon aux cheveux noirs",
                        "choix": ["Der Vater", "Der Bruder"]
                    },
                    {
                        "id": 2,
                        "support": "deux garçons jouent au tennis de table",
                        "choix": ["Klettern", "Tischtennis spielen"]
                    }
                ]
            },
            "correction": ["Der Bruder", "Tischtennis spielen"]
        }
    },
    "click_3_choix": {
        "description": "Un support (une image, ou un mot/étiquette) accompagné de 3 choix de réponse ; l'élève clique sur le bon.",
        "format_reference": {
            "contenu": {
                "items": [
                    {
                        "id": 1,
                        "support": "un garçon aux cheveux noirs",
                        "choix": ["Der Vater", "Der Bruder", "Die Mutter"]
                    },
                    {
                        "id": 2,
                        "support": "deux garçons jouent au tennis de table",
                        "choix": ["Klettern", "Tischtennis spielen", "Geige spielen"]
                    }
                ]
            },
            "correction": ["Der Bruder", "Tischtennis spielen"]
        }
    },
    "click_4_choix": {
        "description": "Un support (une image, ou un mot/étiquette) accompagné de 4 choix de réponse (disposés en grille) ; l'élève clique sur le bon.",
        "format_reference": {
            "contenu": {
                "items": [
                    {
                        "id": 1,
                        "support": "un garçon aux cheveux noirs",
                        "choix": ["Der Vater", "Der Bruder", "Die Mutter", "Die Schwester"]
                    },
                    {
                        "id": 2,
                        "support": "deux garçons jouent au tennis de table",
                        "choix": ["Klettern", "Tischtennis spielen", "Geige spielen", "Schwimmen"]
                    }
                ]
            },
            "correction": ["Der Bruder", "Tischtennis spielen"]
        }
    },
    "click_phrase": {
        "description": "Un texte (question directe, phrase à trou, ou affirmation à juger vrai/faux), sans image, avec 2 choix de réponse ; l'élève clique sur le bon.",
        "format_reference": {
            "contenu": {
                "items": [
                    {
                        "id": 1,
                        "phrase": "........ vas à l'école.",
                        "choix": ["Je", "Tu"]
                    },
                    {
                        "id": 2,
                        "phrase": "........ mange une pomme.",
                        "choix": ["Il", "Nous"]
                    }
                ]
            },
            "correction": ["Tu", "Il"]
        }
    },
    "click_3_phrase": {
        "description": "Un texte (question directe ou phrase à trou), sans image, avec 3 choix de réponse ; l'élève clique sur le bon.",
        "format_reference": {
            "contenu": {
                "items": [
                    {
                        "id": 1,
                        "phrase": "...... wohnst du?",
                        "choix": ["Was", "Wo", "Wann"]
                    },
                    {
                        "id": 2,
                        "phrase": "...... heisst du?",
                        "choix": ["Wie", "Wo", "Warum"]
                    }
                ]
            },
            "correction": ["Wo", "Wie"]
        }
    },
    "click_4_phrase": {
        "description": "Un texte, sans image, avec 4 choix de réponse (disposés en grille) ; l'élève clique sur le bon.",
        "format_reference": {
            "contenu": {
                "items": [
                    {
                        "id": 1,
                        "phrase": "(Léo) joue au football durant la récréation.",
                        "choix": ["Groupe infinitif", "Groupe nominal", "Pronom personnel", "Nom propre"]
                    },
                    {
                        "id": 2,
                        "phrase": "(La maîtresse) écrit au tableau.",
                        "choix": ["Verbe conjugué", "Groupe nominal", "Adjectif", "Nom propre"]
                    }
                ]
            },
            "correction": ["Nom propre", "Groupe nominal"]
        }
    },
    "dropbox": {
        "description": "Phrase à trou avec un menu déroulant listant plusieurs options ; l'élève sélectionne la bonne.",
        "format_reference": {
            "contenu": {
                "items": [
                    {
                        "id": 1,
                        "phrase": "........ suis content d'aller à l'école.",
                        "choix": ["Je", "Tu", "Il"]
                    },
                    {
                        "id": 2,
                        "phrase": "........... joues au ballon dans la cour.",
                        "choix": ["Ils", "Vous", "Tu"]
                    }
                ]
            },
            "correction": ["Je", "Tu"]
        }
    },
    "dropbox_langue": {
        "description": "Mot ou phrase à trou (orthographe/vocabulaire/grammaire d'une langue) avec un menu déroulant listant plusieurs variantes ; l'élève sélectionne la bonne.",
        "format_reference": {
            "contenu": {
                "items": [
                    {
                        "id": 1,
                        "phrase": "Guten ____",
                        "choix": ["Tag", "tagg", "teg"]
                    },
                    {
                        "id": 2,
                        "phrase": "...... name ist Leo.",
                        "choix": ["Men", "Mein", "Meinm"]
                    }
                ]
            },
            "correction": ["Tag", "Mein"]
        }
    },
    "drag_and_drop_phrase": {
        "description": "Phrase à trou avec plusieurs étiquettes à glisser-déposer ; l'élève place la bonne étiquette dans le trou.",
        "format_reference": {
            "contenu": {
                "etiquettes": ["dormir", "ouvrir", "lancer", "écrire", "jouer", "mettre"],
                "phrases": [
                    {"id": 1, "phrase": "Le chat aime ____ sur le canapé."},
                    {"id": 2, "phrase": "Nous allons ____ la fenêtre."}
                ]
            },
            "correction": ["dormir", "ouvrir"]
        }
    },
    "drag_and_drop_paragraphe": {
        "description": "Texte à trou avec plusieurs étiquettes à glisser-déposer (liste d'options plus large) ; l'élève place la bonne étiquette dans le trou.",
        "format_reference": {
            "contenu": {
                "etiquettes": ["Je", "tu", "elle", "nous", "vous", "ils"],
                "texte": "Bonjour ! ___1___ m'appelle Ely et j'ai dix ans. Chaque matin, quand je vais à l'école, maman me dit : « Est-ce que ___2___ as pris ton cartable ? » Maman est très gentille : ___3___ prépare mon petit déjeuner avec soin. À l'école, mes amis et moi, ___4___ jouons dans la cour avant de rentrer en classe."
            },
            "correction": ["Je", "tu", "elle", "nous"]
        }
    },
}