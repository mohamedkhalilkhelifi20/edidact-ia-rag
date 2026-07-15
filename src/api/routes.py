from fastapi import APIRouter, HTTPException
from src.api.schemas import DemandeExercice, ExerciceResultat, ExerciceGenere, DemandeCorrection
from src.vecteur.search import rechercher
from src.generation.pipeline import generer_nouvel_exercice
from src.generation.correction_professeur import corriger_exercice

router = APIRouter()


@router.post("/rechercher", response_model=list[ExerciceResultat])
def rechercher_exercice(demande: DemandeExercice):
    try:
        return rechercher(
            category=demande.category,
            sub_category=demande.sub_category,
            sub_sub_category=demande.sub_sub_category,
            sub_sub_sub_category=demande.sub_sub_sub_category,
            degree=demande.degree,
            texte=demande.texte,
            limite=demande.limite,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Erreur recherche: {e}")


@router.post("/generer", response_model=ExerciceGenere)
def generer_exercice_endpoint(demande: DemandeExercice):
    try:
        return generer_nouvel_exercice(
            category=demande.category,
            sub_category=demande.sub_category,
            sub_sub_category=demande.sub_sub_category,
            sub_sub_sub_category=demande.sub_sub_sub_category,
            degree=demande.degree,
            texte=demande.texte,
            limite=demande.limite,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur inattendue: {e}")


@router.post("/corriger", response_model=ExerciceGenere)
def corriger_exercice_endpoint(demande: DemandeCorrection):
    """
    Corrige un exercice existant selon une instruction libre du professeur.
    Le professeur envoie l'exercice ACTUEL (pas forcément l'original — peut
    déjà être une version corrigée précédemment) + son instruction.
    """
    try:
        return corriger_exercice(
            exercice=demande.exercice.model_dump(),
            instruction=demande.instruction,
            sub_sub_sub_category=demande.sub_sub_sub_category,
            limite=demande.limite,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur inattendue: {e}")