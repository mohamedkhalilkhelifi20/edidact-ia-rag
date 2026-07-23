from src.vecteur.search import rechercher
from src.generation.generateur import generer_exercice


def generer_nouvel_exercice(
    category: str,
    sub_category: str,
    sub_sub_category: str,
    sub_sub_sub_category: str,
    degree: str,
    type_exercice: str,
    texte: str = "",
    limite: int = 3,
) -> dict:
    # type_exercice n'est PAS transmis à rechercher() : le payload Qdrant ne
    # contient pas ce champ (il ne fait pas partie de CHAMPS_PAYLOAD_INDEXES),
    # la recherche d'exemples reste filtrée uniquement sur category/sub_category/
    # sub_sub_category/sub_sub_sub_category/degree, comme avant.
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
        "type_exercice": type_exercice,
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
        type_exercice="clavier_langue",
        texte="conditionnel passé",
    )
    print(json.dumps(resultat, ensure_ascii=False, indent=2))