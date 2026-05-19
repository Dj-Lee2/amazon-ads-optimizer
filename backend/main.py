import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from db import engine, SessionLocal
from models import Base, Asin
from api import router
from api.optimizer_routes import router as optimizer_router


def _seed_if_empty():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        if session.query(Asin).first() is None:
            print("DB가 비어 있습니다. Mock 데이터를 생성합니다 (약 1-2분)...")
            from data_providers.mock_generator import generate_all
            generate_all(session, days=90)
            print("Mock 데이터 생성 완료.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_if_empty()
    yield


app = FastAPI(title="Amazon Ads Optimizer", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(optimizer_router)


@app.get("/health")
def health():
    return {"status": "ok"}


# React 빌드 정적 파일 서빙 (API 라우터 등록 이후에 마운트)
_build_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "build")
_build_dir = os.path.abspath(_build_dir)

if os.path.isdir(_build_dir):
    app.mount("/static", StaticFiles(directory=os.path.join(_build_dir, "static")), name="static")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """API 경로가 아닌 모든 요청은 React index.html 반환 (SPA 라우팅)."""
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        return FileResponse(os.path.join(_build_dir, "index.html"))
