Install uv on your operating system. https://docs.astral.sh/uv/getting-started/installation/

Setup an empty PostgreSQL database.

Open Command Prompt or shell in this directory / project root.

Run below command in project root folder to create the project python virtual environment & install project dependencies:
   - `uv sync`

Set below environment variables in a `.env` file:
  - `AuthCookieExpireSecs` (default: `315360000`)
  - `DB_OPS_PASS` (example: `"secretpassword"`)
  - `DATABASE_URL` (example: `"postgresql://postgres.syygijfhasdjkiqqolf:passxx23@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"`)
  - `FDC_API_KEY` (example: `"1yYw75HS4eekjyGhNgtHbH8xCUOgucZqrLgcJuSP"`)

Start the server:
   - Windows: `.\runapp.ps1`
   - macOS/Linux: `./runapp.sh`

Run below command in Git Bash or Linux Terminal to create the Database Tables. Replace the db_ops_pass value with what you set in .env file
   - `curl -X POST http://127.0.0.1:8000/api/admin/create_db_tables \
  -H "Content-Type: application/json" \
  -d '{"db_ops_pass":"secretpassword"}'`

Visit the app in your browser at url below
   - `http://127.0.0.1:8000`

Create an account, and begin analyzing your diets.

Tutorial video:
<iframe width="560" height="315" src="https://www.youtube.com/embed/qViczOMwgg8?si=BAqk0T_2-aQ2lumC" title="EvalDiet Tutorial" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>

Live Demo: [https://evaldiet.onrender.com/](https://evaldiet.onrender.com/)
