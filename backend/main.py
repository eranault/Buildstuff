from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import analyze

app = FastAPI(title="CodeGraph API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
