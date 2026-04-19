from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())
load_dotenv(find_dotenv(".env.local"), override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .user_route import router as user_router
from .analysis_route import router as analysis_router

app = FastAPI(title="JobAssistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router, prefix="/api/users", tags=["users"])
app.include_router(analysis_router, prefix="/api", tags=["analysis"])


@app.get("/health")
def health():
    return {"status": "ok"}
