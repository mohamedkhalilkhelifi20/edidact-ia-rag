import re
import time
from openai import OpenAI
from src.config.config import OPENAI_API_KEY
from src.generation.appel_logger import logger_appel

_client_openai = None

MODELE_PAR_DEFAUT = "gpt-5.4-mini"


def get_openai_client() -> OpenAI:
    global _client_openai
    if _client_openai is None:
        _client_openai = OpenAI(api_key=OPENAI_API_KEY)
    return _client_openai


def nettoyer_json(texte: str) -> str:
    """Retire les balises markdown ```json ... ``` si le LLM les ajoute malgré la consigne."""
    texte = texte.strip()
    texte = re.sub(r"^```json\s*", "", texte)
    texte = re.sub(r"^```\s*", "", texte)
    texte = re.sub(r"```\s*$", "", texte)
    return texte.strip()


def extraire_resume_raisonnement(response) -> str:
    """
    Extrait le résumé du raisonnement interne du modèle depuis response.output
    (item de type 'reasoning'). Peut être vide.
    """
    try:
        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) == "reasoning":
                morceaux = getattr(item, "summary", []) or []
                textes = [getattr(m, "text", "") for m in morceaux if getattr(m, "text", "")]
                if textes:
                    return "\n".join(textes)
    except Exception:
        pass
    return ""


def appeler_modele(
    prompt: str,
    reasoning_effort: str = "high",
    verbosity: str = "low",
    etape: str = "non_precisee",
    limite: int = None,
    type_exercice: str = None,
) -> tuple[str, str]:
    """
    Point d'entrée UNIQUE pour appeler le LLM — API Responses.

    limite : la taille du pool d'exemples Qdrant utilisée pour cette génération —
    transmise jusqu'au log de performance, pour pouvoir comparer objectivement
    plusieurs valeurs de limite entre elles.

    type_exercice : type demandé par le professeur (ex: "clavier_maths"), transmis
    jusqu'au log — permet, plus tard, de mesurer objectivement si le taux
    d'échec/de retry varie selon le type. Optionnel : certains appels (ex.
    relecture, correction professeur) n'ont pas toujours ce contexte disponible.

    Retourne (texte_nettoyé, statut).
    """
    client = get_openai_client()
    debut = time.time()

    response = client.responses.create(
        model=MODELE_PAR_DEFAUT,
        input=[{"role": "user", "content": prompt}],
        reasoning={"effort": reasoning_effort, "summary": "auto"},
        text={"verbosity": verbosity},
    )

    duree = time.time() - debut
    texte_brut = response.output_text or ""
    texte_propre = nettoyer_json(texte_brut)
    statut = getattr(response, "status", "inconnu")
    raisonnement = extraire_resume_raisonnement(response)

    logger_appel(
        etape=etape,
        reasoning_effort=reasoning_effort,
        verbosity=verbosity,
        duree=duree,
        statut=statut,
        limite=limite,
        raisonnement=raisonnement,
        type_exercice=type_exercice,
    )

    return texte_propre, statut