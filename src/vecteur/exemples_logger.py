import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.config.config import LOG_EXEMPLES_MONTRES


def logger_exemples_montres(id_exercices: list[str], filtres: dict) -> None:
    """
    Note, à chaque recherche Qdrant, quels exercices ont été montrés comme
    exemples au modèle. Une ligne = une recherche.
    """
    entree = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "id_exercices": id_exercices,
        "filtres": filtres,
    }
    Path(LOG_EXEMPLES_MONTRES).parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_EXEMPLES_MONTRES, "a", encoding="utf-8") as f:
        f.write(json.dumps(entree, ensure_ascii=False) + "\n")


def compter_vues(id_exercices_candidats: list[str]) -> dict[str, int]:
    """
    Lit le carnet et retourne, pour chaque id d'exercice candidat, combien de
    fois il a déjà été montré. Un id jamais vu vaut 0 — pas d'erreur si le
    carnet n'existe pas encore (première utilisation).
    """
    compteur = Counter()
    try:
        with open(LOG_EXEMPLES_MONTRES, "r", encoding="utf-8") as f:
            for ligne in f:
                ligne = ligne.strip()
                if not ligne:
                    continue
                entree = json.loads(ligne)
                for id_ex in entree.get("id_exercices", []):
                    compteur[id_ex] += 1
    except FileNotFoundError:
        pass

    return {id_ex: compteur.get(id_ex, 0) for id_ex in id_exercices_candidats}