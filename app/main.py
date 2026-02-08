from contextlib import asynccontextmanager
from random import random
import string
import traceback
import logging
import os
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
from app.db_routes import get_db_router
from app.db.session import SessionLocal
from app.db.models import User, Food, Diet, RDA, UL, DEFAULT_SETTINGS
from sqlalchemy import select, update, delete, func, text
from sqlalchemy.orm import Session
import re

load_dotenv()  # loads .env from current working directory
logger = logging.getLogger(__name__)

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

def model_to_dict(obj) -> dict:
    return {col.name: getattr(obj, col.key) for col in obj.__table__.columns}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_auth_token_get_user(request: Request, db: Session = Depends(get_db)) -> dict:
    auth_token = request.cookies.get("auth_token")

    if auth_token:
        try:
            user = db.execute(
                select(User).where(User.hashed_password == auth_token).limit(1)
            ).scalar_one_or_none()
            if user is not None:
                return model_to_dict(user)
        except Exception:
            pass

    login_url = "/ui/login"
    raise HTTPException(
        status_code=307,
        detail="Unauthorized",
        headers={"Location": login_url},
    )

app.include_router(get_db_router())


# serve /static/...
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["rand_id"] = random_alphanumeric

@app.get("/")
def root(request: Request, user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
    user_id = user["id"]
    try:
        diet_name = db.execute(
            select(Diet.diet_name)
            .where(Diet.user_id == user_id)
            .order_by(Diet.diet_name.asc())
            .limit(1)
        ).scalar_one_or_none() or ""
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

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

@app.post("/api/register")
def register_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    captcha_code: str = Form(...),
    captcha_check: str | None = Form(None),
):
    raise HTTPException(status_code=501, detail="register_submit not migrated to PostgreSQL yet")
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
def login_submit(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        user = db.execute(
            select(User).where(User.username == username).limit(1)
        ).scalar_one_or_none()
        stored_password = user.hashed_password if user else None
        if not stored_password:
            raise HTTPException(status_code=401, detail="user doesn't exist")

        verified = verify_password(password, stored_password)
        if not verified:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        first_login = user.last_login is None
        user.last_login = func.now()
        db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

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
def get_me(user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
    try:
        db_user = db.execute(
            select(User).where(User.id == user["id"]).limit(1)
        ).scalar_one_or_none()
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        user_dict = model_to_dict(db_user)
        user_dict.pop("hashed_password", None)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return JSONResponse(user_dict)



@app.put("/api/users/me")
def update_me(payload: dict = Body(...), user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
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
                settings_obj = json.loads(settings_payload)
            else:
                settings_obj = settings_payload
            if not isinstance(settings_obj, dict):
                raise HTTPException(status_code=400, detail="Invalid settings payload")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid settings payload")
        updates["settings"] = settings_obj

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        if "username" in updates:
            existing = db.execute(
                select(User.id)
                .where(User.username == username, User.id != user_id)
                .limit(1)
            ).scalar_one_or_none()
            if existing is not None:
                raise HTTPException(status_code=400, detail="Username already exists")

        db_user = db.execute(
            select(User).where(User.id == user_id).limit(1)
        ).scalar_one_or_none()
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")

        if "username" in updates:
            db_user.username = updates["username"]
        if "hashed_password" in updates:
            db_user.hashed_password = updates["hashed_password"]
        if "settings" in updates:
            db_user.settings = updates["settings"]

        db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

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
def reset_user_settings(user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
    user_id = user["id"]
    try:
        default_settings = dict(DEFAULT_SETTINGS)
        db_user = db.execute(
            select(User).where(User.id == user_id).limit(1)
        ).scalar_one_or_none()
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        db_user.settings = default_settings
        db.commit()
        return JSONResponse({"settings": default_settings}, status_code=200)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/foods")
@app.get("/api/foods/{fdc_id}")
def get_foods(fdc_id: int | None = None, user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
    user_id = user["id"]
    try:
        if fdc_id is None:
            rows = db.execute(
                select(Food)
                .where(Food.user_id == user_id)
                .order_by(Food.fdc_id.asc())
            ).scalars().all()
            return strip_user_id([model_to_dict(row) for row in rows])
        row = db.execute(
            select(Food).where(Food.fdc_id == fdc_id, Food.user_id == user_id)
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Food not found")
        return strip_user_id(model_to_dict(row))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/foods/")
def create_food(payload: FoodCreate, user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
    user_id = user["id"]
    name = str(payload.name).strip()
    try:
        exists = db.execute(
            select(Food.fdc_id).where(Food.user_id == user_id, Food.name == name).limit(1)
        ).scalar_one_or_none()
        if exists is not None:
            raise HTTPException(status_code=400, detail="Food Name already exists")

        next_fdc_id = db.execute(
            select(func.coalesce(func.max(Food.fdc_id), 0) + 1)
            .where(Food.user_id == user_id, Food.fdc_id < 1000)
        ).scalar_one()
        db.add(Food(user_id=user_id, fdc_id=next_fdc_id, name=name))
        db.commit()
        return {"message": f"Created{next_fdc_id} : {name}", "fdc_id": next_fdc_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    
@app.put("/api/foods/{fdcid}")
def update_food(fdcid: int, payload: dict = Body(...), user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
    user_id = user["id"]
    try:
        valid_cols = {col.name for col in Food.__table__.columns}

        new_fdc_id = None
        if payload and "fdc_id" in payload:
            try:
                new_fdc_id = int(payload.get("fdc_id"))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid fdc_id")
            if new_fdc_id <= 0:
                raise HTTPException(status_code=400, detail="Invalid fdc_id")
            if new_fdc_id != fdcid:
                exists = db.execute(
                    select(Food.fdc_id).where(Food.fdc_id == new_fdc_id, Food.user_id == user_id).limit(1)
                ).scalar_one_or_none()
                if exists is not None:
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

        values = {Food.__table__.c[key]: value for key, value in updates.items()}
        result = db.execute(
            update(Food)
            .where(Food.fdc_id == fdcid, Food.user_id == user_id)
            .values(values)
        )
        db.commit()
        foodRowsUpdated = result.rowcount
        if foodRowsUpdated == 0:
            raise HTTPException(status_code=404, detail="Food not found")
        
        db.execute(
            text(
                'UPDATE foods SET "Vitamin K, total µg" = "Vitamin K (phylloquinone) µg" + "Vitamin K (Menaquinone-4) µg" + "Vitamin K (Menaquinone-7) µg" WHERE user_id = :user_id'
            ),
            {"user_id": user_id},
        )
        db.commit()
        return {"updated": foodRowsUpdated}

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.delete("/api/foods/{fdc_id}")
def delete_food(fdc_id: int, user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
    user_id = user["id"]
    try:
        result = db.execute(
            delete(Food).where(Food.fdc_id == fdc_id, Food.user_id == user_id)
        )
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Food not found")
        return {"deleted": result.rowcount}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/foods/create_update_food_from_fdcid/{fdcid}") 
def create_update_food_from_fdcid(fdcid: int, request: Request, user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
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

    try:
        record = db.execute(
            select(Food).where(Food.fdc_id == fdcid, Food.user_id == user_id).limit(1)
        ).scalar_one_or_none()

        #Create new record for the food if food doesn't exist in local DB
        if record is None:
            created = True
            db.add(Food(user_id=user_id, fdc_id=fdcid, name=foodname, serving_size=100, unit="grams"))
            db.commit()
            print("New food inserted: " + foodname)
        else:
            created = False

        #Get all cols of food table
        table_cols = {col.name for col in Food.__table__.columns}

        for nutrient in food['foodNutrients']:

            unwanted = re.search("^PUFA|^MUFA|^TFA|^SFA|^Water|^Ash", nutrient['nutrient']['name']) #I don't have those PUFA MUFA TFA SFA data

            #if nutrient entry has amount and not in unwanted list
            #Some of them don't have amount, so useless we skip
            if "amount" in nutrient and not unwanted:
                matching_table_col_name = nutrient['nutrient']['name'] + " " + nutrient['nutrient']['unitName']

                #create relevant nutrient column if the column doesn't exist
                if matching_table_col_name not in table_cols:
                    safe_col = matching_table_col_name.replace('"', '""')
                    logger.info("Starting ALTER TABLE foods ADD column: %s. Postgres is Locked", safe_col)
                    db.execute(
                        text(f'ALTER TABLE foods ADD "{safe_col}" NUMERIC(10, 3) NOT NULL DEFAULT 0.000')
                    )
                    db.commit()
                    logger.info("Completed ALTER TABLE foods ADD column: %s. Postgres Lock Released", safe_col)

                #Update all the "nutrient" column values in DB for the food
                safe_col = matching_table_col_name.replace('"', '""')
                db.execute(
                    text(f'UPDATE foods SET "{safe_col}" = :amount WHERE fdc_id = :fdc_id AND user_id = :user_id'),
                    {"amount": nutrient["amount"], "fdc_id": fdcid, "user_id": user_id},
                )
                db.commit()
        
        #do the total vitamin K calculation
        db.execute(
            text(
                'UPDATE foods SET "Vitamin K, total µg" = "Vitamin K (phylloquinone) µg" + "Vitamin K (Menaquinone-4) µg" + "Vitamin K (Menaquinone-7) µg" WHERE fdc_id = :fdc_id'
            ),
            {"fdc_id": fdcid},
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

    return f"Food {fdcid} {foodname} {'created' if created else 'updated'}"



@app.get("/api/diets/{diet_name}")
def get_diets(diet_name: str = "*", user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
    try:
        if diet_name == "*":
            rows = db.execute(
                select(Diet).where(Diet.user_id == user["id"])
            ).scalars().all()
        else:
            rows = db.execute(
                select(Diet).where(Diet.diet_name == diet_name, Diet.user_id == user["id"])
            ).scalars().all()

        return strip_user_id([model_to_dict(row) for row in rows])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/diets/{diet_name}/nutrition")
def diets_nutrition(diet_name: str, user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
    try:
        diet_items = strip_user_id([
            model_to_dict(row)
            for row in db.execute(
                select(Diet).where(Diet.diet_name == diet_name, Diet.user_id == user["id"])
            ).scalars().all()
        ])

        foods = strip_user_id([
            model_to_dict(row)
            for row in db.execute(
                select(Food).where(Food.user_id == user["id"])
            ).scalars().all()
        ])

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
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/rda")
def get_rda(user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
    try:
        rows = db.execute(
            select(RDA).where(RDA.user_id == user["id"])
        ).scalars().all()
        return strip_user_id([model_to_dict(row) for row in rows])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.put("/api/rda/{id}")
def update_rda(id: int, payload: RDAUpdate, user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
    user_id = user["id"]
    value = float(payload.value)

    try:
        row = db.execute(
            select(RDA).where(RDA.id == id, RDA.user_id == user_id).limit(1)
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="RDA not found")
        nutrient_name = str(row.nutrient or "").strip()

        row.value = value
        db.commit()
        return JSONResponse({"detail": f"Updated RDA {nutrient_name}"}, status_code=200)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/ul")
def get_ul(user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
    try:
        rows = db.execute(
            select(UL).where(UL.user_id == user["id"])
        ).scalars().all()
        return strip_user_id([model_to_dict(row) for row in rows])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.put("/api/ul/{id}")
def update_ul(id: int, payload: ULUpdate, user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
    user_id = user["id"]
    value = float(payload.value)

    try:
        row = db.execute(
            select(UL).where(UL.id == id, UL.user_id == user_id).limit(1)
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="UL not found")
        nutrient_name = str(row.nutrient or "").strip()

        row.value = value
        db.commit()
        return JSONResponse({"detail": f"Updated UL {nutrient_name}"}, status_code=200)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/diet")
def create_diet(payload: DietCreate, user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
    try:
        db.add(
            Diet(
                user_id=user["id"],
                diet_name=payload.diet_name,
                fdc_id=payload.fdc_id,
                quantity=payload.quantity,
                sort_order=payload.sort_order,
                color=payload.color,
            )
        )
        db.commit()
        return {"created": 1}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.put("/api/diet")
def update_diet(payload: DietUpdate, user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
    try:
        original_fdc_id = payload.original_fdc_id if payload.original_fdc_id is not None else payload.fdc_id
        original_quantity = payload.original_quantity if payload.original_quantity is not None else payload.quantity
        original_sort_order = payload.original_sort_order if payload.original_sort_order is not None else payload.sort_order
        result = db.execute(
            update(Diet)
            .where(
                Diet.user_id == user["id"],
                Diet.diet_name == payload.diet_name,
                Diet.fdc_id == original_fdc_id,
                Diet.quantity == original_quantity,
                Diet.sort_order == original_sort_order,
            )
            .values(
                diet_name=payload.diet_name,
                fdc_id=payload.fdc_id,
                quantity=payload.quantity,
                sort_order=payload.sort_order,
                color=payload.color,
            )
        )
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Diet not found")
        return {"updated": result.rowcount}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.delete("/api/diet")
def delete_diet(payload: DietDelete, user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
    try:
        if payload.delete_all:
            result = db.execute(
                delete(Diet).where(Diet.diet_name == payload.diet_name, Diet.user_id == user["id"])
            )
        else:
            result = db.execute(
                delete(Diet).where(
                    Diet.user_id == user["id"],
                    Diet.diet_name == payload.diet_name,
                    Diet.fdc_id == payload.fdc_id,
                    Diet.quantity == payload.quantity,
                    Diet.sort_order == payload.sort_order,
                )
            )
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Diet item not found")
        return {"deleted": result.rowcount}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.put("/api/diet/name_only")
def update_diet_name_only(payload: DietNameUpdate, user: dict = Depends(verify_auth_token_get_user), db: Session = Depends(get_db)):
    try:
        result = db.execute(
            update(Diet)
            .where(Diet.diet_name == payload.diet_name_old, Diet.user_id == user["id"])
            .values(diet_name=payload.diet_name_new)
        )
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Diet not found")
        return {"updated": result.rowcount}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

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
