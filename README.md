Install uv on your operating system. https://docs.astral.sh/uv/getting-started/installation/

Open Command Prompt or shell in this directory.

Run below command in project root folder to create the project python virtual environment & install project dependencies:
   - `uv sync`

Set below environment variables in a `.env` file:
  - `AuthCookieExpireSecs` (default: `315360000`)
  - `EVALDIET_DB_PATH` (default: `evaldiet.sqlite3`)
  - `DB_OPS_PASS`

Start the server:
   - Windows: `.\runapp.ps1`
   - macOS/Linux: `./runapp.sh`

Run below command in Git Bash or Linux Terminal to create the database. Replace the db_ops_pass value with what you set in .env file
   - `curl -X POST http://127.0.0.1:8000/api/admin/create_db \
  -H "Content-Type: application/json" \
  -d '{"db_ops_pass":"supersecretpassword"}'`

Open the app in your browser, Create an account, and begin using it:
   - `http://127.0.0.1:8000`
