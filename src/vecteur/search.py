from qdrant_client.models import Filter, FieldCondition, MatchValue
from src.database.client import get_client
from src.config.config import COLLECTION_HYBRID, POOL_CANDIDATS
from src.vecteur.search_hybrid import rechercher_hybrid
from src.vecteur.search_dense import rechercher_dense
from src.vecteur.selection_diversite import selectionner_avec_diversite


def _formater(resultats, methode: str) -> list[dict]:
    return [
        {
            "methode": methode,
            "score": r.score,
            "id_exercice": r.payload.get("id_exercice"),
            "consigne": r.payload.get("consigne"),
            "contenu": r.payload.get("contenu"),
        }
        for r in resultats
    ]


def rechercher_par_filtre_seul(
    category: str, sub_category: str, sub_sub_category: str,
    sub_sub_sub_category: str, degree: str, limite: int = 3
) -> list[dict]:
    """Aucun texte fourni : retourne des exercices correspondant uniquement aux filtres."""
    client = get_client()
    filtre = Filter(must=[
        FieldCondition(key="category", match=MatchValue(value=category)),
        FieldCondition(key="sub_category", match=MatchValue(value=sub_category)),
        FieldCondition(key="sub_sub_category", match=MatchValue(value=sub_sub_category)),
        FieldCondition(key="sub_sub_sub_category", match=MatchValue(value=sub_sub_sub_category)),
        FieldCondition(key="degree", match=MatchValue(value=degree)),
    ])
    resultats, _ = client.scroll(
        collection_name=COLLECTION_HYBRID,
        scroll_filter=filtre,
        limit=POOL_CANDIDATS
    )

    filtres_log = {
        "category": category, "sub_category": sub_category,
        "sub_sub_category": sub_sub_category,
        "sub_sub_sub_category": sub_sub_sub_category, "degree": degree,
    }
    # Pas de score ici (scroll, pas une recherche par similarité) —
    # aucun "meilleur" à privilégier, tous égaux pour la diversité.
    resultats = selectionner_avec_diversite(resultats, limite, filtres_log, garder_meilleur=False)

    return [
        {
            "methode": "filtre_seul",
            "score": None,
            "id_exercice": r.payload.get("id_exercice"),
            "consigne": r.payload.get("consigne"),
            "contenu": r.payload.get("contenu"),
        }
        for r in resultats
    ]


def rechercher(
    category: str,
    sub_category: str,
    sub_sub_category: str,
    sub_sub_sub_category: str,
    degree: str,
    texte: str = "",
    limite: int = 3
) -> list[dict]:
    texte = (texte or "").strip()

    filtres_log = {
        "category": category, "sub_category": sub_category,
        "sub_sub_category": sub_sub_category,
        "sub_sub_sub_category": sub_sub_sub_category, "degree": degree,
    }

    if not texte:
        return rechercher_par_filtre_seul(
            category, sub_category, sub_sub_category, sub_sub_sub_category, degree, limite
        )

    # On demande un POOL de candidats (pas juste `limite`) à la méthode de
    # recherche, pour avoir de la marge sur laquelle appliquer la diversité.
    resultats = rechercher_hybrid(
        texte, category, sub_category, sub_sub_category, sub_sub_sub_category, degree, POOL_CANDIDATS
    )
    if resultats:
        resultats = selectionner_avec_diversite(resultats, limite, filtres_log, garder_meilleur=True)
        return _formater(resultats, "hybrid")

    print(f"[fallback] hybrid vide pour '{texte}' → dense")
    resultats = rechercher_dense(
        texte, category, sub_category, sub_sub_category, sub_sub_sub_category, degree, POOL_CANDIDATS
    )
    if resultats:
        resultats = selectionner_avec_diversite(resultats, limite, filtres_log, garder_meilleur=True)
        return _formater(resultats, "dense_fallback")

    # texte fourni mais rien trouvé → on retombe sur filtre seul plutôt que rien
    print(f"[fallback] dense vide aussi pour '{texte}' → filtre seul (sans texte)")
    return rechercher_par_filtre_seul(
        category, sub_category, sub_sub_category, sub_sub_sub_category, degree, limite
    )


if __name__ == "__main__":
    resultats = rechercher(
        category="Maths", sub_category="Nombres",
        sub_sub_category="Fractions", sub_sub_sub_category="Calcul de fractions",
        degree="9/10",
        texte="Bonjour, je cherche un exercice pour mes élèves qui ont des difficultés avec les fractions"
    )
    for r in resultats:
        print(f"[{r['methode']}] score={r['score']} | {r['consigne']}")