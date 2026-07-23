from pydantic import BaseModel

class DemandeExercice(BaseModel):
    category: str
    sub_category: str
    sub_sub_category: str
    sub_sub_sub_category: str
    degree: str
    type_exercice: str
    texte: str = ""
    limite: int = 3

class ExerciceResultat(BaseModel):
    methode: str
    score: float
    id_exercice: str | None
    consigne: str | None
    contenu: dict | list | None

class ExerciceGenere(BaseModel):
    consigne: str
    contenu: dict | list
    correction: dict | list

class DemandeCorrection(BaseModel):
    exercice: ExerciceGenere
    instruction: str
    sub_sub_sub_category: str = ""
    limite: int = 3