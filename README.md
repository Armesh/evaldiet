Install uv on your operating system. https://docs.astral.sh/uv/getting-started/installation/
Open Command Prompt or shell in this directory.


Run below command to create/activate the environment and install deps:
   - `uv sync`

Start the server:
   - Windows: `.\runapp.ps1`
   - macOS/Linux: `./runapp.sh`

Open the app in your browser:
   - `http://127.0.0.1:8000`

Notes:
- Set required environment variables in a `.env` file:
  - `AuthCookieExpireSecs` (default: `3600`)
  - `EVALDIET_DB_PATH` (optional, default: `app/evaldiet.db`)
