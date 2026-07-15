import random
from src.vecteur.exemples_logger import compter_vues, logger_exemples_montres


def selectionner_avec_diversite(candidats: list, limite: int, filtres: dict, garder_meilleur: bool = True) -> list:
    """
    Point d'entrée UNIQUE de la règle de choix des exemples — appelé depuis
    search.py, quelle que soit la méthode de recherche utilisée en amont
    (hybrid, dense, filtre seul).

    Règle : si garder_meilleur=True (résultats classés par score, hybrid/dense),
    le 1er candidat est toujours conservé. Les places restantes vont aux
    candidats les MOINS souvent montrés (carnet exemples_logger), tirage au
    sort seulement en cas d'égalité entre plusieurs candidats à égalité de vues.

    Si garder_meilleur=False (filtre seul, sans score), tous les candidats
    sont traités à égalité pour la sélection, sans "meilleur" forcé.
    """
    if len(candidats) <= limite:
        resultat = candidats
    else:
        if garder_meilleur:
            meilleur = candidats[0]
            reste = candidats[1:]
            nombre_a_choisir = limite - 1
        else:
            meilleur = None
            reste = candidats
            nombre_a_choisir = limite

        ids_reste = [c.payload.get("id_exercice") for c in reste]
        vues = compter_vues(ids_reste)

        reste_melange = reste[:]
        random.shuffle(reste_melange)
        reste_trie = sorted(reste_melange, key=lambda c: vues.get(c.payload.get("id_exercice"), 0))

        choisis = reste_trie[:nombre_a_choisir]
        resultat = ([meilleur] + choisis) if garder_meilleur else choisis

    ids_montres = [c.payload.get("id_exercice") for c in resultat]
    logger_exemples_montres(id_exercices=ids_montres, filtres=filtres)

    return resultat