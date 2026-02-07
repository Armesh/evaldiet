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
            conn.executescript(
                """
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  hashed_password TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  settings TEXT NOT NULL DEFAULT '{"diet_columns": ["Name", "Unit", "Price", "Energy kcal", "Protein g", "Total lipid (fat) g", "Carbohydrate, by difference g", "Fiber, total dietary g", "Calcium, Ca mg", "Iron, Fe mg", "Magnesium, Mg mg", "Phosphorus, P mg", "Potassium, K mg", "Sodium, Na mg", "Zinc, Zn mg", "Copper, Cu mg", "Selenium, Se \u00b5g", "Vitamin C, total ascorbic acid mg", "Thiamin mg", "Riboflavin mg", "Niacin mg", "Pantothenic acid mg", "Vitamin B-6 mg", "Folate, total \u00b5g", "Vitamin B-12 \u00b5g", "Choline, total mg", "Vitamin A, RAE \u00b5g", "Cholesterol mg", "Fatty acids, total saturated g", "Vitamin E (alpha-tocopherol) mg", "Vitamin K, total \u00b5g", "Vitamin D (D2 + D3), International Units IU", "diet_name", "fdc_id", "quantity", "sort_order", "color"], "diet_hide_rda_ul_values": false, "diet_rda_threshold": 100, "diet_ul_threshold": 100, "food-dominant-carb": "#4c65b8", "food-dominant-fat": "#98823e", "food-dominant-protein": "#490303"}'
, last_login TIMESTAMP);

CREATE TABLE "foods" (
	"user_id"	INTEGER NOT NULL,
	"fdc_id"	INTEGER NOT NULL,
	"Name"	TEXT NOT NULL,
	"Serving Size"	INTEGER NOT NULL DEFAULT 100,
	"Unit"	TEXT NOT NULL DEFAULT 'grams',
	"Price"	REAL NOT NULL DEFAULT 999,
	"Energy kJ"	REAL NOT NULL DEFAULT 0,
	"Energy kcal"	REAL NOT NULL DEFAULT 0,
	"Protein g"	REAL NOT NULL DEFAULT 0,
	"Total lipid (fat) g"	REAL NOT NULL DEFAULT 0,
	"Carbohydrate, by difference g"	REAL NOT NULL DEFAULT 0,
	"Fiber, total dietary g"	REAL NOT NULL DEFAULT 0,
	"Calcium, Ca mg"	REAL NOT NULL DEFAULT 0,
	"Iron, Fe mg"	REAL NOT NULL DEFAULT 0,
	"Magnesium, Mg mg"	REAL NOT NULL DEFAULT 0,
	"Phosphorus, P mg"	REAL NOT NULL DEFAULT 0,
	"Potassium, K mg"	REAL NOT NULL DEFAULT 0,
	"Sodium, Na mg"	REAL NOT NULL DEFAULT 0,
	"Zinc, Zn mg"	REAL NOT NULL DEFAULT 0,
	"Copper, Cu mg"	REAL NOT NULL DEFAULT 0,
	"Selenium, Se µg"	REAL NOT NULL DEFAULT 0,
	"Vitamin C, total ascorbic acid mg"	REAL NOT NULL DEFAULT 0,
	"Thiamin mg"	REAL NOT NULL DEFAULT 0,
	"Riboflavin mg"	REAL NOT NULL DEFAULT 0,
	"Niacin mg"	REAL NOT NULL DEFAULT 0,
	"Pantothenic acid mg"	REAL NOT NULL DEFAULT 0,
	"Vitamin B-6 mg"	REAL NOT NULL DEFAULT 0,
	"Folate, total µg"	REAL NOT NULL DEFAULT 0,
	"Folic acid µg"	REAL NOT NULL DEFAULT 0,
	"Folate, food µg"	REAL NOT NULL DEFAULT 0,
	"Folate, DFE µg"	REAL NOT NULL DEFAULT 0,
	"Vitamin B-12 µg"	REAL NOT NULL DEFAULT 0,
	"Vitamin B-12, added µg"	REAL NOT NULL DEFAULT 0,
	"Choline, total mg"	REAL NOT NULL DEFAULT 0,
	"Vitamin A, RAE µg"	REAL NOT NULL DEFAULT 0,
	"Retinol µg"	REAL NOT NULL DEFAULT 0,
	"Vitamin A, IU IU"	REAL NOT NULL DEFAULT 0,
	"Cholesterol mg"	REAL NOT NULL DEFAULT 0,
	"Fatty acids, total saturated g"	REAL NOT NULL DEFAULT 0,
	"Fatty acids, total monounsaturated g"	REAL NOT NULL DEFAULT 0,
	"Fatty acids, total polyunsaturated g"	REAL NOT NULL DEFAULT 0,
	"Tryptophan g"	REAL NOT NULL DEFAULT 0,
	"Threonine g"	REAL NOT NULL DEFAULT 0,
	"Isoleucine g"	REAL NOT NULL DEFAULT 0,
	"Leucine g"	REAL NOT NULL DEFAULT 0,
	"Lysine g"	REAL NOT NULL DEFAULT 0,
	"Methionine g"	REAL NOT NULL DEFAULT 0,
	"Cystine g"	REAL NOT NULL DEFAULT 0,
	"Phenylalanine g"	REAL NOT NULL DEFAULT 0,
	"Tyrosine g"	REAL NOT NULL DEFAULT 0,
	"Valine g"	REAL NOT NULL DEFAULT 0,
	"Arginine g"	REAL NOT NULL DEFAULT 0,
	"Histidine g"	REAL NOT NULL DEFAULT 0,
	"Aspartic acid g"	REAL NOT NULL DEFAULT 0,
	"Glutamic acid g"	REAL NOT NULL DEFAULT 0,
	"Glycine g"	REAL NOT NULL DEFAULT 0,
	"Proline g"	REAL NOT NULL DEFAULT 0,
	"Serine g"	REAL NOT NULL DEFAULT 0,
	"Nitrogen g"	REAL NOT NULL DEFAULT 0,
	"Manganese, Mn mg"	REAL NOT NULL DEFAULT 0,
	"Total fat (NLEA) g"	REAL NOT NULL DEFAULT 0,
	"Vitamin D (D2 + D3), International Units IU"	REAL NOT NULL DEFAULT 0,
	"Vitamin D (D2 + D3) µg"	REAL NOT NULL DEFAULT 0,
	"Vitamin D3 (cholecalciferol) µg"	REAL NOT NULL DEFAULT 0,
	"Vitamin E (alpha-tocopherol) mg"	REAL NOT NULL DEFAULT 0,
	"Tocopherol, beta mg"	REAL NOT NULL DEFAULT 0,
	"Tocopherol, gamma mg"	REAL NOT NULL DEFAULT 0,
	"Tocopherol, delta mg"	REAL NOT NULL DEFAULT 0,
	"Tocotrienol, alpha mg"	REAL NOT NULL DEFAULT 0,
	"Tocotrienol, beta mg"	REAL NOT NULL DEFAULT 0,
	"Tocotrienol, gamma mg"	REAL NOT NULL DEFAULT 0,
	"Tocotrienol, delta mg"	REAL NOT NULL DEFAULT 0,
	"Vitamin E, added mg"	REAL NOT NULL DEFAULT 0,
	"Vitamin K (phylloquinone) µg"	REAL NOT NULL DEFAULT 0,
	"Vitamin K (Menaquinone-4) µg"	REAL NOT NULL DEFAULT 0,
	"Vitamin K (Menaquinone-7) µg"	REAL NOT NULL DEFAULT 0,
	"Vitamin K, total µg"	REAL NOT NULL DEFAULT 0,
	"Vitamin K (Dihydrophylloquinone) µg"	REAL NOT NULL DEFAULT 0,
	"Fatty acids, total trans g"	REAL NOT NULL DEFAULT 0,
	"Fatty acids, total trans-monoenoic g"	REAL NOT NULL DEFAULT 0,
	"Fatty acids, total trans-dienoic g"	REAL NOT NULL DEFAULT 0,
	"Sugars, total including NLEA g"	REAL NOT NULL DEFAULT 0,
	"Sucrose g"	REAL NOT NULL DEFAULT 0,
	"Glucose g"	REAL NOT NULL DEFAULT 0,
	"Fructose g"	REAL NOT NULL DEFAULT 0,
	"Lactose g"	REAL NOT NULL DEFAULT 0,
	"Maltose g"	REAL NOT NULL DEFAULT 0,
	"Galactose g"	REAL NOT NULL DEFAULT 0,
	"Betaine mg"	REAL NOT NULL DEFAULT 0,
	"Carotene, beta µg"	REAL NOT NULL DEFAULT 0,
	"Carotene, alpha µg"	REAL NOT NULL DEFAULT 0,
	"Cryptoxanthin, beta µg"	REAL NOT NULL DEFAULT 0,
	"Lycopene µg"	REAL NOT NULL DEFAULT 0,
	"Lutein + zeaxanthin µg"	REAL NOT NULL DEFAULT 0,
	"Phytosterols mg"	REAL NOT NULL DEFAULT 0,
	"Alanine g"	REAL NOT NULL DEFAULT 0,
	"Theobromine mg"	REAL NOT NULL DEFAULT 0,
	"Starch g"	REAL NOT NULL DEFAULT 0,
	"Hydroxyproline g"	REAL NOT NULL DEFAULT 0,
	"Fluoride, F µg"	REAL NOT NULL DEFAULT 0,
	"Fatty acids, total trans-polyenoic g"	REAL NOT NULL DEFAULT 0,
	"Stigmasterol mg"	REAL NOT NULL DEFAULT 0,
	"Campesterol mg"	REAL NOT NULL DEFAULT 0,
	"Beta-sitosterol mg"	REAL NOT NULL DEFAULT 0,
	"Alcohol, ethyl g"	REAL NOT NULL DEFAULT 0,
	"Caffeine mg"	REAL NOT NULL DEFAULT 0,
	"Sugars, added g"	REAL NOT NULL DEFAULT 0,
	"Sugars, Total g"	REAL NOT NULL DEFAULT 0,
	"Total Sugars g"	REAL NOT NULL DEFAULT 0,
	"Biotin µg"	REAL NOT NULL DEFAULT 0,
	"Cysteine g"	REAL NOT NULL DEFAULT 0,
	"Daidzein mg"	REAL NOT NULL DEFAULT 0,
	"Genistein mg"	REAL NOT NULL DEFAULT 0,
	"Daidzin mg"	REAL NOT NULL DEFAULT 0,
	"Genistin mg"	REAL NOT NULL DEFAULT 0,
	"Glycitin mg"	REAL NOT NULL DEFAULT 0, "Energy (Atwater General Factors) kcal" REAL NOT NULL DEFAULT 0, "Energy (Atwater Specific Factors) kcal" REAL NOT NULL DEFAULT 0, "Iodine, I µg" REAL NOT NULL DEFAULT 0,
	UNIQUE("user_id","Name"),
	UNIQUE("user_id","fdc_id"),
	FOREIGN KEY("user_id") REFERENCES "users"("id") ON DELETE CASCADE
);

CREATE TABLE "diets" (
	"user_id"	INTEGER NOT NULL,
	"diet_name"	TEXT NOT NULL,
	"fdc_id"	INTEGER NOT NULL,
	"quantity"	NUMERIC NOT NULL,
	"sort_order"	INTEGER NOT NULL,
	"color"	TEXT,
	FOREIGN KEY("user_id","fdc_id") REFERENCES "foods"("user_id","fdc_id") ON DELETE CASCADE,
	UNIQUE("user_id","diet_name","fdc_id","quantity","sort_order")
);

CREATE TABLE "RDA" (
    "id" INTEGER PRIMARY KEY,
    "user_id" INTEGER NOT NULL,
    "nutrient" TEXT NOT NULL,
    "value" REAL NOT NULL,
    UNIQUE ("user_id", "nutrient"),
    FOREIGN KEY ("user_id")
        REFERENCES "users"("id")
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE "UL" (
    "id" INTEGER PRIMARY KEY,
    "user_id" INTEGER NOT NULL,
    "nutrient" TEXT NOT NULL,
    "value" REAL NOT NULL,
    UNIQUE ("user_id", "nutrient"),
    FOREIGN KEY ("user_id")
        REFERENCES "users"("id")
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
                """
            )
            conn.commit()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        finally:
            conn.close()

        return {f"Database {db_path} Created"}

    return router
