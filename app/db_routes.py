import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.db.models import Base
from app.db.session import engine
import app.db.models  # REQUIRED so models are registered

def verify_db_ops_pass(provided_pass: str | None):
    expected = os.getenv("DB_OPS_PASS")
    if not expected:
        raise HTTPException(status_code=403, detail="DB_OPS_PASS not configured")
    if not provided_pass or provided_pass != expected:
        raise HTTPException(status_code=403, detail="Invalid DB_OPS_PASS")


def get_db_router():
    router = APIRouter()

    class DbOpsPassPayload(BaseModel):
        db_ops_pass: str | None = None

    @router.get("/api/admin/db_health")
    def db_health():
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "ok"}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
    
    @router.post("/api/admin/create_db")
    def create_db(payload: DbOpsPassPayload):
        verify_db_ops_pass(payload.db_ops_pass)
        try:
            Base.metadata.create_all(bind=engine)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

        return {"status": "ok", "message": "Database created with SQLAlchemy models"}

    return router
