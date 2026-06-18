param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

function Normalize-Text {
    param([string]$Value)
    return ($Value -replace "`r`n", "`n").Trim()
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendPath = Join-Path $ProjectRoot "backend"
$FrontendPath = Join-Path $ProjectRoot "frontend"
$OldStaticPath = Join-Path $ProjectRoot "backend\app\static"

$RequiredFrontendFiles = @("index.html", "app.js", "styles.css")
foreach ($FileName in $RequiredFrontendFiles) {
    $Path = Join-Path $FrontendPath $FileName
    if (-not (Test-Path $Path)) {
        throw "Missing frontend source file: $Path"
    }
}

if (Test-Path $OldStaticPath) {
    $ManualCopies = Get-ChildItem -Path $OldStaticPath -Recurse -File |
        Where-Object { $_.Extension -in @(".html", ".js", ".css") }

    if ($ManualCopies.Count -gt 0) {
        $CopyList = ($ManualCopies | ForEach-Object { $_.FullName }) -join "`n"
        throw "backend/app/static still contains manually maintained frontend files:`n$CopyList"
    }
}

$AppJsPath = Join-Path $FrontendPath "app.js"
$AppJs = Get-Content -Raw -Encoding UTF8 $AppJsPath
if ($AppJs -notmatch 'const API_BASE = "";') {
    throw "frontend/app.js must use same-origin API calls so phone access works through the laptop server."
}

$PythonPath = Join-Path $BackendPath ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonPath)) {
    $PythonPath = "python"
}

$Server = Start-Process `
    -FilePath $PythonPath `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port") `
    -WorkingDirectory $BackendPath `
    -WindowStyle Hidden `
    -PassThru

try {
    Start-Sleep -Milliseconds 500
    if ($Server.HasExited) {
        throw "Verification server exited before it became reachable."
    }

    $BaseUrl = "http://127.0.0.1:$Port"
    $Deadline = (Get-Date).AddSeconds(20)
    $Ready = $false

    while ((Get-Date) -lt $Deadline) {
        try {
            $Health = Invoke-RestMethod -Uri "$BaseUrl/health"
            if ($Health.status -eq "ok") {
                $Ready = $true
                break
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    if (-not $Ready) {
        throw "Verification server did not become reachable at $BaseUrl."
    }

    $Index = (Invoke-WebRequest -Uri "$BaseUrl/" -UseBasicParsing).Content
    if ($Index -notmatch '/static/styles.css' -or $Index -notmatch '/static/app.js') {
        throw "Served index.html does not reference frontend assets through /static."
    }

    $ServedApp = (Invoke-WebRequest -Uri "$BaseUrl/static/app.js" -UseBasicParsing).Content
    $SourceApp = Get-Content -Raw -Encoding UTF8 (Join-Path $FrontendPath "app.js")
    if ((Normalize-Text $ServedApp) -ne (Normalize-Text $SourceApp)) {
        throw "Served app.js does not match frontend/app.js."
    }

    $ServedStyles = (Invoke-WebRequest -Uri "$BaseUrl/static/styles.css" -UseBasicParsing).Content
    $SourceStyles = Get-Content -Raw -Encoding UTF8 (Join-Path $FrontendPath "styles.css")
    if ((Normalize-Text $ServedStyles) -ne (Normalize-Text $SourceStyles)) {
        throw "Served styles.css does not match frontend/styles.css."
    }

    $Categories = Invoke-RestMethod -Uri "$BaseUrl/categories/"
    if ($Categories.Count -lt 1) {
        throw "Categories endpoint returned no categories."
    }

    Write-Host "Frontend single-source verification passed at $BaseUrl."
} finally {
    if ($Server -and -not $Server.HasExited) {
        Stop-Process -Id $Server.Id -Force
    }
}
