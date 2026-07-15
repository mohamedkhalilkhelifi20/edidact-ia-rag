from qdrant_client.models import VectorParams, Distance, SparseVectorParams, PayloadSchemaType
from src.database.client import get_client
from src.config.config import COLLECTION_HYBRID, VECTOR_SIZE, CHAMPS_PAYLOAD_INDEXES


def creer_collection_hybrid():
    client = get_client()

    if not client.collection_exists(COLLECTION_HYBRID):
        client.create_collection(
            collection_name=COLLECTION_HYBRID,
            vectors_config={
                "dense": VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)},
            sparse_vectors_config={"sparse": SparseVectorParams()}
        )
        print("Collection hybrid créée.")
    else:
        print("Collection hybrid existe déjà.")

    for champ in CHAMPS_PAYLOAD_INDEXES:
        client.create_payload_index(
            collection_name=COLLECTION_HYBRID,
            field_name=champ,
            field_schema=PayloadSchemaType.KEYWORD
        )

    info = client.get_collection(COLLECTION_HYBRID)
    print(f"État : status={info.status.name}, points={info.points_count}")

if __name__ == "__main__":
    creer_collection_hybrid()