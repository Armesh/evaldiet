import os
import sqlite3

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi.responses import FileResponse


def get_db_path() -> str:
    return os.getenv("EVALDIET_DB_PATH", "evaldiet.sqlite3")


def get_db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.execute("PRAGMA foreign_keys = ON")
    # Enforce FK support for every connection.
    fk_enabled = conn.execute("PRAGMA foreign_keys").fetchone()
    if not fk_enabled or fk_enabled[0] != 1:
        raise RuntimeError("SQLite foreign_keys must be enabled.")
    return conn

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

    @router.post("/api/admin/db_download")
    def db_download(payload: DbOpsPassPayload):
        verify_db_ops_pass(payload.db_ops_pass)
        db_path = get_db_path()
        if not os.path.exists(db_path):
            raise HTTPException(status_code=404, detail="Database not found")
        return FileResponse(db_path, media_type="application/octet-stream", filename="evaldiet.sqlite3")

    @router.post("/api/admin/create_db")
    def create_db(payload: DbOpsPassPayload):
        verify_db_ops_pass(payload.db_ops_pass)
        db_path = get_db_path()
        if os.path.exists(db_path):
            if not os.path.isfile(db_path):
                raise HTTPException(status_code=400, detail="Database path is not a file. Create aborted.")

            try:
                if os.path.getsize(db_path) < 40 * 1024:
                    os.remove(db_path)  # Existing faulty DB is removed
                else:
                    raise HTTPException(status_code=400, detail=f"Database {db_path} already exists. Create aborted.")
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc))

        conn = get_db_conn()
        try:
            init_schema_path = os.path.join("app", "init_create_db.sql")
            if not os.path.exists(init_schema_path):
                raise HTTPException(status_code=500, detail="Schema file missing: app/init_create_db.sql")

            with open(init_schema_path, "r", encoding="utf-8") as handle:
                sql_blob = handle.read()

            statements = [stmt.strip() for stmt in sql_blob.split(";") if stmt.strip()]
            for stmt in statements:
                conn.execute(stmt)

            conn.commit()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        finally:
            conn.close()

        return {f"Database {db_path} Created"}

    return router
