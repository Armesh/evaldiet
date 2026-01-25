from contextlib import asynccontextmanager
import traceback
import os
import sqlite3
from typing import Union, Annotated
import httpx
from dotenv import load_dotenv
import signal

from fastapi import FastAPI, HTTPException, Header, Request, Depends, Response
from fastapi.params import Body
from fastapi.responses import JSONResponse, RedirectResponse

from fastapi.staticfiles import StaticFiles
from app.models import DietCreate, DietUpdate

load_dotenv()  # loads .env from current working directory

@asynccontextmanager
async def lifespan(app: FastAPI):
    # One client + one connection pool for the whole app lifetime
    app.state.httpx_client = httpx.AsyncClient(
        timeout=10.0,
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
    )
    yield

    await app.state.httpx_client.aclose()
    os.kill(os.getpid(), signal.SIGINT)

app = FastAPI(lifespan=lifespan)



# serve /static/...
app.mount("/static", StaticFiles(directory="app/static"), name="static")

def get_db_path() -> str:
    return os.getenv("EVALDIET_DB_PATH", "app/evaldiet.db")

@app.get("/")
def root():
    return JSONResponse(content=dict(os.environ),media_type="application/json")

@app.get("/all_routes")
def all_routes(request: Request):
    routes = []
    for route in request.app.routes:
        routes.append({
            "path": route.path,
            # "methods": list(route.methods),
            "name": route.name,
        })
    return routes

@app.get("/foods")
def get_foods():
    conn = None
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM foods")
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()

@app.get("/diets")
def get_diets():
    conn = None
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM diets")
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()

@app.post("/diet")
def create_diet(payload: DietCreate):
    conn = None
    try:
        conn = sqlite3.connect(get_db_path())
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO diets (Name, FDC_ID, Quantity, sort_order)
            VALUES (?, ?, ?, ?)
            """,
            (payload.Name, payload.FDC_ID, payload.Quantity, payload.sort_order),
        )
        conn.commit()
        return {"created": cur.rowcount}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()

@app.put("/diet/{name}")
def update_diet(name: str, payload: DietUpdate):
    conn = None
    try:
        conn = sqlite3.connect(get_db_path())
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE diets
            SET Name = ?, FDC_ID = ?, Quantity = ?, sort_order = ?
            WHERE Name = ?
            """,
            (payload.Name, payload.FDC_ID, payload.Quantity, payload.sort_order, name),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Diet not found")
        return {"updated": cur.rowcount}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()
