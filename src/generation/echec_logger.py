import json
from datetime import datetime, timezone
from pathlib import Path

from src.config.config import LOG_ECHECS_PATH


def logger_echec(etape: str, tentative: int, motif: str, demande: dict) -> None:
    """
    Ajoute une ligne JSONL décrivant un échec de génération.
    """
    entree = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "etape": etape,
        "tentative": tentative,
        "motif": motif,
        "category": demande.get("category"),
        "sub_category": demande.get("sub_category"),
        "sub_sub_sub_category": demande.get("sub_sub_sub_category"),
        "degree": demande.get("degree"),
        "type_exercice": demande.get("type_exercice"),
        "limite": demande.get("limite"),
    }

    Path(LOG_ECHECS_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_ECHECS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entree, ensure_ascii=False) + "\n")