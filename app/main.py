from contextlib import asynccontextmanager
from random import random
import string
import traceback
import os
import sqlite3
import base64
import hashlib
import hmac
import time
import json

import httpx
from dotenv import load_dotenv
import signal
import random

from fastapi import FastAPI, HTTPException, Request, Depends, Response, requests, Form
from fastapi.params import Body
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates

from fastapi.staticfiles import StaticFiles
from app.models import *
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

PBKDF2_ITERATIONS = 200_000

def hash_password(plain: str) -> str:
    if plain is None:
        raise ValueError("Password is required")
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", str(plain).encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{PBKDF2_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"

def verify_password(plain: str, stored: str) -> bool:
    try:
        iterations_str, salt_b64, hash_b64 = stored.split("$", 2)
        iterations = int(iterations_str)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
    except Exception:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", str(plain).encode("utf-8"), salt, iterations)
    return hmac.compare_digest(dk, expected)

def strip_user_id(data):
    if isinstance(data, dict):
        data.pop("user_id", None)
        return data
    if isinstance(data, list):
        return [strip_user_id(item) for item in data]
    return data

def verify_auth_token_get_user(request: Request) -> dict:
    auth_token = request.cookies.get("auth_token")

    if auth_token:
        conn = None
        try:
            conn = get_db_conn()
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE hashed_password = ? LIMIT 1", (auth_token,))
            row = cur.fetchone()
            if row is not None:
                return dict(row)
        except Exception:
            pass
        finally:
            if conn is not None:
                conn.close()

    login_url = "/ui/login"
    raise HTTPException(
        status_code=307,
        detail="Unauthorized",
        headers={"Location": login_url},
    )


# serve /static/...
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["rand_id"] = random_alphanumeric

@app.get("/")
def root(request: Request, user: dict = Depends(verify_auth_token_get_user)):
    user_id = user["id"]
    conn = None
    try:
        conn = get_db_conn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT diet_name FROM diets WHERE user_id = ? ORDER BY diet_name ASC LIMIT 1", (user_id,))
        row = cur.fetchone()
        diet_name = row[0] if row else ""
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()

    if diet_name:
        return RedirectResponse(url=f"/ui/diets?diet_name={diet_name}")
    return RedirectResponse(url="/ui/foods")

@app.get("/ui/login")
def login_page(request: Request):
    try:
        verify_auth_token_get_user(request)
        return RedirectResponse(url="/")
    except HTTPException:
        return templates.TemplateResponse("login.html", {"request": request})

@app.get("/ui/register")
def register_page(request: Request):
    try:
        verify_auth_token_get_user(request)
        return RedirectResponse(url="/")
    except HTTPException:
        captcha_code = random_alphanumeric(6)
        response = templates.TemplateResponse(
            "register.html",
            {"request": request, "reg_captcha_code": captcha_code},
        )
        response.set_cookie(
            key="reg_code",
            value=captcha_code,
            httponly=False,
            secure=False,
            samesite="lax",
            path="/",
            max_age=600,
        )
        return response

@app.get("/hashpassword/{password}")
def test_hash(password: str):
    return {"hash": hash_password(password)}

@app.get("/db_download_15890")
def db_download_15890(request: Request, user: dict = Depends(verify_auth_token_get_user)):
    db_path = os.path.join("app", "evaldiet.db")
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database not found")
    return FileResponse(db_path, media_type="application/octet-stream", filename="evaldiet.db")

@app.post("/api/register")
def register_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    captcha_code: str = Form(...),
    captcha_check: str | None = Form(None),
):
    conn = None
    try:
        reg_code = request.cookies.get("reg_code")
        if not reg_code or captcha_check is None or captcha_code.strip() != reg_code:
            raise HTTPException(status_code=400, detail="Captcha check failed")
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE username = ? LIMIT 1", (username,))
        if cur.fetchone() is not None:
            raise HTTPException(status_code=400, detail="Username already exists")

        hashed_password = hash_password(password)
        cur.execute(
            "INSERT INTO users (username, hashed_password, created_at) VALUES (?, ?, datetime('now'))",
            (username, hashed_password),
        )
        user_id = cur.lastrowid

        init_foods_path = os.path.join("app", "init_foods_data.sql")
        if os.path.exists(init_foods_path):
            with open(init_foods_path, "r", encoding="utf-8") as handle:
                sql_blob = handle.read()
            statements = [stmt.strip() for stmt in sql_blob.split(";") if stmt.strip()]
            for stmt in statements:
                stmt = re.sub(r"(VALUES\s*\(\s*)xx(\s*,)", rf"\g<1>{user_id}\g<2>", stmt)
                cur.execute(stmt)

        init_diets_path = os.path.join("app", "init_diets_data.sql")
        if os.path.exists(init_diets_path):
            with open(init_diets_path, "r", encoding="utf-8") as handle:
                sql_blob = handle.read()
            statements = [stmt.strip() for stmt in sql_blob.split(";") if stmt.strip()]
            for stmt in statements:
                stmt = re.sub(r"(VALUES\s*\(\s*)xx(\s*,)", rf"\g<1>{user_id}\g<2>", stmt)
                cur.execute(stmt)

        init_rdas_path = os.path.join("app", "init_rdas_data.sql")
        if os.path.exists(init_rdas_path):
            with open(init_rdas_path, "r", encoding="utf-8") as handle:
                sql_blob = handle.read()
            statements = [stmt.strip() for stmt in sql_blob.split(";") if stmt.strip()]
            for stmt in statements:
                stmt = re.sub(r"(VALUES\s*\(\s*)xx(\s*,)", rf"\g<1>{user_id}\g<2>", stmt)
                cur.execute(stmt)

        init_ul_path = os.path.join("app", "init_ul_data.sql")
        if os.path.exists(init_ul_path):
            with open(init_ul_path, "r", encoding="utf-8") as handle:
                sql_blob = handle.read()
            statements = [stmt.strip() for stmt in sql_blob.split(";") if stmt.strip()]
            for stmt in statements:
                stmt = re.sub(r"(VALUES\s*\(\s*)xx(\s*,)", rf"\g<1>{user_id}\g<2>", stmt)
                cur.execute(stmt)

        conn.commit()
        cur.execute("SELECT * FROM users WHERE id = ? LIMIT 1", (user_id,))
        created_user = cur.fetchone()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()

    response = login_submit(request, username=username, password=password)
    response.delete_cookie(key="reg_code", path="/")
    return response

@app.post("/api/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = None
    try:
        conn = get_db_conn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ? LIMIT 1", (username,))
        user = cur.fetchone()
        stored_password = user["hashed_password"] if user else None
        if not stored_password:
            raise HTTPException(status_code=401, detail="user doesn't exist")

        verified = verify_password(password, stored_password)
        if not verified:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        first_login = user["last_login"] is None
        cur.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user["id"],),
        )
        conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()

    redirect_url = "/ui/tutorial" if first_login else "/"
    response = JSONResponse(
        {"detail": "Login Successful", "redirect_url": redirect_url},
        status_code=200,
    )
    # --- SET AUTH COOKIE HERE ---
    response.set_cookie(
        key="auth_token",
        value=stored_password,
        httponly=True,        # JS cannot read
        secure=False,         # True in prod (HTTPS)
        samesite="lax",       # Same-domain
        path="/",
        max_age=int(os.getenv("AuthCookieExpireSecs", 60 * 60 * 24 * 365 * 10)) #default 10 years
    )
    return response

@app.post("/logout")
def logout(user: dict = Depends(verify_auth_token_get_user)):
    response = RedirectResponse(url="/ui/login", status_code=303)
    response.delete_cookie(key="auth_token", path="/")
    return response

@app.get("/ui/diets")
def diet_details(request: Request, diet_name: str, user: dict = Depends(verify_auth_token_get_user)):
    return templates.TemplateResponse("diets.html", {"request": request, "diet_name": diet_name})
    
@app.get("/ui/foods")
def all_foods(request: Request, user: dict = Depends(verify_auth_token_get_user)):
    return templates.TemplateResponse("foods.html", {"request": request})

@app.get("/ui/foods/edit/{fdc_id}")
def edit_food(request: Request, fdc_id: int, user: dict = Depends(verify_auth_token_get_user)):
    return templates.TemplateResponse("foods_edit.html", {"request": request, "fdc_id": fdc_id})

@app.get("/ui/tutorial")
def tutorial_page(request: Request, user: dict = Depends(verify_auth_token_get_user)):
    return templates.TemplateResponse("tutorial.html", {"request": request})

@app.get("/ui/rda_ul")
def rda_ul_page(request: Request, user: dict = Depends(verify_auth_token_get_user)):
    return templates.TemplateResponse("rda_ul.html", {"request": request})

@app.get("/ui/settings")
def settings_page(request: Request, user: dict = Depends(verify_auth_token_get_user)):
    return templates.TemplateResponse("settings.html", {"request": request})

@app.get("/ui/update_profile")
def update_profile_page(request: Request, user: dict = Depends(verify_auth_token_get_user)):
    return templates.TemplateResponse("update_profile.html", {"request": request, "user": user})




@app.get("/api/users/me")
def get_me(user: dict = Depends(verify_auth_token_get_user)):
    conn = get_db_conn()
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id= ? LIMIT 1", (user["id"],))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="User not found")
        user = dict(row)
        user.pop("hashed_password", None)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        conn.close()
    return JSONResponse(user)



@app.put("/api/users/me")
def update_me(payload: dict = Body(...), user: dict = Depends(verify_auth_token_get_user)):
    user_id = user["id"]
    username = payload.get("username") if isinstance(payload, dict) else None
    password = payload.get("password") if isinstance(payload, dict) else None

    updates = {}
    new_hashed_password = None

    if username is not None:
        username = str(username).strip()
        if not username:
            raise HTTPException(status_code=400, detail="Username is required")
        updates["username"] = username

    if password is not None:
        password = str(password)
        if not password:
            raise HTTPException(status_code=400, detail="Password is required")
        new_hashed_password = hash_password(password)
        updates["hashed_password"] = new_hashed_password

    if isinstance(payload, dict) and "settings" in payload:
        settings_payload = payload.get("settings")
        try:
            if isinstance(settings_payload, str):
                json.loads(settings_payload)
                settings_json = settings_payload
            else:
                settings_json = json.dumps(settings_payload)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid settings payload")
        updates["settings"] = settings_json

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        if "username" in updates:
            cur.execute("SELECT 1 FROM users WHERE username = ? AND id != ? LIMIT 1", (username, user_id))
            if cur.fetchone() is not None:
                raise HTTPException(status_code=400, detail="Username already exists")

        set_clause = ", ".join([f"\"{col}\" = ?" for col in updates.keys()])
        values = list(updates.values()) + [user_id]
        cur.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()

    response = JSONResponse({"updated": True}, status_code=200)
    max_age = int(os.getenv("AuthCookieExpireSecs", 60 * 60 * 24 * 365 * 10)) #default 10 years
    if new_hashed_password:
        response.set_cookie(
            key="auth_token",
            value=new_hashed_password,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/",
            max_age=max_age,
        )
    return response

@app.post("/api/users/me/reset_settings")
def reset_user_settings(user: dict = Depends(verify_auth_token_get_user)):
    user_id = user["id"]
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT dflt_value FROM pragma_table_info('users') WHERE name = 'settings'")
        row = cur.fetchone()
        if not row or row[0] is None:
            raise HTTPException(status_code=500, detail="Settings default not defined")
        default_value = str(row[0])
        if len(default_value) >= 2 and default_value[0] == default_value[-1] and default_value[0] in ("'", '"'):
            default_value = default_value[1:-1]
        try:
            parsed = json.loads(default_value)
        except Exception:
            raise HTTPException(status_code=500, detail="Invalid settings default JSON")
        cur.execute("UPDATE users SET settings = ? WHERE id = ?", (default_value, user_id))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
        return JSONResponse({"settings": parsed}, status_code=200)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()

@app.get("/api/foods")
@app.get("/api/foods/{fdc_id}")
def get_foods(fdc_id: int | None = None, user: dict = Depends(verify_auth_token_get_user)):
    user_id = user["id"]
    conn = None
    try:
        conn = get_db_conn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if fdc_id is None:
            cur.execute("SELECT * FROM foods WHERE user_id = ? ORDER BY fdc_id ASC", (user_id,))
            rows = cur.fetchall()
            return strip_user_id([dict(row) for row in rows])
        cur.execute("SELECT * FROM foods WHERE fdc_id = ? AND user_id = ?", (fdc_id, user_id))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Food not found")
        return strip_user_id(dict(row))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()

@app.put("/api/foods/{fdcid}")
def update_food(fdcid: int, payload: dict = Body(...), user: dict = Depends(verify_auth_token_get_user)):
    user_id = user["id"]
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(foods)")
        cols = [row[1] for row in cur.fetchall()]
        valid_cols = set(cols)

        new_fdc_id = None
        if payload and "fdc_id" in payload:
            try:
                new_fdc_id = int(payload.get("fdc_id"))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid fdc_id")
            if new_fdc_id <= 0:
                raise HTTPException(status_code=400, detail="Invalid fdc_id")
            if new_fdc_id != fdcid:
                cur.execute("SELECT 1 FROM foods WHERE fdc_id = ? AND user_id = ?", (new_fdc_id, user_id))
                if cur.fetchone() is not None:
                    raise HTTPException(status_code=400, detail="fdc_id already exists")

        updates = {}
        for key, value in (payload or {}).items():
            if key == "fdc_id":
                continue
            if key in valid_cols:
                updates[key] = value
        if new_fdc_id is not None and new_fdc_id != fdcid:
            updates["fdc_id"] = new_fdc_id

        if not updates:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        set_clause = ", ".join([f"\"{col.replace('\"', '\"\"')}\" = ?" for col in updates.keys()])
        values = list(updates.values()) + [fdcid, user_id]
        cur.execute(f"UPDATE foods SET {set_clause} WHERE fdc_id = ? AND user_id = ?", values)
        conn.commit()
        foodRowsUpdated = cur.rowcount
        if foodRowsUpdated == 0:
            raise HTTPException(status_code=404, detail="Food not found")
        
        cur.execute('UPDATE foods SET "Vitamin K, total µg" = "Vitamin K (phylloquinone) µg" + "Vitamin K (Menaquinone-4) µg" + "Vitamin K (Menaquinone-7) µg" WHERE user_id = ?', (user_id,))
        conn.commit()
        return {"updated": foodRowsUpdated}

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        conn.close()

@app.delete("/api/foods/{fdc_id}")
def delete_food(fdc_id: int, user: dict = Depends(verify_auth_token_get_user)):
    user_id = user["id"]
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM foods WHERE fdc_id = ? AND user_id = ?", (fdc_id, user_id))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Food not found")
        return {"deleted": cur.rowcount}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()


@app.post("/api/foods/create_update_food_from_fdcid/{fdcid}") 
def create_update_food_from_fdcid(fdcid: int, request: Request, user: dict = Depends(verify_auth_token_get_user)):
    user_id = user["id"]
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
        conn = get_db_conn()
        cur = conn.cursor()
        #Get the food record from local db first
        cur.execute("SELECT * from foods where fdc_id = ? AND user_id = ?", (fdcid, user_id))
        record = cur.fetchone()

        #Create new record for the food if food doesn't exist in local DB
        if record is None:
            created = True
            cur.execute(
                "INSERT INTO foods ('user_id','fdc_id','Name','Serving Size','Unit') VALUES (?, ?, ?, ?, ?);",
                (user_id, fdcid, foodname, 100, "grams"),
            )
            conn.commit()
            print("New food inserted: " + foodname)
        else:
            created = False

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
                        'ALTER TABLE foods ADD "%s" REAL NOT NULL DEFAULT 0;' % safe_col
                    )
                    conn.commit()
                    print(matching_table_col_name + " Col Created")

                #Update all the "nutrient" column values in DB for the food
                safe_col = matching_table_col_name.replace('"', '""')
                cur.execute(
                    'UPDATE foods SET "%s" = ? WHERE fdc_id = ? AND user_id = ?;' % safe_col,
                    (nutrient['amount'], fdcid, user_id),
                )
                conn.commit()
        
        #do the total vitamin K calculation
        cur.execute('UPDATE foods SET "Vitamin K, total µg" = "Vitamin K (phylloquinone) µg" + "Vitamin K (Menaquinone-4) µg" + "Vitamin K (Menaquinone-7) µg" WHERE fdc_id = ?', (fdcid,))
        conn.commit()
    finally:
        if conn is not None:
            conn.close()

    return f"Food {fdcid} {foodname} {'created' if created else 'updated'}"



@app.get("/api/diets/{diet_name}")
def get_diets(diet_name: str = "*", user: dict = Depends(verify_auth_token_get_user)):
    conn = None
    try:
        conn = get_db_conn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if diet_name == "*":
            cur.execute("SELECT * FROM diets WHERE user_id = ?", (user["id"],))
        else:
            cur.execute("SELECT * FROM diets WHERE diet_name = ? AND user_id = ?",(diet_name, user["id"]))

        rows = cur.fetchall()
        return strip_user_id([dict(row) for row in rows])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()

@app.get("/api/diets/{diet_name}/nutrition")
def diets_nutrition(diet_name: str, user: dict = Depends(verify_auth_token_get_user)):
    conn = None
    try:
        conn = get_db_conn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT diets.* FROM diets WHERE diets.diet_name = ? AND user_id = ?", (diet_name, user["id"]))
        diet_items = strip_user_id([dict(row) for row in cur.fetchall()])

        cur.execute("SELECT * FROM foods WHERE user_id = ?", (user["id"],))
        foods = strip_user_id([dict(row) for row in cur.fetchall()])

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
                        adjusted_value = 0.00
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

@app.get("/api/rda")
def get_rda(user: dict = Depends(verify_auth_token_get_user)):
    conn = None
    try:
        conn = get_db_conn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM RDA WHERE user_id = ?", (user["id"],))
        rows = cur.fetchall()
        return strip_user_id([dict(row) for row in rows])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()

@app.put("/api/rda/{id}")
def update_rda(id: int, payload: RDAUpdate, user: dict = Depends(verify_auth_token_get_user)):
    user_id = user["id"]
    value = float(payload.value)

    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT nutrient FROM RDA WHERE id = ? AND user_id = ? LIMIT 1", (id, user_id))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="RDA not found")
        nutrient_name = str(row[0] or "").strip()

        cur.execute(
            "UPDATE RDA SET value = ? WHERE id = ? AND user_id = ?",
            (value, id, user_id),
        )
        conn.commit()
        return JSONResponse({"detail": f"Updated RDA {nutrient_name}"}, status_code=200)
    finally:
        conn.close()

@app.get("/api/ul")
def get_ul(user: dict = Depends(verify_auth_token_get_user)):
    conn = None
    try:
        conn = get_db_conn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM UL WHERE user_id = ?", (user["id"],))
        rows = cur.fetchall()
        return strip_user_id([dict(row) for row in rows])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()

@app.put("/api/ul/{id}")
def update_ul(id: int, payload: ULUpdate, user: dict = Depends(verify_auth_token_get_user)):
    user_id = user["id"]
    value = float(payload.value)

    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT nutrient FROM UL WHERE id = ? AND user_id = ? LIMIT 1", (id, user_id))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="UL not found")
        nutrient_name = str(row[0] or "").strip()

        cur.execute(
            "UPDATE UL SET value = ? WHERE id = ? AND user_id = ?",
            (value, id, user_id),
        )
        conn.commit()
        return JSONResponse({"detail": f"Updated UL {nutrient_name}"}, status_code=200)
    finally:
        conn.close()

@app.post("/api/diet")
def create_diet(payload: DietCreate, user: dict = Depends(verify_auth_token_get_user)):
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO diets (user_id, diet_name, fdc_id, quantity, sort_order, color)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user["id"], payload.diet_name, payload.fdc_id, payload.quantity, payload.sort_order, payload.color),
        )
        conn.commit()
        return {"created": cur.rowcount}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()

@app.put("/api/diet")
def update_diet(payload: DietUpdate, user: dict = Depends(verify_auth_token_get_user)):
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        original_fdc_id = payload.original_fdc_id if payload.original_fdc_id is not None else payload.fdc_id
        original_quantity = payload.original_quantity if payload.original_quantity is not None else payload.quantity
        original_sort_order = payload.original_sort_order if payload.original_sort_order is not None else payload.sort_order
        cur.execute(
            """
            UPDATE diets
            SET diet_name = ?, fdc_id = ?, quantity = ?, sort_order = ?, color = ?
            WHERE user_id = ? AND diet_name = ? AND fdc_id = ? AND quantity = ? AND sort_order = ?
            """,
            (
                payload.diet_name,
                payload.fdc_id,
                payload.quantity,
                payload.sort_order,
                payload.color,
                user["id"],
                payload.diet_name,
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

@app.delete("/api/diet")
def delete_diet(payload: DietDelete, user: dict = Depends(verify_auth_token_get_user)):
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        if payload.delete_all:
            cur.execute("DELETE FROM diets WHERE diet_name = ? AND user_id = ?", (payload.diet_name, user["id"]))
        else:
            cur.execute(
                """
                DELETE FROM diets
                WHERE user_id = ? AND diet_name = ? AND fdc_id = ? AND quantity = ? AND sort_order = ?
                """,
                (user["id"], payload.diet_name, payload.fdc_id, payload.quantity, payload.sort_order),
            )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Diet item not found")
        return {"deleted": cur.rowcount}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()

@app.put("/api/diet/name_only")
def update_diet_name_only(payload: DietNameUpdate, user: dict = Depends(verify_auth_token_get_user)):
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE diets SET diet_name = ? WHERE diet_name = ? AND user_id = ?",
            (payload.diet_name_new, payload.diet_name_old, user["id"]),
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

def get_db_path() -> str:
    return os.getenv("EVALDIET_DB_PATH", "app/evaldiet.db")

def get_db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.execute("PRAGMA foreign_keys = ON")
    # Enforce FK support for every connection.
    fk_enabled = conn.execute("PRAGMA foreign_keys").fetchone()
    if not fk_enabled or fk_enabled[0] != 1:
        raise RuntimeError("SQLite foreign_keys must be enabled.")
    return conn

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
