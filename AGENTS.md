# Codex Agent Guide for evaldiet

## Purpose
This repo is a small diet/foods web app. Use this file as the single source of truth for how I want Codex to work in this project.
It is a FastAPI application that serves Jinja2 templates with full page loads and redirects. It is not an SPA.

## Priorities
1. Keep diet table required columns always selected and hidden from the settings checklist:
   - diet_name, fdc_id, quantity, sort_order, color
2. Prefer minimal, targeted changes over refactors.

## Key files
- Frontend behavior: app/static/custom.js
- Settings UI: app/templates/settings.html
- Backend routes: app/main.py
- Environment: .env

## Run / test
- Run app: ./runapp.ps1 (Windows) or ./runapp.sh (macOS/Linux)
- No automated tests currently.

## UI conventions
- Keep existing AdminLTE/Bootstrap markup.
- Avoid adding new dependencies.
- Keep changes simple and readable; prefer plain JS.
- Avoid unnecessary defensive guards in JS (e.g., checking `document.body` before use) unless there’s a concrete risk.

## Notes for Codex
- If you touch column-selection logic, keep required columns forced into storage and not user-toggleable in the settings UI.
- For diet items table editing: do not auto-save mid-edit; save only when leaving edit mode (clicking outside/switching rows/Escape).
- Always re-check the latest file state before answering questions about current contents.
- SQL files in `app/` contain the `µg` character (e.g., `Biotin µg`). In PowerShell, use `Get-Content -Encoding utf8` to avoid mojibake (e.g., `µg` showing as `痢`).
- In foods edit UI, "Vitamin K, total µg" is a generated field and must not be editable or shown.
- Toasts: use the `msg-toast` class (no id), and ensure only one toast per page.
- This is not an SPA; avoid unnecessary defensive JS patterns like `_...Attached` flags for event handlers.
- Prefer Alpine.js patterns for UI events and state over manual DOM event listeners.
- When combining SortableJS with Alpine x-for lists, reordering can snap back unless you force a re-render; use a pattern like clearing the list and restoring it in a microtask.
- SQLite must always enforce foreign keys.
- Never change the database schema or data unless explicitly instructed.
- When editing HTML, keep attributes on a single line when reasonable; elements can span multiple lines.
- Ask before making large structural changes.


# Alpine.store('diet').dietItemNutritionList objects sample
[{
    "diet_name": "Meat",
    "fdc_id": 2445649,
    "quantity": 30,
    "sort_order": 3,
    "color": "#ad5322",
    "Name": "Animal Whey Protein Cookies & Cream",
    "Unit": "grams",
    "Price": 4.47,
    "Energy kJ": 0,
    "Energy kcal": 112.5,
    "Protein g": 23.44,
    "Total lipid (fat) g": 0.94,
    "Carbohydrate, by difference g": 1.88,
    "Fiber, total dietary g": 0,
    "Calcium, Ca mg": 131.4,
    "Iron, Fe mg": 0.38,
    "Magnesium, Mg mg": 18.6,
    "Phosphorus, P mg": 89.1,
    "Potassium, K mg": 131.4,
    "Sodium, Na mg": 112.5,
    "Zinc, Zn mg": 0,
    "Copper, Cu mg": 0,
    "Selenium, Se µg": 0,
    "Vitamin C, total ascorbic acid mg": 0,
    "Thiamin mg": 0,
    "Riboflavin mg": 0,
    "Niacin mg": 0,
    "Pantothenic acid mg": 0,
    "Vitamin B-6 mg": 0,
    "Folate, total µg": 0,
    "Folic acid µg": 0,
    "Folate, food µg": 0,
    "Folate, DFE µg": 0,
    "Vitamin B-12 µg": 0,
    "Vitamin B-12, added µg": 0,
    "Choline, total mg": 0,
    "Vitamin A, RAE µg": 0,
    "Retinol µg": 0,
    "Vitamin A, IU IU": 0,
    "Cholesterol mg": 23.4,
    "Fatty acids, total saturated g": 0.47,
    "Fatty acids, total monounsaturated g": 0,
    "Fatty acids, total polyunsaturated g": 0,
    "Tryptophan g": 0,
    "Threonine g": 0,
    "Isoleucine g": 0,
    "Leucine g": 0,
    "Lysine g": 0,
    "Methionine g": 0,
    "Cystine g": 0,
    "Phenylalanine g": 0,
    "Tyrosine g": 0,
    "Valine g": 0,
    "Arginine g": 0,
    "Histidine g": 0,
    "Aspartic acid g": 0,
    "Glutamic acid g": 0,
    "Glycine g": 0,
    "Proline g": 0,
    "Serine g": 0,
    "Nitrogen g": 0,
    "Manganese, Mn mg": 0,
    "Total fat (NLEA) g": 0,
    "Vitamin D (D2 + D3), International Units IU": 0,
    "Vitamin D (D2 + D3) µg": 0,
    "Vitamin D3 (cholecalciferol) µg": 0,
    "Vitamin E (alpha-tocopherol) mg": 0,
    "Tocopherol, beta mg": 0,
    "Tocopherol, gamma mg": 0,
    "Tocopherol, delta mg": 0,
    "Tocotrienol, alpha mg": 0,
    "Tocotrienol, beta mg": 0,
    "Tocotrienol, gamma mg": 0,
    "Tocotrienol, delta mg": 0,
    "Vitamin E, added mg": 0,
    "Vitamin K (phylloquinone) µg": 0,
    "Vitamin K (Menaquinone-4) µg": 0,
    "Vitamin K (Menaquinone-7) µg": 0,
    "Vitamin K, total µg": 0,
    "Vitamin K (Dihydrophylloquinone) µg": 0,
    "Fatty acids, total trans g": 0,
    "Fatty acids, total trans-monoenoic g": 0,
    "Fatty acids, total trans-dienoic g": 0,
    "Sugars, total including NLEA g": 0,
    "Sucrose g": 0,
    "Glucose g": 0,
    "Fructose g": 0,
    "Lactose g": 0,
    "Maltose g": 0,
    "Galactose g": 0,
    "Betaine mg": 0,
    "Carotene, beta µg": 0,
    "Carotene, alpha µg": 0,
    "Cryptoxanthin, beta µg": 0,
    "Lycopene µg": 0,
    "Lutein + zeaxanthin µg": 0,
    "Phytosterols mg": 0,
    "Alanine g": 0,
    "Theobromine mg": 0,
    "Starch g": 0,
    "Hydroxyproline g": 0,
    "Fluoride, F µg": 0,
    "Fatty acids, total trans-polyenoic g": 0,
    "Stigmasterol mg": 0,
    "Campesterol mg": 0,
    "Beta-sitosterol mg": 0,
    "Alcohol, ethyl g": 0,
    "Caffeine mg": 0,
    "Sugars, added g": 0.93,
    "Sugars, Total g": 0,
    "Total Sugars g": 1.88,
    "Biotin µg": 0,
    "Cysteine g": 0,
    "Daidzein mg": 0,
    "Genistein mg": 0,
    "Daidzin mg": 0,
    "Genistin mg": 0,
    "Glycitin mg": 0,
    "Iodine, I µg": 0,
    "Chlorine, Cl mg": 70.2
}]

# Response data from fetch("/api/users/me"). This is the user object in javascript.

{
    "id": 1,
    "username": "mesh",
    "created_at": "2026-02-08T07:42:00.074414+00:00",
    "last_login": "2026-02-12T13:31:13.581617+00:00",
    "settings": {
        "diet_columns": [
            "Name",
            "Unit",
            "Price",
            "Energy kcal",
            "Protein g",
            "Total lipid (fat) g",
            "Carbohydrate, by difference g",
            "Fiber, total dietary g",
            "Calcium, Ca mg",
            "Iron, Fe mg",
            "Magnesium, Mg mg",
            "Phosphorus, P mg",
            "Potassium, K mg",
            "Sodium, Na mg",
            "Zinc, Zn mg",
            "Copper, Cu mg",
            "Selenium, Se µg",
            "Vitamin C, total ascorbic acid mg",
            "Thiamin mg",
            "Riboflavin mg",
            "Niacin mg",
            "Pantothenic acid mg",
            "Vitamin B-6 mg",
            "Folate, total µg",
            "Vitamin B-12 µg",
            "Choline, total mg",
            "Vitamin A, RAE µg",
            "Cholesterol mg",
            "Fatty acids, total saturated g",
            "Vitamin E (alpha-tocopherol) mg",
            "Vitamin K, total µg",
            "Vitamin D (D2 + D3), International Units IU",
            "diet_name",
            "fdc_id",
            "quantity",
            "sort_order",
            "color"
        ],
        "diet_ul_threshold": 120,
        "food-dominant-fat": "#98823e",
        "diet_rda_threshold": 90,
        "food-dominant-carb": "#4c65b8",
        "food-dominant-protein": "#490303",
        "diet_hide_rda_ul_values": true
    }
}
