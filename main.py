from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router

app = FastAPI(title="EdiDact — API de recherche d'exercices")

# CORS : nécessaire pour appeler cette API depuis une page ouverte dans un
# navigateur (page de test, futur frontend) sur une autre origine que
# localhost:8000. En développement local uniquement — à restreindre à un
# domaine précis avant toute mise en production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)