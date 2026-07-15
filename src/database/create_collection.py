from qdrant_client.models import VectorParams, Distance, PayloadSchemaType
from src.database.client import get_client
from src.config.config import COLLECTION_NAME, VECTOR_SIZE, CHAMPS_PAYLOAD_INDEXES

def create_collection():
    client = get_client()

    if client.collection_exists(COLLECTION_NAME):
        print(f"Collection '{COLLECTION_NAME}' existe déjà — rien à créer.")
        return
    
     # 1. Créer la collection vide avec vecteur + distance
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
    )

     # 2. Vérifier l'état avant d'aller plus loin
    info = client.get_collection(COLLECTION_NAME)
    assert info.status.name == "GREEN", f"Collection en erreur: {info.status}"
    assert info.points_count == 0, "Collection non vide dès la création — anormal"
    print(f"Collection créée : status={info.status.name}, points={info.points_count}")

    # 3. Créer les index de payload
    for champ in CHAMPS_PAYLOAD_INDEXES:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=champ,
            field_schema=PayloadSchemaType.KEYWORD
        )
        print(f"Index créé sur le champ : {champ}")

    # 4. Vérification finale
    info_finale = client.get_collection(COLLECTION_NAME)
    print(f"Collection prête : status={info_finale.status.name}, points={info_finale.points_count}")

if __name__ == "__main__":
    create_collection()
