import re

from src.config.config import TYPES_EXERCICE


def extraire_nombre_demande(texte_professeur: str) -> int | None:
    """Cherche un nombre de questions explicitement demandé par le professeur (ex: '6 questions')."""
    match = re.search(r'(\d+)\s*questions?', texte_professeur.lower())
    return int(match.group(1)) if match else None


def valider_structure(exercice) -> tuple[bool, str]:
    if not isinstance(exercice, dict):
        return False, "la réponse n'est pas un objet JSON"

    for champ in ("consigne", "contenu", "correction"):
        if champ not in exercice or not exercice[champ]:
            return False, f"champ '{champ}' manquant ou vide"

    if len(exercice["consigne"]) < 10:
        return False, "consigne trop courte (minimum 10 caractères)"

    if not isinstance(exercice["contenu"], (dict, list)):
        return False, "champ 'contenu' doit être un objet ou une liste"

    if not isinstance(exercice["correction"], (dict, list)):
        return False, "champ 'correction' doit être un objet ou une liste"

    return True, ""


def verifier_structure_type(exercice: dict, type_exercice: str | None) -> tuple[bool, str]:
    """
    Vérifie que la structure de "contenu" produite par le modèle correspond
    aux clés attendues du format_reference validé pour ce type_exercice
    (voir TYPES_EXERCICE dans config.py).

    Générique — AUCUN branchement par type ici. La fonction lit uniquement
    la donnée déjà validée manuellement dans config.py ; elle ne connaît rien
    des types eux-mêmes. Ajouter/modifier un type_reference dans config.py
    suffit à changer ce que cette fonction vérifie, sans toucher au code.

    Cas où la vérification est sautée (retourne toujours True) plutôt que de
    risquer une fausse alerte :
    - type_exercice absent/None (ex: relecture sans contexte de type)
    - type inconnu de TYPES_EXERCICE
    - format_reference pas encore validé pour ce type (None) — 2 types sur 13
      dans cet état au moment où cette fonction a été écrite ; comportement
      identique à avant pour eux
    - "contenu" du format_reference ou de l'exercice généré n'est pas un dict
      de premier niveau comparable (structure trop différente pour comparer
      des clés simplement)
    """
    if not type_exercice:
        return True, ""

    info = TYPES_EXERCICE.get(type_exercice)
    if not info:
        return True, ""

    format_reference = info.get("format_reference")
    if not format_reference:
        return True, ""

    contenu_attendu = format_reference.get("contenu")
    contenu_obtenu = exercice.get("contenu")

    if not isinstance(contenu_attendu, dict) or not isinstance(contenu_obtenu, dict):
        return True, ""

    cles_attendues = set(contenu_attendu.keys())
    cles_obtenues = set(contenu_obtenu.keys())

    if cles_attendues != cles_obtenues:
        return False, (
            f"structure de 'contenu' non conforme au type '{type_exercice}' : "
            f"clés attendues {sorted(cles_attendues)}, clés obtenues {sorted(cles_obtenues)}"
        )

    return True, ""


# ── Helpers structurels partagés ──────────────────────────────────────────
# Une seule façon de "lire" une structure contenu/correction dans tout le
# fichier — jamais de nom de clé supposé (le LLM choisit librement sa
# structure). Toutes les fonctions ci-dessous s'appuient sur ces deux helpers.

def _extraire_liste_items(valeur):
    """
    Retourne la liste d'éléments de premier niveau d'une structure :
    liste directe, ou dict avec un seul champ imbriqué qui contient la vraie
    liste, ou sinon les valeurs du dict lui-même.
    """
    if isinstance(valeur, list):
        return valeur
    if isinstance(valeur, dict):
        imbriques = [v for v in valeur.values() if isinstance(v, list) and len(v) > 0]
        if len(imbriques) == 1:
            return imbriques[0]
        return list(valeur.values())
    return []


def extraire_liste_items(valeur):
    """
    Alias public de _extraire_liste_items — même logique, exposée pour
    réutilisation hors de ce module (ex: rendu Streamlit) sans dupliquer
    la logique d'extraction de liste.
    """
    return _extraire_liste_items(valeur)


def _texte_principal(item) -> str:
    """Texte principal d'un élément de contenu — première chaîne rencontrée, hors 'choix'."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for cle, val in item.items():
            if cle != "choix" and isinstance(val, str):
                return val
    return str(item)


def _tous_les_textes(item) -> str:
    """
    Concatène TOUTES les valeurs textuelles d'un élément (hors 'choix'), pas
    seulement la première. Nécessaire pour détecter une réponse qui fuiterait
    dans n'importe quel champ de contenu — pas seulement le champ principal.

    Cas trouvé qui justifie cette fonction : {"phrase": "...", "réponse": "manger"}
    — la réponse était écrite directement dans un second champ de contenu,
    invisible pour _texte_principal qui ne regarde que le premier champ.
    """
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        textes = [v for cle, v in item.items() if cle != "choix" and isinstance(v, str)]
        return " ".join(textes)
    return str(item)


def compter_elements(valeur) -> int | None:
    """
    Compte le nombre d'éléments de premier niveau d'une structure (contenu OU
    correction), sans supposer aucun nom de clé fixe.

    - Liste directe → sa longueur.
    - Dict avec une ou plusieurs listes imbriquées → la longueur de la PLUS
      GRANDE d'entre elles. Une liste plus courte à côté (en-têtes de colonnes,
      pool d'options à choix) n'est pas le nombre d'éléments réel — c'est presque
      toujours la plus grande liste qui représente le vrai nombre de questions.
      Corrige deux bugs réels trouvés en test :
      1. Structure d'association à listes égales ("phrases"+"infinitifs", 6 et 6)
         → avant : comptait les clés (2) au lieu de 6.
      2. Structure tableau ("colonnes"=2 en-têtes, "lignes"=6 questions)
         → avant : comptait les clés (2) au lieu de 6, confirmé par le log
         ("2 question(s), 6 réponse(s)").
    - Sinon (pas de liste exploitable) → nombre de clés du dict lui-même
      (ex: dict indexé par numéro comme Test 5).
    """
    if isinstance(valeur, list):
        return len(valeur)

    if isinstance(valeur, dict):
        if not valeur:
            return None

        listes = [v for v in valeur.values() if isinstance(v, list) and len(v) > 0]
        if listes:
            return max(len(l) for l in listes)

        return len(valeur)

    return None


def verifier_diversite_choix(exercice: dict) -> tuple[bool, str]:
    """
    Pour toute question à choix (détectée par la présence d'une clé 'choix'),
    vérifie que les bonnes réponses ne sont pas toutes identiques — peu importe
    la matière, le sujet, ou le nom de clé utilisé par le LLM pour structurer
    la liste de questions (corrige un bug : la version précédente ne
    reconnaissait que la clé 'questions', ratant les structures comme
    'exercices' ou un dict indexé par numéro).
    """
    contenu = exercice.get("contenu")
    correction = exercice.get("correction")

    items_contenu = _extraire_liste_items(contenu)
    items_correction = _extraire_liste_items(correction)

    if not items_contenu or len(items_contenu) != len(items_correction):
        return True, ""  # structures non comparables terme à terme — pas de vérification fiable

    reponses = [
        str(items_correction[i]) for i, item in enumerate(items_contenu)
        if isinstance(item, dict) and "choix" in item
    ]

    if len(reponses) < 3:
        return True, ""  # pas assez de questions à choix pour juger la diversité

    if len(set(reponses)) == 1:
        return False, f"toutes les réponses aux questions à choix sont identiques ('{reponses[0]}') — aucune vraie discrimination testée"

    return True, ""


def verifier_reponse_non_visible(exercice: dict) -> tuple[bool, str]:
    """
    Vérifie qu'AUCUNE réponse n'apparaît déjà littéralement dans le texte de sa
    question associée — peu importe la matière, la langue, ou le type de
    transformation demandée (conjugaison→infinitif, genre allemand, figure de
    style...). Compare chaque élément de 'contenu' à SA réponse réelle dans
    'correction' (par position), pas une liste figée de mots suspects.

    Cas trouvé qui justifie cette généralisation : "Tu [vas ranger] ta chambre"
    avec réponse "ranger" — l'infinitif demandé était déjà écrit dans la
    périphrase.

    Les réponses purement numériques sont ignorées (un chiffre dans l'énoncé
    d'un calcul est souvent légitime — ex: "3x + 5 = 20" où 5 est un
    coefficient, pas une fuite de la réponse "x=5").

    Limite connue : si contenu/correction ne s'apparient pas terme à terme
    (longueurs différentes, structures trop divergentes), la fonction ne
    vérifie rien plutôt que de risquer une fausse alerte — pas encore
    validée sur un grand volume de cas réels.
    """
    contenu = exercice.get("contenu")
    correction = exercice.get("correction")

    items_contenu = _extraire_liste_items(contenu)
    items_correction = _extraire_liste_items(correction)

    if not items_contenu or len(items_contenu) != len(items_correction):
        return True, ""

    for item_c, item_r in zip(items_contenu, items_correction):
        texte_question = _tous_les_textes(item_c)
        reponse = item_r if isinstance(item_r, str) else _texte_principal(item_r)

        if not isinstance(reponse, str):
            continue
        reponse = reponse.strip()
        if len(reponse) < 2 or not reponse.replace(" ", "").isalpha():
            continue

        pattern = r'\b' + re.escape(reponse) + r'\b'
        if re.search(pattern, texte_question, re.IGNORECASE):
            return False, (
                f"la réponse '{reponse}' apparaît déjà littéralement dans l'énoncé "
                f"associé : '{texte_question[:60]}...'"
            )

    return True, ""


def valider_exercice_complet(exercice: dict, type_exercice: str | None = None) -> tuple[bool, str]:
    """
    Chaîne complète des validations déterministes. Utilisée à deux moments
    identiques dans le pipeline :
    1. sur l'exercice généré initialement
    2. sur l'exercice renvoyé par la relecture LLM (verifier_et_corriger) — pour
       s'assurer que la relecture n'a pas réintroduit un problème déjà écarté.

    type_exercice : optionnel — si fourni, ajoute la vérification structurelle
    contre le format_reference du type demandé (voir verifier_structure_type).
    Rétrocompatible : si omis, se comporte exactement comme avant ce check.
    """
    valide, motif = valider_structure(exercice)
    if not valide:
        return False, motif

    valide, motif = verifier_structure_type(exercice, type_exercice)
    if not valide:
        return False, motif

    valide, motif = verifier_diversite_choix(exercice)
    if not valide:
        return False, motif

    valide, motif = verifier_reponse_non_visible(exercice)
    if not valide:
        return False, motif

    return True, ""