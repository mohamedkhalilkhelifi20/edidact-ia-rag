import json, uuid
from src.database.client import get_client
from src.vecteur.search_dense import rechercher_dense
from src.embedding.embedding import vectoriser
from src.vecteur.search_sparse import vectoriser_sparse
from src.config.config import DATA_PATH, BATCH_SIZE,COLLECTION_HYBRID
from qdrant_client.models import PointStruct

def construire_payload(exercice: dict) -> dict:
    return {
        "id_exercice": exercice.get("id"),
        "category": exercice.get("category"),
        "sub_category": exercice.get("sub_category"),
        "sub_sub_category": exercice.get("sub_sub_category"),
        "sub_sub_sub_category": exercice.get("sub_sub_sub_category"),
        "consigne": exercice.get("consigne"),
        "contenu": exercice.get("contenu"),
        "degree": exercice.get("degree"),
    }

def indexer_hybrid():
    client = get_client()
    with open(DATA_PATH, encoding="utf-8") as f:
        dataset = json.load(f)
    print(f"Dataset chargé : {len(dataset)} exercices")

    points = []
    for i, exercice in enumerate(dataset):
        texte = exercice.get("consigne", "")
        vecteur_dense = vectoriser(texte)
        vecteur_sparse = vectoriser_sparse(texte)

        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector={"dense": vecteur_dense, "sparse": vecteur_sparse},
            payload=construire_payload(exercice)
        ))

        if len(points) >= BATCH_SIZE:
            client.upsert(collection_name=COLLECTION_HYBRID, points=points)
            print(f"Batch inséré : {i+1}/{len(dataset)}")
            points = []

    if points:
        client.upsert(collection_name=COLLECTION_HYBRID, points=points)

    info = client.get_collection(COLLECTION_HYBRID)
    print(f"Terminé. Points : {info.points_count}")

if __name__ == "__main__":
    indexer_hybrid()
