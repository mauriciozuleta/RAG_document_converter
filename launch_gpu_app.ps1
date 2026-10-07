$ErrorActionPreference = 'Stop'
$previousDevice = $env:PDF_RAG_OCR_DEVICE
try {
    $env:PDF_RAG_OCR_DEVICE = 'gpu:0'
    $appPython = Join-Path $PSScriptRoot '.venv-gpu\Scripts\pythonw.exe'
    if (-not (Test-Path -LiteralPath $appPython)) { throw 'GPU environment is not installed.' }
    Start-Process -FilePath $appPython -ArgumentList ('"' + (Join-Path $PSScriptRoot 'pdf_to_rag_ui.py') + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
} finally {
    $env:PDF_RAG_OCR_DEVICE = $previousDevice
}
