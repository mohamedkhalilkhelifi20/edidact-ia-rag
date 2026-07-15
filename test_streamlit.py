"""
Banc de test Streamlit pour le pipeline de génération EdiDact.

Lancer avec : streamlit run banc_test_streamlit.py
"""

import time
import json
import threading
from collections import Counter
import streamlit as st
from qdrant_client import QdrantClient
from src.config.config import QDRANT_HOST, QDRANT_PORT, COLLECTION_HYBRID, LOG_EXEMPLES_MONTRES
from src.generation.pipeline import generer_nouvel_exercice
from src.generation.correction_professeur import corriger_exercice
from src.generation.validation import compter_elements

st.set_page_config(page_title="EdiDact — Banc de test", layout="centered", page_icon="📘")

CHAMPS_FILTRE = ["degree", "category", "sub_category", "sub_sub_category", "sub_sub_sub_category"]

CARACTERES_MARKDOWN_SPECIAUX = ["\\", "`", "*", "_", "{", "}", "[", "]", "(", ")", "#", "+", "-", "!", ">", "<"]


# ══════════════════════════════════════════════════════════════════════
# Utilitaires d'affichage
# ══════════════════════════════════════════════════════════════════════

def echapper_markdown(texte) -> str:
    """
    Neutralise les caractères ayant une signification spéciale en Markdown
    (*, _, #, >, <, `, -...) pour que le contenu généré par le modèle
    s'affiche toujours tel quel, jamais mal interprété par st.markdown.

    Bug corrigé : un choix de réponse valant exactement ">" (ex: exercice de
    comparaison de nombres) disparaissait à l'affichage — Markdown interprète
    "- >" comme une citation imbriquée dans une liste, pas comme le caractère
    littéral ">".
    """
    if not isinstance(texte, str):
        texte = str(texte)
    for caractere in CARACTERES_MARKDOWN_SPECIAUX:
        texte = texte.replace(caractere, "\\" + caractere)
    return texte


def est_question_a_choix(valeur) -> bool:
    return isinstance(valeur, dict) and isinstance(valeur.get("choix"), list)


def rendre_question(question: dict, numero: int) -> None:
    """
    Affiche une question, numérotée. Le texte principal peut être sous
    n'importe quelle clé ('question', 'phrase', 'énoncé'...) — on prend la
    première chaîne trouvée, hors 'choix'. Les choix peuvent être une liste
    (rendus en options) ou toute autre valeur (rendue telle quelle) — la
    numérotation ne dépend JAMAIS de la présence d'une clé 'choix' précise.
    """
    texte_question = ""
    for cle, valeur in question.items():
        if cle != "choix" and not isinstance(valeur, (list, dict)):
            texte_question = str(valeur)
            break

    st.markdown(f"**{numero}. {echapper_markdown(texte_question)}**")

    choix = question.get("choix")
    if isinstance(choix, list):
        for c in choix:
            st.markdown(f"- {echapper_markdown(c)}")
    elif choix is not None:
        st.markdown(echapper_markdown(choix))

    # Afficher les autres champs éventuels (hors texte principal déjà montré et 'choix')
    for cle, valeur in question.items():
        if cle == "choix" or valeur == texte_question:
            continue
        if isinstance(valeur, str):
            st.markdown(echapper_markdown(valeur))


def rendre_valeur(valeur) -> None:
    """Rendu récursif générique d'une structure contenu/correction — ne
    suppose jamais de nom de clé fixe, s'adapte à la forme réelle reçue.
    TOUT élément d'une liste est numéroté, qu'il ait ou non une clé 'choix' —
    corrige un bug où les questions sans clé 'choix' en liste (ex: options
    écrites comme une chaîne "46 / 64" au lieu d'une vraie liste) n'étaient
    jamais numérotées."""
    if valeur is None:
        return
    if isinstance(valeur, (str, int, float)):
        st.markdown(echapper_markdown(valeur))
        return
    if isinstance(valeur, list):
        compteur = 0
        for item in valeur:
            compteur += 1
            if isinstance(item, dict):
                rendre_question(item, compteur)
            else:
                st.markdown(f"**{compteur}.** {echapper_markdown(item)}")
        return
    if isinstance(valeur, dict):
        for cle, val in valeur.items():
            if cle == "texte" and isinstance(val, str):
                st.info(echapper_markdown(val))
            elif est_question_a_choix(val):
                rendre_question(val, 1)
            elif isinstance(val, (list, dict)):
                rendre_valeur(val)
            else:
                st.markdown(echapper_markdown(val))
        return


def afficher_exercice(exercice: dict) -> None:
    """Rendu complet d'un exercice — réutilisé partout (résultat principal,
    bulles de chat) pour qu'un seul endroit gère la présentation."""
    with st.container(border=True):
        st.markdown(f"### {echapper_markdown(exercice.get('consigne', ''))}")
        rendre_valeur(exercice.get("contenu"))

        with st.expander("✅ Afficher la correction"):
            rendre_valeur(exercice.get("correction"))

        with st.expander("🔧 JSON brut (avancé)"):
            st.json(exercice)


def resumer_changement(ancien: dict, nouveau: dict) -> str:
    """Résumé court de ce qui a changé entre deux versions — basé sur
    compter_elements (générique), pas sur un simple 'corrigé' muet."""
    lignes = []

    if ancien.get("consigne", "") != nouveau.get("consigne", ""):
        lignes.append("consigne modifiée")

    n_avant = compter_elements(ancien.get("contenu"))
    n_apres = compter_elements(nouveau.get("contenu"))
    if n_avant is not None and n_apres is not None and n_avant != n_apres:
        signe = "+" if n_apres > n_avant else ""
        lignes.append(f"contenu {n_avant} → {n_apres} ({signe}{n_apres - n_avant})")

    if not lignes:
        return "Correction appliquée (détail ci-dessous)."
    return "Correction appliquée — " + ", ".join(lignes) + "."


@st.cache_data
def charger_combinaisons() -> dict:
    """
    Construit l'arbre des combinaisons réellement indexées dans Qdrant :
    degree -> category -> sub_category -> sub_sub_category -> {sub_sub_sub_category}.
    Certains points ont un payload malformé (champ stocké comme liste au lieu
    d'une chaîne) — normalisés ici plutôt que de planter.
    """
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    arbre: dict = {}
    offset = None
    points_ignores = 0

    def normaliser(valeur):
        if isinstance(valeur, str):
            return valeur
        if isinstance(valeur, list) and len(valeur) == 1 and isinstance(valeur[0], str):
            return valeur[0]
        return None

    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION_HYBRID, limit=500, offset=offset,
            with_payload=CHAMPS_FILTRE, with_vectors=False,
        )
        for point in points:
            payload = point.payload or {}
            valeurs = [normaliser(payload.get(c)) for c in CHAMPS_FILTRE]
            if not all(valeurs):
                points_ignores += 1
                continue
            degree, category, sub_category, sub_sub_category, sub_sub_sub_category = valeurs
            (arbre.setdefault(degree, {}).setdefault(category, {})
                  .setdefault(sub_category, {}).setdefault(sub_sub_category, set())
                  .add(sub_sub_sub_category))
        if offset is None:
            break

    if points_ignores > 0:
        print(f"[banc_test_streamlit] {points_ignores} point(s) Qdrant ignoré(s) — payload malformé.")
    return arbre


def charger_historique_exemples() -> list[dict]:
    try:
        with open(LOG_EXEMPLES_MONTRES, "r", encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]
    except FileNotFoundError:
        return []


# ══════════════════════════════════════════════════════════════════════
# Page
# ══════════════════════════════════════════════════════════════════════

st.title("📘 Banc de test — génération d'exercice")

onglet_config, onglet_exercice, onglet_diagnostic = st.tabs(
    ["⚙️ Configurer", "📄 Exercice", "🔍 Diagnostic"]
)

# ── Onglet 1 : configuration et génération ───────────────────────────
with onglet_config:
    try:
        arbre = charger_combinaisons()
    except Exception as e:
        st.error(f"Impossible de charger les combinaisons depuis Qdrant : {e}")
        st.stop()

    if not arbre:
        st.error("Qdrant ne renvoie aucune combinaison — la collection est-elle bien indexée ?")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        degree = st.selectbox("Degree", sorted(arbre.keys()))
        options_category = sorted(arbre[degree].keys())
        category = st.selectbox("Category", options_category)
        options_sub_category = sorted(arbre[degree][category].keys())
        sub_category = st.selectbox("Sub category", options_sub_category)
    with col2:
        options_sub_sub_category = sorted(arbre[degree][category][sub_category].keys())
        sub_sub_category = st.selectbox("Sub sub category", options_sub_sub_category)
        options_sub_sub_sub_category = sorted(arbre[degree][category][sub_category][sub_sub_category])
        sub_sub_sub_category = st.selectbox("Sub sub sub category", options_sub_sub_sub_category)

    with st.form("formulaire_generation"):
        texte = st.text_area(
            "Texte (demande libre du professeur)",
            placeholder="Optionnel — instructions précises (nombre de questions, thème...)",
            help=(
                "Optionnel. Laisse vide pour un exercice standard sur le sujet choisi. "
                "Utile pour : préciser un thème, imposer un nombre exact de questions, "
                "ou détailler une répartition par compétence."
            ),
        )
        with st.expander("Options avancées"):
            limite = st.number_input("Limite (exemples Qdrant)", min_value=1, max_value=10, value=3)

        valider = st.form_submit_button("Générer un exercice", use_container_width=True)

    if valider:
        resultat_thread = {}

        def executer_generation():
            try:
                resultat_thread["exercice"] = generer_nouvel_exercice(
                    category=category, sub_category=sub_category,
                    sub_sub_category=sub_sub_category,
                    sub_sub_sub_category=sub_sub_sub_category,
                    degree=degree, texte=texte, limite=int(limite),
                )
            except Exception as e:
                resultat_thread["erreur"] = e

        fil = threading.Thread(target=executer_generation)
        debut = time.time()
        fil.start()

        indicateur = st.empty()
        while fil.is_alive():
            indicateur.markdown(f"⏳ Génération en cours… ({time.time() - debut:.0f}s)")
            time.sleep(0.3)
        fil.join()
        indicateur.empty()

        duree = time.time() - debut
        erreur = resultat_thread.get("erreur")
        exercice = resultat_thread.get("exercice")

        if isinstance(erreur, ValueError):
            st.error(f"Aucun exemple trouvé : {erreur}")
        elif isinstance(erreur, RuntimeError):
            st.error(f"Échec de génération : {erreur}")
        elif erreur is not None:
            st.error(f"Erreur inattendue : {erreur}")
        elif exercice:
            st.session_state["exercice_actuel"] = exercice
            st.session_state["historique_chat"] = []
            st.session_state["derniere_duree"] = duree
            st.session_state["limite_courante"] = int(limite)
            st.session_state["sujet_courant"] = sub_sub_sub_category
            st.success("✓ Exercice généré — va voir l'onglet **📄 Exercice**.")

# ── Onglet 2 : exercice actuel + chat de correction ──────────────────
with onglet_exercice:
    if "exercice_actuel" not in st.session_state:
        st.info("Génère un exercice depuis l'onglet **⚙️ Configurer**.")
    else:
        st.caption(f"Généré en {st.session_state.get('derniere_duree', 0):.1f}s")
        afficher_exercice(st.session_state["exercice_actuel"])

        st.divider()
        st.markdown("**💬 Demander une correction**")

        for role, message, exercice_lie in st.session_state.get("historique_chat", []):
            with st.chat_message(role):
                st.markdown(message)
                if exercice_lie is not None:
                    afficher_exercice(exercice_lie)

        instruction = st.chat_input("Ex: remplace la question 3, elle est trop facile")

        if instruction:
            st.session_state.setdefault("historique_chat", []).append(("user", instruction, None))
            with st.chat_message("user"):
                st.markdown(instruction)

            resultat_correction = {}
            # Capturé AVANT le thread — session_state n'est pas fiable à lire
            # depuis l'intérieur d'un thread séparé.
            exercice_pour_correction = st.session_state["exercice_actuel"]
            sujet_pour_correction = st.session_state.get("sujet_courant", "")
            limite_pour_correction = st.session_state.get("limite_courante", 3)

            def executer_correction():
                try:
                    resultat_correction["exercice"] = corriger_exercice(
                        exercice=exercice_pour_correction,
                        instruction=instruction,
                        sub_sub_sub_category=sujet_pour_correction,
                        limite=limite_pour_correction,
                    )
                except Exception as e:
                    resultat_correction["erreur"] = e

            fil_correction = threading.Thread(target=executer_correction)
            fil_correction.start()

            with st.chat_message("assistant"):
                indicateur_correction = st.empty()
                debut_correction = time.time()
                while fil_correction.is_alive():
                    indicateur_correction.markdown(f"⏳ Correction en cours… ({time.time() - debut_correction:.0f}s)")
                    time.sleep(0.3)
                fil_correction.join()

                erreur_correction = resultat_correction.get("erreur")
                nouvel_exercice = resultat_correction.get("exercice")

                if erreur_correction is not None:
                    message_reponse = f"❌ Correction impossible : {erreur_correction}"
                    indicateur_correction.markdown(message_reponse)
                    exercice_a_stocker = None
                else:
                    resume = resumer_changement(exercice_pour_correction, nouvel_exercice)
                    message_reponse = f"✓ {resume}"
                    indicateur_correction.markdown(message_reponse)
                    afficher_exercice(nouvel_exercice)
                    st.session_state["exercice_actuel"] = nouvel_exercice
                    exercice_a_stocker = nouvel_exercice

            st.session_state["historique_chat"].append(("assistant", message_reponse, exercice_a_stocker))
            st.rerun()

# ── Onglet 3 : diagnostic (rotation des exemples Qdrant) ─────────────
with onglet_diagnostic:
    if "sujet_courant" not in st.session_state:
        st.info("Génère au moins un exercice pour voir le diagnostic.")
    else:
        historique = charger_historique_exemples()
        entrees = [
            h for h in historique
            if h.get("filtres", {}).get("sub_sub_sub_category") == st.session_state["sujet_courant"]
        ]

        if not entrees:
            st.caption("Aucune recherche enregistrée pour ce sujet pour l'instant.")
        else:
            compteur = Counter()
            for e in entrees:
                for id_ex in e.get("id_exercices", []):
                    compteur[id_ex] += 1

            st.caption(f"{len(entrees)} recherche(s) enregistrée(s) pour « {st.session_state['sujet_courant']} ».")

            st.markdown("**Fréquence d'apparition de chaque exercice source :**")
            for id_ex, n in compteur.most_common():
                st.markdown(f"- `{id_ex}` → {n} fois")

            st.markdown("**Dernières sélections (la plus récente en dernier) :**")
            for e in entrees[-5:]:
                st.code(f"{e['timestamp']} → {e['id_exercices']}", language=None)