import json
from datetime import datetime
from pathlib import Path
from src.vecteur.search_dense import rechercher_dense
from src.vecteur.search_sparse import rechercher_sparse
from src.vecteur.search_hybrid import rechercher_hybrid

def sauvegarder_resultats(resultats: list):
    dossier = Path("benchmarks")
    dossier.mkdir(exist_ok=True)
    fichier = dossier / f"benchmark_recherche_{datetime.now().strftime('%Y%m%d')}.json"
    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)
    print(f"\nRésultats sauvegardés : {fichier}")

def _fmt(resultats):
    return [{"score": r.score, "consigne": r.payload.get("consigne")} for r in resultats]

if __name__ == "__main__":
    exemples = [
        {
            "texte": "Complète les expressions avec le mot correct.",
            "category": "Français", "sub_category": "Vocabulaire",
            "sub_sub_category": "Champ lexical", "sub_sub_sub_category": "Sens propre et sens figuré",
            "degree": "9/10"
        },
        {
            "texte": "Écris l'article correct de ces noms.",
            "category": "Allemand", "sub_category": "Grammaire",
            "sub_sub_category": "Les noms", "sub_sub_sub_category": "Le genre des noms",
            "degree": "5/6"
        },
    ]

    rapport = []
    for ex in exemples:
        print(f"\n=== {ex['texte']} ({ex['category']}) ===")
        args = (ex["texte"], ex["category"], ex["sub_category"], ex["sub_sub_category"], ex["sub_sub_sub_category"], ex["degree"])

        entree = {"requete": ex["texte"], "category": ex["category"]}

        print("-- DENSE (filtre complet) --")
        r_dense = rechercher_dense(*args)
        for r in r_dense:
            print(f"  score={r.score:.4f} | {r.payload.get('consigne')}")
        entree["dense"] = _fmt(r_dense)

        print("-- SPARSE (filtre complet) --")
        r_sparse = rechercher_sparse(*args)
        for r in r_sparse:
            print(f"  score={r.score:.4f} | {r.payload.get('consigne')}")
        entree["sparse"] = _fmt(r_sparse)

        print("-- HYBRID (filtre complet) --")
        r_hybrid = rechercher_hybrid(*args)
        for r in r_hybrid:
            print(f"  score={r.score:.4f} | {r.payload.get('consigne')}")
        entree["hybrid"] = _fmt(r_hybrid)

        rapport.append(entree)

    sauvegarder_resultats(rapport)