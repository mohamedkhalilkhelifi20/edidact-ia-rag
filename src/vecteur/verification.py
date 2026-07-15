from src.database.client import get_client
from src.embedding.embedding import vectoriser
from src.config.config import COLLECTION_NAME

def verifier_etat():
    client = get_client()
    info = client.get_collection(COLLECTION_NAME)
    print(f"Collection : {COLLECTION_NAME}")
    print(f"Status : {info.status.name}")
    print(f"Points indexés : {info.points_count}")

def tester_recherche(texte_recherche: str, limite: int = 3):
    client = get_client()
    vecteur = vectoriser(texte_recherche)

    resultats = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vecteur,
        limit=limite
    ).points

    print(f"\nRecherche : '{texte_recherche}'")
    for r in resultats:
        print(f"  score={r.score:.4f} | consigne={r.payload.get('consigne','')[:60]}")

from qdrant_client.models import Filter, FieldCondition, MatchValue

def tester_recherche_filtree(texte_recherche: str, category: str, degree: str, limite: int = 3):
    client = get_client()
    vecteur = vectoriser(texte_recherche)

    filtre = Filter(
        must=[
            FieldCondition(key="category", match=MatchValue(value=category)),
            FieldCondition(key="degree", match=MatchValue(value=degree)),
        ]
    )

    resultats = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vecteur,
        query_filter=filtre,
        limit=limite
    ).points

    print(f"\nRecherche filtrée : '{texte_recherche}' | category={category} | degree={degree}")
    if not resultats:
        print("  Aucun résultat.")
    for r in resultats:
        print(f"  score={r.score:.4f} | consigne={r.payload.get('consigne','')[:60]}")

if __name__ == "__main__":
    verifier_etat()
    tester_recherche("exercice de mathématiques sur les fractions niveau 9H")
    tester_recherche_filtree("fractions", category="Français", degree="9/10")