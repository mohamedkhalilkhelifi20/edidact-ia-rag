from fastapi import FastAPI
from src.api.routes import router

app = FastAPI(title="EdiDact — API de recherche d'exercices")
app.include_router(router)