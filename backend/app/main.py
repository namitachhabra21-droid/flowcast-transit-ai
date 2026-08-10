from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.predict import router as predict_router
from app.api.recommend import router as recommend_router
from app.api.v1.router import router as api_v1_router
from app.config import get_settings

settings = get_settings()

allowed_origins = [settings.frontend_origin] + [
    origin.strip() for origin in settings.extra_cors_origins.split(",") if origin.strip()
]

app = FastAPI(title="TransitPulse API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)
app.include_router(predict_router)
app.include_router(recommend_router)


@app.get("/health")
def health():
    return {"status": "ok"}
