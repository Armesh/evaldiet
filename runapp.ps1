Set-Location $PSScriptRoot

# Resolve venv python explicitly (do NOT rely on PATH)
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

# Arguments as an array (important for Start-Process)
$uvicornArgs = @(
    '-m', 'uvicorn',
    'app.main:app',
    '--reload',
    '--host', '127.0.0.1',
    '--port', '8000',
    '--use-colors'
)

# The -NoNewWindow is needed for ouput text in PowerShell to have colors, else all ANSI code will fail to process into colors.
Start-Process `
    -FilePath $python `
    -ArgumentList $uvicornArgs `
    -NoNewWindow `
    -Wait
