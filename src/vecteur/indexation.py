import json
import uuid
from src.database.client import get_client
from src.embedding.embedding import construire_texte, vectoriser
from src.config.config import (
    DATA_PATH, COLLECTION_NAME, BATCH_SIZE, SEUIL_DOUBLON_SEMANTIQUE
)
from qdrant_client.models import PointStruct

def charger_dataset():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)

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

#def est_doublon(client, vecteur) -> bool:
 #   resultats = client.query_points(
 #       collection_name=COLLECTION_NAME,
 #       query=vecteur,
 #       limit=1
  #  ).points
  #  return bool(resultats) and resultats[0].score > SEUIL_DOUBLON_SEMANTIQUE

def indexer():
    client = get_client()
    dataset = charger_dataset()
    print(f"Dataset chargé : {len(dataset)} exercices")

    points = []
    doublons = 0

    for i, exercice in enumerate(dataset):
        texte = construire_texte(exercice)
        vecteur = vectoriser(texte)

        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=vecteur,
            payload=construire_payload(exercice)
        ))

        if len(points) >= BATCH_SIZE:
            client.upsert(collection_name=COLLECTION_NAME, points=points)
            print(f"Batch inséré : {i+1}/{len(dataset)} traités")
            points = []

    if points:
        client.upsert(collection_name=COLLECTION_NAME, points=points)

    info = client.get_collection(COLLECTION_NAME)
    print(f"Terminé. Points insérés : {info.points_count} | Doublons rejetés : {doublons}")

if __name__ == "__main__":
    indexer()