from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from src.config.config import QDRANT_HOST, QDRANT_PORT, COLLECTION_HYBRID
from src.database.create_collection_hybrid import creer_collection_hybrid
from src.database.client import get_client
import time

source = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
creer_collection_hybrid()
dest = get_client()

total_migres = 0
offset = None

while True:
    records, offset = source.scroll(
        collection_name=COLLECTION_HYBRID,
        limit=100,
        with_vectors=True,
        with_payload=True,
        offset=offset,
    )
    if not records:
        break

    points = [PointStruct(id=r.id, vector=r.vector, payload=r.payload) for r in records]

    for tentative in range(3):
        try:
            dest.upsert(collection_name=COLLECTION_HYBRID, points=points)
            break
        except Exception as e:
            print(f"Timeout, nouvelle tentative dans 3s... ({e})")
            time.sleep(3)
            if tentative == 2:
                raise

    total_migres += len(points)
    print(f"{total_migres} points migrés...")
    if offset is None:
        break

print(f"\nMigration terminée : {total_migres} exercices traités.")
print(f"Vérification — points sur le cloud : {dest.count(COLLECTION_HYBRID).count}")