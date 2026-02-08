import os
import logging
from fastapi import APIRouter, HTTPException
from sqlalchemy import inspect
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
    
    @router.post("/api/admin/create_db_tables")
    def create_db(payload: DbOpsPassPayload):
        verify_db_ops_pass(payload.db_ops_pass)
        try:
            logger = logging.getLogger(__name__)
            inspector = inspect(engine)
            existing_tables = set(inspector.get_table_names())
            model_tables = set(Base.metadata.tables.keys())
            if model_tables and model_tables.issubset(existing_tables):
                raise HTTPException(status_code=400, detail="Nothing was done. All Tables already present")
            logger.info("create_db: starting Base.metadata.create_all")
            Base.metadata.create_all(bind=engine)
            logger.info("create_db: finished Base.metadata.create_all")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

        return {"status": "ok", "message": "Database Tables created with SQLAlchemy models"}

    return router
