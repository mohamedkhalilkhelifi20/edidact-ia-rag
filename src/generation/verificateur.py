import json
from src.generation.client_llm import appeler_modele


def verifier_et_corriger(
    exercice: dict, demande_originale: str = "", sub_sub_sub_category: str = "", limite: int = None
) -> dict:
    bloc_demande = ""
    if demande_originale.strip():
        bloc_demande = f"""
# DEMANDE ORIGINALE DU PROFESSEUR
"{demande_originale}"
Vérifie que l'exercice respecte toutes les instructions précises de cette demande
(nombre de questions, longueur, répartition par compétence). Corrige si nécessaire.
"""

    prompt = f"""# TÂCHE
Relis cet exercice pédagogique et vérifie sa qualité :

{json.dumps(exercice, ensure_ascii=False, indent=2)}
{bloc_demande}
# POINTS DE VÉRIFICATION
1. Cohérence : la consigne décrit-elle fidèlement le contenu réel ?
2. Complétude : chaque question a-t-elle bien une réponse ?
3. Consigne simple : une seule action claire, sans détail redondant avec le visible ?
4. Choix variés : dans un QCM, les options sont-elles pensées par question, pas recopiées ?
5. Exactitude factuelle : chaque réponse qui identifie un élément du texte
   (type de phrase, figure de style, temps verbal, nature du mot) correspond-elle
   vraiment à la réalité du texte ? (ex : une phrase "exclamative" doit contenir
   un vrai point d'exclamation)
6. VALEUR PÉDAGOGIQUE RÉELLE : cet exercice fait-il vraiment réfléchir ou calculer
   l'élève, ou est-ce une tâche mécanique sans réel apprentissage ? Le sujet
   "{sub_sub_sub_category}" est-il vraiment testé en profondeur, ou seulement
   effleuré superficiellement ? Si l'exercice est pédagogiquement faible, RECONSTRUIS-le
   avec une approche plus exigeante.

# CONSIGNE
Si tout est déjà correct, renvoie l'exercice EXACTEMENT tel quel.
Sinon, corrige uniquement ce qui doit l'être.

# FORMAT DE SORTIE
JSON complet corrigé, sans texte avant, sans balises markdown."""

    texte_propre, statut = appeler_modele(
        prompt, reasoning_effort="medium", verbosity="low", etape="relecture", limite=limite
    )

    if not texte_propre:
        raise RuntimeError(f"Relecture LLM a renvoyé un contenu vide (statut='{statut}')")

    try:
        return json.loads(texte_propre)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Relecture LLM a produit un JSON invalide : {e}")