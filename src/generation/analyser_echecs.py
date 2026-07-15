import json
from collections import Counter

from src.config.config import LOG_ECHECS_PATH


def analyser_echecs() -> None:
    """
    Lit le log JSONL des échecs de génération et affiche les motifs les plus
    fréquents par étape. Script de détection uniquement — ne corrige rien,
    ne recalcule rien depuis le dataset. Sert juste à décider objectivement
    quelle règle du prompt mérite d'être corrigée en premier.
    """
    try:
        with open(LOG_ECHECS_PATH, "r", encoding="utf-8") as f:
            lignes = [json.loads(l) for l in f if l.strip()]
    except FileNotFoundError:
        print(f"Aucun log trouvé à {LOG_ECHECS_PATH} — pas encore de générations enregistrées.")
        return

    if not lignes:
        print("Log vide.")
        return

    print(f"Total échecs enregistrés : {len(lignes)}\n")

    par_etape = Counter(l["etape"] for l in lignes)
    print("Répartition par étape :")
    for etape, n in par_etape.most_common():
        print(f"  {etape} : {n}")

    print("\nMotifs les plus fréquents (toutes étapes confondues) :")
    par_motif = Counter(l["motif"] for l in lignes)
    for motif, n in par_motif.most_common(10):
        print(f"  [{n}] {motif}")

    print("\nRépartition par matière (category) :")
    par_matiere = Counter(l.get("category") for l in lignes)
    for matiere, n in par_matiere.most_common():
        print(f"  {matiere} : {n}")


if __name__ == "__main__":
    analyser_echecs()