import json
from datetime import datetime, timezone
from pathlib import Path

from src.config.config import LOG_APPELS_PATH


def logger_appel(
    etape: str,
    reasoning_effort: str,
    verbosity: str,
    duree: float,
    statut: str,
    limite: int = None,
    raisonnement: str = "",
) -> None:
    """
    Trace CHAQUE appel au modèle (succès ou échec) dans un fichier JSON.
    `limite` (taille du pool d'exemples Qdrant demandée) est incluse pour
    pouvoir comparer objectivement plusieurs valeurs de limite entre elles —
    sans ce champ, impossible de relier après coup un temps/échec à la valeur
    de limite qui était utilisée à ce moment-là.
    """
    entree = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "etape": etape,
        "reasoning_effort": reasoning_effort,
        "verbosity": verbosity,
        "duree_s": round(duree, 2),
        "statut": statut,
        "limite": limite,
        "raisonnement": raisonnement,
    }

    Path(LOG_APPELS_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_APPELS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entree, ensure_ascii=False) + "\n")