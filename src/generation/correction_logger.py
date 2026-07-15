import json
from datetime import datetime, timezone
from pathlib import Path

from src.config.config import LOG_CORRECTIONS_PATH


def logger_correction(instruction: str, acceptee: bool, motif: str = "") -> None:
    """
    Trace chaque demande de correction du professeur — utile plus tard pour
    repérer les instructions les plus fréquentes (signe de défauts récurrents
    à corriger à la source, dans prompt_builder.py, plutôt que de compter sur
    le professeur pour rattraper à chaque fois).
    """
    entree = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "instruction": instruction,
        "acceptee": acceptee,
        "motif": motif,
    }
    Path(LOG_CORRECTIONS_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_CORRECTIONS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entree, ensure_ascii=False) + "\n")