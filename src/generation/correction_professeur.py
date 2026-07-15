import json
from src.generation.client_llm import appeler_modele
from src.generation.validation import valider_exercice_complet
from src.generation.correction_logger import logger_correction


def corriger_exercice(
    exercice: dict,
    instruction: str,
    sub_sub_sub_category: str = "",
    limite: int = None,
) -> dict:
    """
    Corrige un exercice existant selon une instruction libre du professeur
    (pattern "Human-in-the-loop" / Plan-Confirm-Execute) :
    1. PLAN + EXECUTE : le modèle reçoit l'exercice ACTUEL complet (pas
       l'original — s'il y a déjà eu une correction précédente, c'est cette
       version qui repart) + l'instruction, et renvoie une version corrigée.
    2. CONFIRM : la version corrigée repasse par la même chaîne de validation
       déterministe que le reste du pipeline (valider_exercice_complet) avant
       d'être acceptée.

    Si la validation échoue, on lève une erreur explicite plutôt que de
    renvoyer une version dégradée — c'est à l'appelant (route API, Streamlit)
    de décider de garder l'ancienne version affichée.
    """
    prompt = f"""# TÂCHE
Voici un exercice pédagogique existant :

{json.dumps(exercice, ensure_ascii=False, indent=2)}

# INSTRUCTION DU PROFESSEUR
"{instruction}"

# CONSIGNE
Applique UNIQUEMENT ce que demande l'instruction ci-dessus. Ne change rien
d'autre dans l'exercice — ni la structure, ni les parties non concernées par
la demande. Si l'instruction est ambiguë, applique l'interprétation la plus
raisonnable pour un exercice de "{sub_sub_sub_category}".

# FORMAT DE SORTIE
JSON complet corrigé (consigne, contenu, correction), sans texte avant, sans
balises markdown."""

    texte_propre, statut = appeler_modele(
        prompt, reasoning_effort="medium", verbosity="low", etape="correction_professeur", limite=limite
    )

    if not texte_propre:
        logger_correction(instruction=instruction, acceptee=False, motif=f"contenu vide (statut='{statut}')")
        raise RuntimeError(f"Correction a renvoyé un contenu vide (statut='{statut}')")

    try:
        exercice_corrige = json.loads(texte_propre)
    except json.JSONDecodeError as e:
        logger_correction(instruction=instruction, acceptee=False, motif=f"JSON invalide : {e}")
        raise RuntimeError(f"Correction a produit un JSON invalide : {e}")

    valide, motif = valider_exercice_complet(exercice_corrige)
    if not valide:
        logger_correction(instruction=instruction, acceptee=False, motif=motif)
        raise RuntimeError(f"Correction rejetée après validation : {motif}")

    logger_correction(instruction=instruction, acceptee=True)
    return exercice_corrige