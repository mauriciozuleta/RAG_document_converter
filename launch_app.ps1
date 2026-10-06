$ErrorActionPreference = 'Stop'
$appPython = Join-Path $PSScriptRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $appPython)) {
    throw 'Install the local environment first: python -m venv .venv; .\.venv\Scripts\python -m pip install -r requirements-ocr.txt'
}
Start-Process -FilePath $appPython -ArgumentList ('"' + (Join-Path $PSScriptRoot 'pdf_to_rag_ui.py') + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
