"""
Banc de test Streamlit pour le pipeline de génération EdiDact.

Lancer avec : streamlit run test_streamlit.py
"""

import time
import json
import re
import threading
import textwrap
from collections import Counter
import streamlit as st
from src.config.config import COLLECTION_HYBRID, LOG_EXEMPLES_MONTRES, TYPES_EXERCICE
from src.database.client import get_client
from src.generation.pipeline import generer_nouvel_exercice
from src.generation.correction_professeur import corriger_exercice
from src.generation.validation import compter_elements, extraire_liste_items

st.set_page_config(page_title="EdiDact — Banc de test", layout="centered", page_icon="📘")

CHAMPS_FILTRE = ["degree", "category", "sub_category", "sub_sub_category", "sub_sub_sub_category"]

CARACTERES_MARKDOWN_SPECIAUX = ["\\", "`", "*", "_", "{", "}", "[", "]", "(", ")", "#", "+", "-", "!", ">", "<"]


# ══════════════════════════════════════════════════════════════════════
# Habillage visuel — style suisse international (grille, rouge signal,
# Inter + JetBrains Mono). Aucune logique métier dans cette section.
# ══════════════════════════════════════════════════════════════════════

def injecter_style() -> None:
    """
    Les widgets natifs (selectbox, boutons, expanders, champs) sont
    désormais entièrement gérés par .streamlit/config.toml via les tables
    [theme.light] et [theme.dark] — c'est la méthode officiellement
    supportée par Streamlit pour theming, avec bascule native accessible
    depuis le menu Settings (⋮ en haut à droite). Aucun CSS custom n'est
    plus nécessaire pour ces composants : les tentatives précédentes de
    surcharger leurs couleurs à la main étaient fragiles précisément parce
    que ce n'est pas la méthode supportée.

    Le CSS ci-dessous ne touche QUE mes propres éléments HTML (en-tête,
    étapes numérotées), qui ne font pas partie des widgets natifs. Ils
    suivent @media (prefers-color-scheme: dark) pour rester cohérents avec
    le thème choisi, en pratique via la même préférence système que
    Streamlit utilise par défaut pour choisir entre theme.light/theme.dark.
    """
    st.markdown(
        textwrap.dedent(
            """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

            :root {
                --edidact-ink: #171717; --edidact-red: #E0001B; --edidact-muted: #6B6A66;
            }
            @media (prefers-color-scheme: dark) {
                :root { --edidact-ink: #F5F4F0; --edidact-red: #FF3B47; --edidact-muted: #A6A49C; }
            }

            .stApp, .stApp p, .stApp span, .stMarkdown {
                font-family: 'Inter', -apple-system, sans-serif;
            }
            [data-testid="stHeader"] { background-color: transparent; }
            .block-container { padding-top: 2.5rem; max-width: 780px; }

            /* ── En-tête ── */
            .edidact-hero {
                border-bottom: 3px solid var(--edidact-red);
                padding-bottom: 1.1rem; margin-bottom: 1.6rem;
            }
            .edidact-eyebrow {
                font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
                letter-spacing: 0.14em; text-transform: uppercase;
                color: var(--edidact-red); font-weight: 600; margin: 0 0 0.35rem 0;
            }
            .edidact-title {
                font-size: 2.05rem; font-weight: 800; letter-spacing: -0.02em;
                line-height: 1.1; margin: 0; color: var(--edidact-ink);
            }

            /* ── Étapes numérotées (sélection réellement séquentielle) ── */
            .step-label {
                display: flex; align-items: center; gap: 0.5rem;
                font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
                letter-spacing: 0.1em; text-transform: uppercase;
                color: var(--edidact-muted); margin: 1.1rem 0 0.4rem 0;
            }
            .step-number {
                display: inline-flex; align-items: center; justify-content: center;
                width: 1.35rem; height: 1.35rem; border: 1.5px solid var(--edidact-red);
                color: var(--edidact-red); font-weight: 700; font-size: 0.68rem; border-radius: 2px;
            }

            /* ── Onglets : typographie mono ── */
            [data-testid="stTabs"] button[role="tab"] p {
                font-family: 'JetBrains Mono', monospace; font-size: 0.78rem;
                letter-spacing: 0.06em; text-transform: uppercase;
            }

            /* ── Caption / code en mono ── */
            [data-testid="stCaptionContainer"] p { font-family: 'JetBrains Mono', monospace; }
            code, pre { font-family: 'JetBrains Mono', monospace !important; }

            /* ── Cartes de question (rendu de l'exercice) ── */
            .edidact-item-card {
                border: 1px solid var(--edidact-border, rgba(128,128,128,0.25));
                border-radius: 10px; padding: 1rem 1.15rem; margin-bottom: 0.85rem;
            }
            .edidact-item-head {
                display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.6rem;
            }
            .edidact-item-badge {
                display: inline-flex; align-items: center; justify-content: center;
                min-width: 1.6rem; height: 1.6rem; padding: 0 0.4rem;
                background: var(--edidact-red); color: white;
                font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 0.82rem;
                border-radius: 999px; flex-shrink: 0;
            }
            .edidact-item-texte {
                font-weight: 600; font-size: 1rem; color: var(--edidact-ink); line-height: 1.4;
            }
            .edidact-pill-row {
                display: flex; flex-wrap: wrap; gap: 0.5rem; margin-left: 2.2rem;
            }
            .edidact-pill {
                border: 1.5px solid var(--edidact-muted); border-radius: 999px;
                padding: 0.32rem 0.9rem; font-size: 0.88rem; color: var(--edidact-ink);
                opacity: 0.85;
            }
            .edidact-pill.correcte {
                border-color: #1DB954; background: rgba(29, 185, 84, 0.12);
                color: #1DB954; font-weight: 700; opacity: 1;
            }
            .edidact-answer-chip {
                display: inline-flex; align-items: center; gap: 0.4rem;
                margin-left: 2.2rem; padding: 0.32rem 0.9rem;
                border: 1.5px solid #1DB954; background: rgba(29, 185, 84, 0.12);
                color: #1DB954; font-weight: 700; font-size: 0.88rem; border-radius: 999px;
            }

            /* ── Blanc à compléter (remplace les suites d'underscores "____",
               qui pouvaient être mal rendues par l'échappement Markdown) ── */
            .edidact-blank {
                display: inline-block; min-width: 2.4rem; height: 1px;
                border-bottom: 2px solid var(--edidact-red);
                margin: 0 0.2rem -0.15rem 0.2rem;
            }

            /* ── Boîte "texte support" (paragraphe continu à trous) ──
               remplace st.info() qui n'accepte pas de HTML, donc pas les
               blancs ci-dessus. */
            .edidact-texte-support {
                background: rgba(96, 165, 250, 0.10); border: 1px solid rgba(96, 165, 250, 0.35);
                border-radius: 8px; padding: 0.9rem 1.05rem; line-height: 1.7;
                color: var(--edidact-ink); margin-bottom: 0.85rem;
            }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )


def afficher_hero() -> None:
    st.markdown(
        '<div class="edidact-hero">'
        '<p class="edidact-eyebrow">EdiDact · Programme scolaire suisse HarmoS</p>'
        '<p class="edidact-title">Banc de test — génération d\'exercice</p>'
        '</div>',
        unsafe_allow_html=True,
    )


def etiquette_etape(numero: str, texte: str) -> None:
    st.markdown(
        f'<div class="step-label"><span class="step-number">{numero}</span>{texte}</div>',
        unsafe_allow_html=True,
    )


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


def transformer_texte_avec_blancs(texte) -> str:
    """
    Comme echapper_markdown, mais remplace en plus toute suite de 2+
    underscores (le marqueur de trou utilisé dans tous nos formats de
    référence : "____", "___1___"...) par un vrai blanc visuel (span HTML)
    plutôt que des underscores échappés un par un.

    Bug corrigé : "\\_\\_\\_\\_" (échappement caractère par caractère d'une
    suite d'underscores) pouvait être mal rendu selon la version de Markdown
    utilisée — affichage corrompu ("L.L.L.L" observé en pratique). Un jeton
    neutre (sans caractère Markdown spécial) évite le problème et donne en
    plus un vrai rendu "ligne à compléter".

    Nécessite unsafe_allow_html=True côté appelant. Le HTML injecté ici est
    fixe (une seule balise <span> sans attribut variable) — pas de risque
    d'injection même si le texte source vient du modèle.
    """
    if not isinstance(texte, str):
        texte = str(texte)
    jeton = "\uE000BLANC\uE000"  # caractère de zone privée Unicode, jamais produit par le modèle
    texte = re.sub(r"_{2,}", jeton, texte)
    texte = echapper_markdown(texte)
    texte = texte.replace(jeton, '<span class="edidact-blank"></span>')
    return texte


def _texte_principal_item(item: dict) -> str:
    """Première vraie chaîne de texte d'un item, hors 'choix' et 'id' — jamais
    de nom de clé supposé ('phrase', 'question', 'support', 'operation'...)."""
    for cle, valeur in item.items():
        if cle in ("choix", "id"):
            continue
        if isinstance(valeur, str):
            return valeur
    return ""


def _reponse_correspond(choix_texte: str, reponse) -> bool:
    """Compare un choix affiché à la réponse correcte pour ce même item —
    gère le cas où la réponse est une simple valeur (str/nombre) ou une liste
    (ex: clavier2inputs, deux réponses par ligne)."""
    if isinstance(reponse, list):
        return any(str(r).strip().lower() == choix_texte.strip().lower() for r in reponse)
    return str(reponse).strip().lower() == choix_texte.strip().lower()


def rendre_item_avec_correction(item: dict, reponse, numero: int, afficher_correction: bool) -> None:
    """
    Affiche UNE question dans une carte : numéro, texte principal, puis soit
    des pastilles de choix (la bonne surlignée en vert si afficher_correction),
    soit — s'il n'y a pas de 'choix' (types clavier) — une puce verte "Réponse"
    directement sous la question quand afficher_correction est actif.

    C'est la correction volontaire du problème "liste de réponses séparée en
    bas de l'exercice, à recompter à la main avec les questions" : ici la
    bonne réponse apparaît directement là où la question est posée.
    """
    texte = _texte_principal_item(item)
    choix = item.get("choix")

    st.markdown(
        f'<div class="edidact-item-card">'
        f'<div class="edidact-item-head">'
        f'<span class="edidact-item-badge">{numero}</span>'
        f'<span class="edidact-item-texte">{transformer_texte_avec_blancs(texte)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if isinstance(choix, list):
        pastilles = ""
        for c in choix:
            c_str = str(c)
            est_correct = afficher_correction and _reponse_correspond(c_str, reponse)
            classe = "edidact-pill correcte" if est_correct else "edidact-pill"
            pastilles += f'<span class="{classe}">{echapper_markdown(c_str)}</span>'
        st.markdown(f'<div class="edidact-pill-row">{pastilles}</div>', unsafe_allow_html=True)
    elif afficher_correction and reponse is not None:
        reponse_texte = ", ".join(str(r) for r in reponse) if isinstance(reponse, list) else str(reponse)
        st.markdown(
            f'<div class="edidact-answer-chip">✓ {echapper_markdown(reponse_texte)}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)


def rendre_valeur(valeur) -> None:
    """
    Rendu générique de secours pour les structures qui ne sont PAS une liste
    d'items appariable à une correction terme à terme (ex: le paragraphe
    continu de drag_and_drop_paragraphe, ou une banque d'étiquettes partagée
    affichée seule). Ne suppose jamais de nom de clé fixe.
    """
    if valeur is None:
        return
    if isinstance(valeur, (str, int, float)):
        st.markdown(echapper_markdown(valeur))
        return
    if isinstance(valeur, list):
        for i, item in enumerate(valeur, 1):
            if isinstance(item, dict):
                rendre_item_avec_correction(item, None, i, False)
            else:
                st.markdown(f"**{i}.** {echapper_markdown(item)}")
        return
    if isinstance(valeur, dict):
        for cle, val in valeur.items():
            if cle == "texte" and isinstance(val, str):
                # st.info() n'accepte pas de HTML — remplacé par une boîte
                # custom pour pouvoir y afficher les blancs "___" correctement
                # (drag_and_drop_paragraphe : paragraphe continu à trous).
                st.markdown(
                    f'<div class="edidact-texte-support">{transformer_texte_avec_blancs(val)}</div>',
                    unsafe_allow_html=True,
                )
            elif isinstance(val, (list, dict)):
                rendre_valeur(val)
            else:
                st.markdown(echapper_markdown(val))
        return


def rendre_contenu(contenu, correction, afficher_correction: bool) -> None:
    """
    Point d'entrée du rendu du contenu. Tente d'abord d'apparier "contenu" et
    "correction" comme deux listes de même longueur (cas de loin le plus
    fréquent parmi les 13 types validés : items/phrases/calculs + correction
    alignée par position) pour un rendu carte-par-carte avec réponse inline.

    Si l'appariement n'est pas possible (longueurs différentes, ou contenu
    avec plusieurs listes de tailles différentes comme une banque d'étiquettes
    partagée + son texte continu), on ne devine rien : on retombe sur le
    rendu générique rendre_valeur(), qui affiche 'contenu' puis, si le toggle
    est actif, 'correction' séparément — comportement sûr plutôt qu'un
    appariement risqué et potentiellement faux.
    """
    items = extraire_liste_items(contenu)
    reponses = extraire_liste_items(correction)

    items_appariables = (
        items and reponses and len(items) == len(reponses)
        and all(isinstance(i, dict) for i in items)
    )

    if items_appariables:
        for i, (item, reponse) in enumerate(zip(items, reponses), 1):
            rendre_item_avec_correction(item, reponse, i, afficher_correction)
        return

    # Repli générique — structure non appariable terme à terme
    rendre_valeur(contenu)
    if afficher_correction:
        st.markdown("**Correction :**")
        rendre_valeur(correction)


def afficher_exercice(exercice: dict, cle: str = "principal") -> None:
    """
    Rendu complet d'un exercice — réutilisé partout (résultat principal,
    bulles de chat) pour qu'un seul endroit gère la présentation.

    `cle` : identifiant unique pour cet appel — nécessaire car cette fonction
    peut être appelée plusieurs fois dans le même rerun (ex: une fois par
    message dans l'historique du chat de correction) ; sans clé unique, les
    toggles en dessous entreraient en collision entre plusieurs exercices
    affichés simultanément.

    Le toggle "Afficher la correction" est lu AVANT le rendu du contenu (pas
    après, comme dans la version précédente) : la correction s'affiche
    désormais directement dans chaque carte de question, pas dans une liste
    séparée à la fin qu'il fallait recompter manuellement avec les questions.
    """
    with st.container(border=True):
        st.markdown(f"### {echapper_markdown(exercice.get('consigne', ''))}")

        col_correction, col_json = st.columns(2)
        with col_correction:
            afficher_correction = st.toggle("Afficher la correction", key=f"correction_{cle}")
        with col_json:
            afficher_json = st.toggle("JSON brut (avancé)", key=f"json_{cle}")

        st.markdown("")  # petit espace avant les cartes
        rendre_contenu(exercice.get("contenu"), exercice.get("correction"), afficher_correction)

        if afficher_json:
            st.divider()
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
    client = get_client()
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
        print(f"[test_streamlit] {points_ignores} point(s) Qdrant ignoré(s) — payload malformé.")
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

injecter_style()
afficher_hero()

onglet_config, onglet_exercice, onglet_diagnostic = st.tabs(
    ["Configurer", "Exercice", "Diagnostic"]
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

    etiquette_etape("01", "Sujet — niveau, matière, thème")
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

    etiquette_etape("02", "Type d'exercice — structure imposée au modèle")
    type_exercice = st.selectbox(
        "Type d'exercice",
        sorted(TYPES_EXERCICE.keys()),
        label_visibility="collapsed",
        help="Structure d'interaction imposée au modèle — il ne réfléchit plus à quel format choisir.",
    )
    st.caption(TYPES_EXERCICE.get(type_exercice, {}).get("description", ""))

    etiquette_etape("03", "Demande libre — optionnel")
    # Pas de st.form ici : un formulaire ne sert qu'à grouper plusieurs champs
    # et différer leur lecture jusqu'au clic — pas nécessaire dans ce cas, et
    # c'est justement la combinaison form + expander qui causait le bug de
    # chevauchement de texte (bug Streamlit documenté). En widgets normaux,
    # l'expander fonctionne correctement.
    texte = st.text_area(
        "Texte (demande libre du professeur)",
        placeholder="Optionnel — instructions précises (nombre de questions, thème...)",
        help=(
            "Optionnel. Laisse vide pour un exercice standard sur le sujet choisi. "
            "Utile pour : préciser un thème, imposer un nombre exact de questions, "
            "ou détailler une répartition par compétence."
        ),
    )
    # PAS de st.expander : bug Streamlit confirmé dans cette version (1.59.1),
    # présent même hors de tout st.form — chevauchement de texte systématique
    # sur l'icône du chevron. Remplacé par une checkbox de repli/dépli, qui
    # ne dépend pas du composant cassé, même fonction pour l'utilisateur.
    afficher_options = st.checkbox("Options avancées")
    if afficher_options:
        limite = st.number_input("Limite (exemples Qdrant)", min_value=1, max_value=10, value=3)
    else:
        limite = 3

    valider = st.button("Générer un exercice", use_container_width=True)

    if valider:
        resultat_thread = {}

        def executer_generation():
            try:
                resultat_thread["exercice"] = generer_nouvel_exercice(
                    category=category, sub_category=sub_category,
                    sub_sub_category=sub_sub_category,
                    sub_sub_sub_category=sub_sub_sub_category,
                    degree=degree, type_exercice=type_exercice,
                    texte=texte, limite=int(limite),
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
            st.success("✓ Exercice généré — va voir l'onglet **Exercice**.")

# ── Onglet 2 : exercice actuel + chat de correction ──────────────────
with onglet_exercice:
    if "exercice_actuel" not in st.session_state:
        st.info("Génère un exercice depuis l'onglet **Configurer**.")
    else:
        st.caption(f"Généré en {st.session_state.get('derniere_duree', 0):.1f}s")
        afficher_exercice(st.session_state["exercice_actuel"])

        st.divider()
        st.markdown("**Demander une correction**")

        for i, (role, message, exercice_lie) in enumerate(st.session_state.get("historique_chat", [])):
            with st.chat_message(role):
                st.markdown(message)
                if exercice_lie is not None:
                    afficher_exercice(exercice_lie, cle=f"chat_{i}")

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
                    afficher_exercice(nouvel_exercice, cle="nouvelle_correction")
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