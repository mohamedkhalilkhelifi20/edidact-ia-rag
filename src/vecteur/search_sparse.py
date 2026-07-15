from fastembed import SparseTextEmbedding
from qdrant_client.models import Filter, FieldCondition, MatchValue, SparseVector
from src.database.client import get_client
from src.config.config import COLLECTION_HYBRID

_sparse_model = None

def get_sparse_model() -> SparseTextEmbedding:
    global _sparse_model
    if _sparse_model is None:
        _sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
    return _sparse_model

def vectoriser_sparse(texte: str) -> SparseVector:
    model = get_sparse_model()
    resultat = list(model.embed([texte]))[0]
    return SparseVector(
        indices=resultat.indices.tolist(),
        values=resultat.values.tolist()
    )

def rechercher_sparse(
    texte: str,
    category: str,
    sub_category: str,
    sub_sub_category: str,
    sub_sub_sub_category: str,
    degree: str,
    limite: int = 3
):
    client = get_client()
    vecteur_sparse = vectoriser_sparse(texte)

    filtre = Filter(must=[
        FieldCondition(key="category", match=MatchValue(value=category)),
        FieldCondition(key="sub_category", match=MatchValue(value=sub_category)),
        FieldCondition(key="sub_sub_category", match=MatchValue(value=sub_sub_category)),
        FieldCondition(key="sub_sub_sub_category", match=MatchValue(value=sub_sub_sub_category)),
        FieldCondition(key="degree", match=MatchValue(value=degree)),
    ])

    resultats = client.query_points(
        collection_name=COLLECTION_HYBRID,
        query=vecteur_sparse,
        using="sparse",
        query_filter=filtre,
        limit=limite
    ).points
    return resultats

if __name__ == "__main__":
    resultats = rechercher_sparse(
        "Écris l'article correct de ces noms.",
        category="Allemand", sub_category="Grammaire",
        sub_sub_category="Les noms", sub_sub_sub_category="Le genre des noms",
        degree="5/6"
    )
    for r in resultats:
        print(f"score={r.score:.4f} | {r.payload.get('consigne')}")