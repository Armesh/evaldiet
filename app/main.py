from contextlib import asynccontextmanager
import traceback
import os
import sqlite3
from typing import Union, Annotated
import httpx
from dotenv import load_dotenv
import signal

from fastapi import FastAPI, HTTPException, Header, Request, Depends, Response, requests
from fastapi.params import Body
from fastapi.responses import JSONResponse, RedirectResponse

from fastapi.staticfiles import StaticFiles
from app.models import DietCreate, DietUpdate
import re

load_dotenv()  # loads .env from current working directory

@asynccontextmanager
async def lifespan(app: FastAPI):
    # One client + one connection pool for the whole app lifetime
    app.state.httpx_client = httpx.Client(
        timeout=10.0,
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
    )
    try:
        yield
    finally:
        app.state.httpx_client.close()
        os.kill(os.getpid(), signal.SIGINT)

app = FastAPI(lifespan=lifespan)

def handle_httpx_exception(e: Exception):
    if isinstance(e, httpx.HTTPStatusError):
        # Pass upstream status code through, but keep a helpful message when the body is empty
        detail = e.response.text
        if not detail:
            reason = e.response.reason_phrase or "Error"
            detail = f"Upstream {e.response.status_code} {reason}"
        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )

    raise HTTPException(
        status_code=500,
        detail={
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc(),
        },
    )

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

@app.post("/create_food_from_fdcid/{fdcid}") 
def create_food_from_fdcid(fdcid: int, request: Request):

    #API Call to FDC to get food nutrition details
    httpx_client =  request.app.state.httpx_client
    url = "https://api.nal.usda.gov/fdc/v1/food/" + str(fdcid) + "?api_key=8yYwQ5HS4ddjLaDMsKIkTH8xCUOgucZqrLgcJuSP"
    try:
        resp = httpx_client.get(url)
        resp.raise_for_status()
        food = resp.json()
        foodname = food['description']

    except Exception as e:
        handle_httpx_exception(e)

    #Set DB Conn
    conn = None
    try:
        conn = sqlite3.connect(get_db_path())
        cur = conn.cursor()
        #Get the food record from local db first
        cur.execute("SELECT * from foods where FDC_ID = ?", (fdcid,))
        record = cur.fetchone()

        #Create new record for the food if food doesn't exist in local DB
        if record is None:
            cur.execute(
                "INSERT INTO foods ('FDC_ID','Name','Serving Size','Unit') VALUES (?, ?, ?, ?);",
                (fdcid, foodname, 100, "grams"),
            )
            conn.commit()
            print("New food inserted: " + foodname)
        else:
            return "Error: Food %d %s already exists in DB. Nothing was changed." % (fdcid, foodname)

        #Get all cols of food table
        cur.execute("PRAGMA table_info(foods)")
        cols = cur.fetchall()
        table_cols = []
        for col in cols:
            table_cols.append(col[1].strip())

        for nutrient in food['foodNutrients']:

            unwanted = re.search("^PUFA|^MUFA|^TFA|^SFA|^Water|^Ash", nutrient['nutrient']['name']) #I don't have those PUFA MUFA TFA SFA data

            #if nutrient entry has amount and not in unwanted list
            #Some of them don't have amount, so useless we skip
            if "amount" in nutrient and not unwanted:
                matching_table_col_name = nutrient['nutrient']['name'] + " " + nutrient['nutrient']['unitName']

                #create relevant nutrient column if the column doesn't exist
                if matching_table_col_name not in table_cols:
                    safe_col = matching_table_col_name.replace('"', '""')
                    cur.execute(
                        'ALTER TABLE foods ADD "%s" DECIMAL NOT NULL DEFAULT 0;' % safe_col
                    )
                    conn.commit()
                    print(matching_table_col_name + " Col Created")

                #Update all the "nutrient" column values in DB for the food
                safe_col = matching_table_col_name.replace('"', '""')
                cur.execute(
                    'UPDATE foods SET "%s" = ? WHERE FDC_ID = ?;' % safe_col,
                    (nutrient['amount'], fdcid),
                )
                conn.commit()
    finally:
        if conn is not None:
            conn.close()

    return "Food %d %s created" % (fdcid, foodname)


@app.put("/update_food_from_fdcid/{fdcid}") 
def update_food_from_fdcid(fdcid: int, request: Request):
    #API Call to FDC to get food nutrition details
    httpx_client =  request.app.state.httpx_client
    url = "https://api.nal.usda.gov/fdc/v1/food/" + str(fdcid) + "?api_key=8yYwQ5HS4ddjLaDMsKIkTH8xCUOgucZqrLgcJuSP"
    try:
        resp = httpx_client.get(url)
        resp.raise_for_status()
        food = resp.json()
        foodname = food['description']
    except Exception as e:
        handle_httpx_exception(e)

    #Set DB Conn
    conn = None
    try:
        conn = sqlite3.connect(get_db_path())
        cur = conn.cursor()
        #Get the food record from local db first
        cur.execute("SELECT * from foods where FDC_ID = ?", (fdcid,))
        record = cur.fetchone()

        #Exit if the food doesn't exist in local DB
        if record is None:
            return "Error: Food FDCID %d (%s) does not exist in DB. Nothing was changed." % (fdcid, foodname)

        #Get all cols of food table
        cur.execute("PRAGMA table_info(foods)")
        cols = cur.fetchall()
        table_cols = []
        for col in cols:
            table_cols.append(col[1].strip())

        for nutrient in food['foodNutrients']:

            unwanted = re.search("^PUFA|^MUFA|^TFA|^SFA|^Water|^Ash", nutrient['nutrient']['name']) #I don't have those PUFA MUFA TFA SFA data

            #if nutrient entry has amount and not in unwanted list
            #Some of them don't have amount, so useless we skip
            if "amount" in nutrient and not unwanted:
                matching_table_col_name = nutrient['nutrient']['name'] + " " + nutrient['nutrient']['unitName']

                #create relevant nutrient column if the column doesn't exist
                if matching_table_col_name not in table_cols:
                    safe_col = matching_table_col_name.replace('"', '""')
                    cur.execute(
                        'ALTER TABLE foods ADD "%s" DECIMAL NOT NULL DEFAULT 0;' % safe_col
                    )
                    conn.commit()
                    print(matching_table_col_name + " Col Created")

                #Update all the "nutrient" column values in DB for the food
                safe_col = matching_table_col_name.replace('"', '""')
                cur.execute(
                    'UPDATE foods SET "%s" = ? WHERE FDC_ID = ?;' % safe_col,
                    (nutrient['amount'], fdcid),
                )
                conn.commit()
    finally:
        if conn is not None:
            conn.close()
    
    return "Food %d %s updated" % (fdcid, foodname)

    
