from src.vecteur.search import rechercher
from src.generation.generateur import generer_exercice


def generer_nouvel_exercice(
    category: str,
    sub_category: str,
    sub_sub_category: str,
    sub_sub_sub_category: str,
    degree: str,
    texte: str = "",
    limite: int = 3,
) -> dict:
    exemples = rechercher(
        category=category,
        sub_category=sub_category,
        sub_sub_category=sub_sub_category,
        sub_sub_sub_category=sub_sub_sub_category,
        degree=degree,
        texte=texte,
        limite=limite,
    )

    if not exemples:
        raise ValueError("Aucun exemple trouvé dans Qdrant pour ces filtres — impossible de générer.")

    demande = {
        "category": category,
        "sub_category": sub_category,
        "sub_sub_category": sub_sub_category,
        "sub_sub_sub_category": sub_sub_sub_category,
        "degree": degree,
        "texte": texte,
        "limite": limite,
    }

    return generer_exercice(demande, exemples)


if __name__ == "__main__":
    import json

    resultat = generer_nouvel_exercice(
        category="Français",
        sub_category="Conjugaison",
        sub_sub_category="Les modes et les temps",
        sub_sub_sub_category="Le conditionnel passé",
        degree="9/10",
        texte="conditionnel passé",
    )
    print(json.dumps(resultat, ensure_ascii=False, indent=2))