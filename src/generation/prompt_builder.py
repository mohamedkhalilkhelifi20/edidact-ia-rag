# src/generation/prompt_builder.py
import json
from src.config.config import TYPES_EXERCICE

def construire_prompt(demande_professeur: dict, exemples: list[dict]) -> str:
    category = demande_professeur["category"]
    sub_category = demande_professeur["sub_category"]
    sub_sub_category = demande_professeur["sub_sub_category"]
    sub_sub_sub_category = demande_professeur["sub_sub_sub_category"]
    degree = demande_professeur["degree"]
    theme = demande_professeur.get("texte", "").strip() or "le même thème que les exemples"
    type_exercice = demande_professeur["type_exercice"]

    type_info = TYPES_EXERCICE.get(type_exercice)
    if type_info is None:
        # Type totalement inconnu de TYPES_EXERCICE — comportement identique
        # à avant : aucune référence, le modèle utilise son jugement.
        description_type = "Type non répertorié — utilise ton jugement pour la structure la plus adaptée."
        format_reference = None
    else:
        description_type = type_info.get("description", "")
        format_reference = type_info.get("format_reference")

    # Bloc structure : injecté SEULEMENT si ce type a été validé manuellement
    # (format_reference non None). Tant qu'un type n'a pas encore été validé
    # un par un avec Mohamed (voir config.py), on ne fabrique rien à sa place —
    # le modèle retombe sur la description seule, comme avant ce changement.
    bloc_structure = ""
    if format_reference is not None:
        bloc_structure = f"""
STRUCTURE JSON DE RÉFÉRENCE POUR CE TYPE (respecte EXACTEMENT cette forme de
"contenu" et de "correction" — mêmes noms de clés, même organisation ; seul
le contenu pédagogique change, jamais la structure) :
{json.dumps(format_reference, ensure_ascii=False, indent=2)}
"""

    exemples_texte = ""
    for i, ex in enumerate(exemples, 1):
        exemple_json = {
            "consigne": ex.get("consigne"),
            "contenu": ex.get("contenu"),
            "correction": ex.get("correction"),
        }
        exemples_texte += f"\n--- Exemple {i} ---\n{json.dumps(exemple_json, ensure_ascii=False, indent=2)}\n"

    prompt = f"""Tu es un expert en création d'exercices pédagogiques pour la plateforme EdiDact,
qui suit le programme scolaire suisse HarmoS.

CONTEXTE :
- Matière : {category}
- Sous-catégorie : {sub_category}
- Sous-sous-catégorie : {sub_sub_category}
- Sujet précis : {sub_sub_sub_category}
- Niveau scolaire : {degree}
- Thème demandé par le professeur : {theme}

EXEMPLES D'EXERCICES RÉELS DE CETTE MATIÈRE ET CE NIVEAU (référence de style, de langue et de niveau de difficulté — pas de structure obligatoire) :
{exemples_texte}

TA TÂCHE :
Le type d'exercice est IMPOSÉ par le professeur : "{type_exercice}".
{description_type}
{bloc_structure}
Ne réfléchis PAS à un autre type de structure (QCM, vrai/faux, association, etc.) —
celle-ci est déjà décidée. Ta seule tâche est de créer UN NOUVEL exercice original
sur le sujet demandé, dont le contenu et la correction respectent cette structure
d'interaction précise.

RÈGLES STRICTES :
1. Le JSON doit contenir exactement trois clés : "consigne", "contenu", "correction".
2. "consigne" est une phrase claire d'instruction (minimum 10 caractères).
3. "contenu" doit être structuré selon le type d'exercice que tu as choisi (objet ou liste,
   selon ce qui représente le mieux ce type — par exemple une liste de lignes pour un tableau,
   un objet avec "question"/"choix" pour un QCM).
4. "correction" doit être structurée de façon cohérente avec "contenu" : mêmes clés ou même
   nombre d'éléments correspondants, pour que chaque réponse soit reliée sans ambiguïté à son élément.
5. L'exercice doit être écrit dans la même langue que les exemples fournis.
6. La difficulté doit correspondre au niveau {degree} — ni plus simple, ni plus complexe que les exemples.
7. L'exercice doit rester précisément dans le sujet "{sub_sub_sub_category}".
8. N'invente pas de nouvelles clés en dehors de "consigne", "contenu", "correction".
9. COHÉRENCE ENTRE CONSIGNE ET CONTENU : si la consigne annonce "phrases", chaque élément de
   "contenu" doit être une vraie phrase grammaticalement complète (sujet + verbe) — jamais un
   mot isolé. Si la consigne parle de "mots" ou "vocabulaire", une liste de mots simples est
   acceptable. Ne jamais annoncer un type de contenu et en produire un autre.
10. CONSIGNE GÉNÉRIQUE : la "consigne" ne doit jamais répéter des valeurs précises (une liste de
    choix, un mot, un nombre) qui sont déjà présentes dans "contenu". Si des choix varient d'une
    question à l'autre, dis simplement "Choisis la bonne réponse parmi les options proposées" —
    jamais énumérer les choix dans la consigne elle-même.
11. RELECTURE FINALE : avant de répondre, relis ta "consigne" et vérifie qu'elle décrit fidèlement
    et uniquement de façon générale ce que contient "contenu" — corrige-la si besoin.
12. DIVERSITÉ DES RÉPONSES : si l'exercice demande de choisir entre plusieurs catégories, types,
    ou options (par exemple "vrai/faux", "sens propre/sens figuré", "masculin/féminin"), les bonnes
    réponses dans "correction" doivent être VARIÉES — ne jamais mettre la même réponse pour tous
    les éléments. Un exercice de discrimination doit permettre de vraiment tester si l'élève sait
    distinguer les cas, donc il doit contenir un mélange réel des différentes possibilités.
13. NE JAMAIS RÉVÉLER LA RÉPONSE DANS L'ÉNONCÉ : le "contenu" ne doit jamais contenir,
    même partiellement, la bonne réponse écrite en toutes lettres. Par exemple, si la
    réponse est "VRAI", la phrase du contenu ne doit jamais inclure le mot "VRAI" —
    c'est à l'élève de le déterminer, pas une information déjà donnée.
14. RESPECT STRICT DES INSTRUCTIONS DU PROFESSEUR : si le "thème demandé" contient des
    instructions précises et détaillées (nombre de questions, types de questions,
    répartition par compétence, longueur du texte, etc.), tu DOIS les suivre exactement,
    point par point. Ne génère jamais un exercice générique si des contraintes précises
    ont été données — vérifie une par une que chaque contrainte demandée est remplie
    avant de finaliser ta réponse.
15. Si le "thème demandé par le professeur" contient des instructions précises et
    chiffrées (nombre de questions, répartition par compétence, longueur du texte, etc.),
    respecte-les EXACTEMENT, une par une. Relis ta réponse avant de la donner et
    vérifie que chaque instruction précise a bien été suivie.
16. CONSIGNE SIMPLE ET DIRECTE (pour tout type d'exercice) : la consigne doit exprimer
    UNE SEULE action claire, en une phrase courte, sans détails redondants avec ce que
    l'élève voit déjà dans la structure de l'exercice, quel que soit son type.

    Ne décris jamais dans la consigne ce qui est déjà visuellement évident dans le contenu :
    - QCM : ne précise pas "parmi les options proposées" (les choix sont déjà visibles)
    - Texte à trous : ne précise pas "dans l'espace prévu" (les espaces sont déjà visibles)
    - Association : ne précise pas "en traçant un trait" ou "entre les deux colonnes"
      (la structure à deux colonnes est déjà visible)
    - Tableau : ne précise pas "dans les cases du tableau" (le tableau est déjà visible)
    - Vrai/Faux : ne précise pas "en cochant vrai ou faux" (déjà visible dans la structure)
    - Question ouverte : ne précise pas "en rédigeant une réponse complète" (déjà implicite)
    - Calcul : ne précise pas "en effectuant le calcul demandé" (déjà implicite dans les nombres)

    Exemples de bonnes consignes, courtes et directes, pour différents types :
    - "Entoure la bonne réponse."
    - "Écris la réponse correcte pour chaque phrase."
    - "Relie chaque mot à sa définition."
    - "Complète les phrases avec le mot correct."
    - "Calcule le résultat de chaque opération."
    - "Classe les mots selon leur catégorie."
    - "Réponds aux questions suivantes."

    Règle générale : avant de finaliser la consigne, retire tout mot ou groupe de mots
    qui décrit la structure visuelle de l'exercice plutôt que l'action à accomplir.
    Garde uniquement le verbe d'action principal et son complément essentiel.

17. CHOIX ADAPTÉS À CHAQUE QUESTION : dans un QCM, les options de réponse ("choix") doivent
    être pensées spécifiquement pour chaque question, pas recopiées identiques d'une question
    à l'autre par facilité. Chaque ensemble de choix doit être plausible et pertinent pour
    la question précise posée.

18. COHÉRENCE TEXTE-CONSIGNE-QUESTIONS : chaque question doit découler directement et
    logiquement du texte de support généré. Ne pose jamais une question dont la réponse
    ne peut pas être déduite ou vérifiée à partir du texte fourni. Relis le texte avant
    de rédiger chaque question pour t'assurer que la réponse s'y trouve réellement.
19. INTERDICTION DES TABLEAUX CROISÉS À DOUBLE ENTRÉE : n'utilise jamais une structure
    de tableau où chaque cellule dépend à la fois d'une ligne ET d'une colonne (type
    "table d'addition croisée" ou "table de multiplication"). Ce type de structure est
    trop complexe à générer de façon fiable. Si l'exercice porte sur des calculs
    tabulaires, utilise à la place une LISTE de lignes indépendantes, où chaque ligne
    contient déjà tous les nombres nécessaires à son propre calcul.

    Exemple INTERDIT (tableau croisé) : une grille où la cellule [ligne 2, colonne 3]
    dépend à la fois de la valeur de la ligne 2 ET de la colonne 3.

    Exemple CORRECT (liste de lignes indépendantes, chaque ligne autonome) :
    une liste où chaque élément contient déjà les deux nombres et le résultat attendu,
    par exemple : premier nombre 12, deuxième nombre 3, résultat à trouver.
    Chaque ligne se calcule seule, sans dépendre d'une autre ligne ou colonne.
20. RICHESSE NATURELLE DU TEXTE SUPPORT : si l'exercice prévoit des questions sur la
    forme de phrase (déclarative/interrogative/exclamative), INTÈGRE NATURELLEMENT dans
    le texte au moins une phrase avec un dialogue exclamatif (ex: « Quelle surprise ! »)
    ou une question directe (ex: « Que va-t-il se passer ? »), en plus des phrases
    déclaratives habituelles — c'est un procédé d'écriture courant dans un texte narratif,
    pas une contrainte artificielle.

    IMPORTANT : ne désigne JAMAIS une phrase comme "exclamative" ou "interrogative" si
    elle n'a pas réellement les marqueurs correspondants (point d'exclamation ou
    d'interrogation). Si tu ne peux pas inclure naturellement une vraie diversité de
    formes de phrases dans ce texte précis, pose UNE SEULE question sur les formes de
    phrases, et remplace la deuxième question de cette compétence par une question
    supplémentaire sur une autre compétence déjà demandée (grammaire, conjugaison,
    vocabulaire), plutôt que d'inventer une fausse catégorisation.
21. ADAPTATION STRICTE AU NIVEAU SCOLAIRE HARMOS : le vocabulaire, la longueur des
    phrases, la complexité des nombres, et la difficulté globale DOIVENT correspondre
    précisément à l'âge réel des élèves de ce niveau :
    - Niveaux 1/2 (élèves d'environ 4-6 ans, école enfantine, cycle 1) : PAS de texte
        à lire de façon autonome — privilégier des consignes très courtes, orales dans
        l'esprit (répétées simplement), avec des nombres de 1 à 10 maximum, reconnaissance
        de formes/couleurs/quantités simples, pas de vraie lecture de phrase complexe
        attendue. Vocabulaire extrêmement simple, une seule idée par consigne.
        Éviter tout exercice nécessitant une lecture fluide ou un raisonnement abstrait.
    - Niveaux 3/4 (élèves d'environ 6-8 ans, cycle 1) : phrases très courtes et
      simples, nombres petits (généralement sous 100), vocabulaire concret et familier,
      pas de notions abstraites.
    - Niveaux 5/6 (élèves d'environ 8-10 ans, cycle 2) : phrases simples, nombres
      jusqu'à 1000, premières notions un peu plus abstraites mais expliquées
      simplement, début des langues étrangères (allemand dès 5H).
    - Niveaux 7/8 (élèves d'environ 10-12 ans, cycle 2) : phrases plus élaborées,
      calculs avec fractions/décimaux simples, vocabulaire plus riche, anglais
      introduit dès 7H.
    - Niveaux 9/10 (élèves d'environ 12-14 ans, cycle 3 secondaire I) : phrases
      complexes, notions abstraites (algèbre, grammaire fine), vocabulaire soutenu
      acceptable, raisonnement plus poussé attendu.

    Un exercice de niveau 9/10 ne doit JAMAIS être aussi simple qu'un exercice de
    niveau 3/4 (ex: "1+1" est réservé aux tout premiers niveaux, pas au secondaire I).
    Un exercice de niveau 3/4 ne doit JAMAIS contenir de notions du secondaire I
    (ex: algèbre, subjonctif, calcul avec puissances).
22. RIGUEUR FACTUELLE UNIVERSELLE : pour toute question qui demande d'identifier,
    classer, ou nommer un élément précis (grammatical, linguistique, mathématique,
    peu importe la matière), NE RÉPONDS QUE si tu peux justifier concrètement ta
    réponse à partir d'un élément vérifiable du texte ou du calcul. Si tu ne peux
    pas justifier concrètement pourquoi ta réponse est vraie (avec une preuve
    précise : un marqueur textuel, un résultat de calcul, une règle grammaticale
    applicable), ne pose pas cette question — remplace-la par une question sur
    un autre aspect que tu peux vérifier avec certitude.
23. RICHESSE PÉDAGOGIQUE MINIMALE : même sans thème précis fourni par le professeur,
    ne remplis JAMAIS la structure imposée avec le contenu le plus simple/basique par
    défaut (comme un simple "complète avec le mot A ou B" quand la structure permet
    mieux). Privilégie toujours un contenu qui demande une vraie réflexion ou un vrai
    calcul de la part de l'élève — par exemple, pour un sujet comme "nombres premiers",
    préfère demander d'identifier des nombres premiers PARMI plusieurs candidats
    (un tri, une sélection dans une liste), plutôt que de simplement demander si un
    nombre déjà donné est premier ou non. Pose-toi la question : "est-ce que ce contenu
    demande un vrai raisonnement, ou juste de recopier un mot dans un espace vide ?"
    Si c'est la deuxième option, exige davantage de l'élève dans le contenu, tout en
    respectant la structure imposée.
24. FORMAT PAPIER RÉALISTE : pense TOUJOURS à la façon dont un élève va physiquement
    répondre sur une feuille imprimée, pas seulement à la logique du contenu JSON.
    - "Entoure" : nécessite que les éléments à choisir soient présentés en ligne ou
      en groupe visible, assez espacés pour être entourés au crayon.
    - "Classe" : nécessite deux colonnes ou catégories clairement nommées, avec un
      espace/tableau où recopier ou cocher chaque élément dans la bonne colonne —
      pas juste deux listes de correction sans structure d'écriture pour l'élève.
    - "Complète" : nécessite un espace vide clairement visible (des pointillés ou
      un blanc) directement dans la phrase ou le mot.
    - "Coche" : nécessite une case ou un symbole ☐ à côté de chaque option.
    - "Relie" : nécessite deux colonnes distinctes et alignées, avec assez d'espace
      entre elles pour tracer un trait.

    Le contenu JSON généré doit inclure des indices structurels qui permettent de
    reconstruire cette mise en page papier plus tard (par exemple, prévoir un champ
    ou une structure qui indique clairement "ceci est une colonne A à remplir" plutôt
    que juste deux listes de résultats déjà séparés).
25. PAS DE FORMULE RÉPÉTÉE D'UN ITEM À L'AUTRE : quand l'exercice contient plusieurs
    questions/items dans une liste, ne réintroduis jamais la même phrase-cadre au
    début de chacun (par exemple "Quel est l'infinitif du verbe dans « ... » ?" répété
    identique à chaque question). Si la "consigne" annonce déjà la tâche à accomplir,
    chaque item ne doit contenir QUE l'élément propre à traiter (la phrase source,
    le mot, le calcul...), jamais la question méta déjà sous-entendue par la consigne.
    Exemple INCORRECT : consigne "Choisis le bon infinitif." puis items "Quel est
    l'infinitif du verbe dans « Tu lis une histoire. » ?", "Quel est l'infinitif du
    verbe dans « Nous mangeons... » ?" (répétition inutile de la même formule).
    Exemple CORRECT : consigne "Choisis le bon infinitif du verbe conjugué dans
    chaque phrase." puis items "Tu lis une histoire.", "Nous mangeons à la maison."
    (la tâche est déjà claire, chaque item ne montre que la phrase à traiter).

FORMAT DE SORTIE :
Réponds UNIQUEMENT avec le JSON, sans texte avant, sans texte après, sans balises markdown (pas de ```).
"""
    return prompt