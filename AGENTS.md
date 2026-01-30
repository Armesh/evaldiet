# Codex Agent Guide for evaldiet

## Purpose
This repo is a small diet/foods web app. Use this file as the single source of truth for how I want Codex to work in this project.

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

## Notes for Codex
- If you touch column-selection logic, keep required columns forced into storage and not user-toggleable in the settings UI.
- For diet items table editing: do not auto-save mid-edit; save only when leaving edit mode (clicking outside/switching rows/Escape).
- Ask before making large structural changes.
