from sentence_transformers import SentenceTransformer
from src.config.config import EMBEDDING_MODEL, VECTOR_SIZE, CHAMPS_EMBEDDING

_model = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model

def normaliser_degree(degree) -> str:
    if isinstance(degree, list):
        return " ".join(str(d) for d in degree)
    return str(degree or "")

def construire_texte(exercice: dict) -> str:
    valeurs = []
    for champ in CHAMPS_EMBEDDING:
        val = exercice.get(champ, "")
        if champ == "degree":
            val = normaliser_degree(val)
        valeurs.append(str(val or ""))
    return " ".join(valeurs).strip()

def vectoriser(texte: str) -> list[float]:
    model = get_model()
    vecteur = model.encode(texte, normalize_embeddings=True)
    assert len(vecteur) == VECTOR_SIZE, f"Dimension incorrecte: {len(vecteur)}"
    return vecteur.tolist()