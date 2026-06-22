$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ExportRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $ProjectRoot ".project-sources-export")
)
$ExpectedExportRoot = Join-Path $ProjectRoot ".project-sources-export"

if ($ExportRoot -ne $ExpectedExportRoot) {
    throw "Export path must remain inside the repository root."
}

$Documents = @(
    @{ Source = "README.md"; Destination = "README.md" },
    @{ Source = "AGENTS.md"; Destination = "AGENTS.md" },
    @{ Source = "docs\project_overview.md"; Destination = "project_overview.md" },
    @{ Source = "docs\mvp_v1_blueprint.md"; Destination = "mvp_v1_blueprint.md" },
    @{ Source = "docs\project_status.md"; Destination = "project_status.md" },
    @{ Source = "docs\decision_log.md"; Destination = "decision_log.md" }
)

$SchemaPath = Join-Path $ProjectRoot "docs\schema_v1.md"
if (Test-Path -LiteralPath $SchemaPath -PathType Leaf) {
    $Documents += @{ Source = "docs\schema_v1.md"; Destination = "schema_v1.md" }
}

foreach ($Document in $Documents) {
    $SourcePath = Join-Path $ProjectRoot $Document.Source
    if (-not (Test-Path -LiteralPath $SourcePath -PathType Leaf)) {
        throw "Required canonical document is missing: $($Document.Source)"
    }
}

if (Test-Path -LiteralPath $ExportRoot) {
    $ResolvedExportRoot = (Resolve-Path -LiteralPath $ExportRoot).Path
    if ($ResolvedExportRoot -ne $ExpectedExportRoot) {
        throw "Refusing to refresh an unexpected export directory: $ResolvedExportRoot"
    }
    Remove-Item -LiteralPath $ResolvedExportRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $ExportRoot | Out-Null

foreach ($Document in $Documents) {
    $SourcePath = Join-Path $ProjectRoot $Document.Source
    $DestinationPath = Join-Path $ExportRoot $Document.Destination
    Copy-Item -LiteralPath $SourcePath -Destination $DestinationPath
}

Write-Host "Exported $($Documents.Count) canonical Project Source files to $ExportRoot"
