from contextlib import asynccontextmanager
from random import random
import string
import traceback
import os
import sqlite3
from typing import Union, Annotated
import httpx
from dotenv import load_dotenv
import signal
import random

from fastapi import FastAPI, HTTPException, Header, Request, Depends, Response, requests
from fastapi.params import Body
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

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

def random_alphanumeric(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# serve /static/...
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["rand_id"] = random_alphanumeric

@app.get("/")
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/foods")
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

@app.get("/api/diets/{diet_name}")
def get_diets(diet_name: str = "*"):
    conn = None
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if diet_name == "*":
            cur.execute("SELECT * FROM diets")
        else:
            cur.execute("SELECT * FROM diets WHERE diet_name = ?",(diet_name,))

        rows = cur.fetchall()
        return rows
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()

@app.get("/api/diets/{diet_name}/nutrition")
def diets_nutrition(diet_name: str):
    conn = None
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT diets.* FROM diets WHERE diets.diet_name = ?", (diet_name,))
        diet_items = [dict(row) for row in cur.fetchall()]

        cur.execute("SELECT * FROM foods")
        foods = [dict(row) for row in cur.fetchall()]

        foods_by_id = {}
        for food in foods:
            foods_by_id[food.get("fdc_id")] = food

        diet_calculated = []
        for diet_entry in diet_items:
            food = foods_by_id.get(diet_entry.get("fdc_id"))
            if not food:
                continue

            serving_size = food.get("Serving Size")
            try:
                serving_size = float(serving_size)
            except (TypeError, ValueError):
                serving_size = 0.0

            adjusted_food = dict(food)
            adjusted_food.pop("Serving Size", None)
            for key, value in food.items():
                if key in ("fdc_id", "Serving Size"):
                    continue
                if isinstance(value, (int, float)):
                    if serving_size > 0:
                        adjusted_value = round((float(value) / serving_size) * float(diet_entry.get("quantity", 0)), 2)
                    else:
                        adjusted_value = 0.0
                    adjusted_food[key] = adjusted_value

            merged = dict(diet_entry)
            merged.update(adjusted_food)
            diet_calculated.append(merged)

        return diet_calculated
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()

@app.post("/api/diet")
def create_diet(payload: DietCreate):
    conn = None
    try:
        conn = sqlite3.connect(get_db_path())
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO diets (diet_name, fdc_id, quantity, sort_order, color)
            VALUES (?, ?, ?, ?, ?)
            """,
            (payload.diet_name, payload.fdc_id, payload.quantity, payload.sort_order, payload.color),
        )
        conn.commit()
        return {"created": cur.rowcount}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()

@app.put("/api/diet/{name}")
def update_diet(name: str, payload: DietUpdate):
    conn = None
    try:
        conn = sqlite3.connect(get_db_path())
        cur = conn.cursor()
        original_fdc_id = payload.original_fdc_id if payload.original_fdc_id is not None else payload.fdc_id
        original_quantity = payload.original_quantity if payload.original_quantity is not None else payload.quantity
        original_sort_order = payload.original_sort_order if payload.original_sort_order is not None else payload.sort_order
        cur.execute(
            """
            UPDATE diets
            SET diet_name = ?, fdc_id = ?, quantity = ?, sort_order = ?, color = ?
            WHERE diet_name = ? AND fdc_id = ? AND quantity = ? AND sort_order = ?
            """,
            (
                payload.diet_name,
                payload.fdc_id,
                payload.quantity,
                payload.sort_order,
                payload.color,
                name,
                original_fdc_id,
                original_quantity,
                original_sort_order,
            ),
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

@app.post("/api/create_food_from_fdcid/{fdcid}") 
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
        cur.execute("SELECT * from foods where fdc_id = ?", (fdcid,))
        record = cur.fetchone()

        #Create new record for the food if food doesn't exist in local DB
        if record is None:
            cur.execute(
                "INSERT INTO foods ('fdc_id','Name','Serving Size','Unit') VALUES (?, ?, ?, ?);",
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
                    'UPDATE foods SET "%s" = ? WHERE fdc_id = ?;' % safe_col,
                    (nutrient['amount'], fdcid),
                )
                conn.commit()
    finally:
        if conn is not None:
            conn.close()

    return "Food %d %s created" % (fdcid, foodname)


@app.put("/api/update_food_from_fdcid/{fdcid}") 
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
        cur.execute("SELECT * from foods where fdc_id = ?", (fdcid,))
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
                    'UPDATE foods SET "%s" = ? WHERE fdc_id = ?;' % safe_col,
                    (nutrient['amount'], fdcid),
                )
                conn.commit()
    finally:
        if conn is not None:
            conn.close()
    
    return "Food %d %s updated" % (fdcid, foodname)


def get_db_path() -> str:
    return os.getenv("EVALDIET_DB_PATH", "app/evaldiet.db")

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
