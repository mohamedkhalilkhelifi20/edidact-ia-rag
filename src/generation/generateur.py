import json
from src.generation.client_llm import appeler_modele
from src.generation.prompt_builder import construire_prompt
from src.generation.validation import (
    valider_exercice_complet,
    compter_elements,
    extraire_nombre_demande,
)
from src.generation.echec_logger import logger_echec

from src.generation.verificateur import verifier_et_corriger


def generer_questions_seules(demande_professeur: dict, exemples: list[dict]) -> dict:
    """Étape 1 : génère consigne + contenu (texte, questions), sans les réponses."""
    prompt = construire_prompt(demande_professeur, exemples)
    prompt += """

EXIGENCE DE STRUCTURE : pour un classement ou une association, chaque élément doit
rester directement lié à sa réponse dans la structure choisie — jamais séparé dans
des listes indépendantes qui obligeraient à recompter pour les relier.

Ne génère PAS de correction à cette étape. Produis uniquement consigne + contenu."""

    limite = demande_professeur.get("limite")
    type_exercice = demande_professeur.get("type_exercice")

    texte_propre, statut = appeler_modele(
        prompt, reasoning_effort="high", verbosity="low", etape="questions",
        limite=limite, type_exercice=type_exercice,
    )

    if not texte_propre:
        raise RuntimeError(
            f"Génération des questions a renvoyé un contenu vide (statut='{statut}')"
        )

    try:
        return json.loads(texte_propre)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Génération des questions a produit un JSON invalide : {e}")


def generer_reponses(exercice_sans_correction: dict, limite: int = None, type_exercice: str = None) -> dict:
    prompt = f"""# TÂCHE
Voici un exercice avec ses questions, sans les réponses :

{json.dumps(exercice_sans_correction, ensure_ascii=False, indent=2)}

# EXIGENCES
- Compte le nombre exact de questions avant de répondre
- Fournis EXACTEMENT le même nombre de réponses, dans le même ordre
- Chaque réponse doit être vérifiable factuellement contre le texte/contenu fourni
- N'invente jamais une classification qui ne correspond pas à la réalité du texte

# FORMAT DE SORTIE
JSON complet (consigne, contenu, correction) — garde "consigne" et "contenu" identiques.
Dans "correction", uniquement la réponse finale. Sans texte autour, sans balises markdown."""

    texte_propre, statut = appeler_modele(
        prompt, reasoning_effort="high", verbosity="low", etape="reponses",
        limite=limite, type_exercice=type_exercice,
    )

    if not texte_propre:
        raise RuntimeError(
            f"Génération des réponses a renvoyé un contenu vide (statut='{statut}')"
        )

    try:
        return json.loads(texte_propre)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Génération des réponses a produit un JSON invalide : {e}")


def generer_exercice(demande_professeur: dict, exemples: list[dict], max_tentatives: int = 3) -> dict:
    """
    Génération en 2 étapes (questions, puis réponses), avec chaîne de vérifications :
    1. Structure correcte (clés présentes)
    2. Diversité des réponses (pas toutes identiques)
    3. Réponse non visible dans l'énoncé (vérification textuelle déterministe)
    4. Nombre de questions conforme à la demande explicite du professeur (si chiffrée)
    5. Comptage questions/réponses interne — filtre rapide, non bloquant en dernière tentative
    6. Relecture LLM finale (cohérence + complétude + fidélité à la demande originale),
       elle-même re-passée par la chaîne de validation (1-3) avant d'être acceptée —
       la relecture ne doit jamais réintroduire un problème déjà écarté.
    """
    texte_demande = demande_professeur.get("texte", "")
    n_questions_demandees = extraire_nombre_demande(texte_demande)
    limite = demande_professeur.get("limite")
    type_exercice = demande_professeur.get("type_exercice")

    # Étape 1 : génération des questions, avec son propre retry
    exercice_sans_correction = None
    for tentative_q in range(1, max_tentatives + 1):
        try:
            exercice_sans_correction = generer_questions_seules(demande_professeur, exemples)
            break
        except RuntimeError as e:
            motif = str(e)
            print(f"[génération questions, tentative {tentative_q}/{max_tentatives}] échec : {motif}")
            logger_echec(etape="questions", tentative=tentative_q, motif=motif, demande=demande_professeur)

    if exercice_sans_correction is None:
        raise RuntimeError("Échec de génération des questions après plusieurs tentatives.")

    motif_erreur = ""

    for tentative in range(1, max_tentatives + 1):
        try:
            exercice = generer_reponses(exercice_sans_correction, limite=limite, type_exercice=type_exercice)
        except RuntimeError as e:
            motif_erreur = str(e)
            print(f"[tentative {tentative}/{max_tentatives}] échec : {motif_erreur}")
            logger_echec(etape="reponses", tentative=tentative, motif=motif_erreur, demande=demande_professeur)
            continue

        # 1-3. Structure + conformité au type + diversité choix + réponse non visible
        valide, motif = valider_exercice_complet(exercice, type_exercice=type_exercice)
        if not valide:
            motif_erreur = motif
            print(f"[tentative {tentative}/{max_tentatives}] échec : {motif_erreur}")
            logger_echec(etape="validation", tentative=tentative, motif=motif_erreur, demande=demande_professeur)
            continue

        n_questions = compter_elements(exercice.get("contenu"))
        n_reponses = compter_elements(exercice.get("correction"))

        # 4. Nombre exact de questions demandé explicitement par le professeur
        if n_questions_demandees is not None and n_questions is not None:
            if n_questions != n_questions_demandees:
                motif_erreur = (
                    f"nombre de questions incorrect : {n_questions} générées, "
                    f"{n_questions_demandees} demandées explicitement par le professeur"
                )
                print(f"[tentative {tentative}/{max_tentatives}] échec : {motif_erreur}")
                logger_echec(etape="nombre_questions", tentative=tentative, motif=motif_erreur, demande=demande_professeur)
                continue

        # 5. Comptage questions/réponses interne — non bloquant à la dernière tentative
        comptage_incoherent = (
            n_questions is not None and n_reponses is not None and n_questions != n_reponses
        )

        if comptage_incoherent and tentative < max_tentatives:
            motif_erreur = f"nombre incohérent : {n_questions} question(s), {n_reponses} réponse(s)"
            print(f"[tentative {tentative}/{max_tentatives}] échec : {motif_erreur}")
            logger_echec(etape="comptage", tentative=tentative, motif=motif_erreur, demande=demande_professeur)
            continue

        # 6. Relecture LLM finale — cohérence + complétude + fidélité à la demande originale
        try:
            exercice_corrige = verifier_et_corriger(
                exercice,
                demande_originale=texte_demande,
                sub_sub_sub_category=demande_professeur.get("sub_sub_sub_category", ""),
                limite=limite,
                type_exercice=type_exercice,
            )
            valide_apres_relecture, motif_relecture = valider_exercice_complet(
                exercice_corrige, type_exercice=type_exercice
            )
            if valide_apres_relecture:
                return exercice_corrige

            print(f"[relecture] rejetée, réintroduit un problème : {motif_relecture}")
            logger_echec(
                etape="relecture_rejetee",
                tentative=tentative,
                motif=motif_relecture,
                demande=demande_professeur,
            )
        except Exception as e:
            print(f"[relecture] échec technique : {e}")
            logger_echec(
                etape="relecture_technique",
                tentative=tentative,
                motif=str(e),
                demande=demande_professeur,
            )

        if not comptage_incoherent:
            return exercice

        motif_erreur = f"nombre incohérent persistant : {n_questions} question(s), {n_reponses} réponse(s)"

    raise RuntimeError(f"Échec de génération après {max_tentatives} tentatives. Dernier motif : {motif_erreur}")