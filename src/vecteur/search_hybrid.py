from src.embedding.embedding import vectoriser as vectoriser_dense
from src.vecteur.search_sparse import vectoriser_sparse
from src.database.client import get_client
from src.config.config import COLLECTION_HYBRID
from qdrant_client.models import FusionQuery, Fusion, Prefetch, Filter, FieldCondition, MatchValue


def rechercher_hybrid(
    texte: str,
    category: str,
    sub_category: str,
    sub_sub_category: str,
    sub_sub_sub_category: str,
    degree: str,
    limite: int = 3
):
    client = get_client()
    vecteur_dense = vectoriser_dense(texte)
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
        prefetch=[
            Prefetch(query=vecteur_dense, using="dense", limit=20, filter=filtre),
            Prefetch(query=vecteur_sparse, using="sparse", limit=20, filter=filtre),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=limite
    ).points
    return resultats

