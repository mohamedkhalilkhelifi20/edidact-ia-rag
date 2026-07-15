from qdrant_client.models import Filter, FieldCondition, MatchValue
from src.database.client import get_client
from src.embedding.embedding import vectoriser
from src.config.config import COLLECTION_HYBRID

def rechercher_dense(
    texte: str,
    category: str,
    sub_category: str,
    sub_sub_category: str,
    sub_sub_sub_category: str,
    degree: str,
    limite: int = 3
):
    client = get_client()
    vecteur = vectoriser(texte)

    filtre = Filter(must=[
        FieldCondition(key="category", match=MatchValue(value=category)),
        FieldCondition(key="sub_category", match=MatchValue(value=sub_category)),
        FieldCondition(key="sub_sub_category", match=MatchValue(value=sub_sub_category)),
        FieldCondition(key="sub_sub_sub_category", match=MatchValue(value=sub_sub_sub_category)),
        FieldCondition(key="degree", match=MatchValue(value=degree)),
    ])

    resultats = client.query_points(
        collection_name=COLLECTION_HYBRID,
        query=vecteur,
        using="dense",
        query_filter=filtre,
        limit=limite
    ).points

    return resultats

if __name__ == "__main__":
    resultats = rechercher_dense(
        "Écris l'article correct de ces noms.",
        category="Allemand", sub_category="Grammaire",
        sub_sub_category="Les noms", sub_sub_sub_category="Le genre des noms",
        degree="5/6"
    )
    for r in resultats:
        print(f"score={r.score:.4f} | {r.payload.get('consigne')}")