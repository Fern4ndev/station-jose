[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Database,
    [Parameter(Mandatory = $true)]
    [string]$InputFile,
    [string]$Host = "localhost",
    [int]$Port = 5432,
    [string]$User = "postgres"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $InputFile -PathType Leaf)) {
    throw "No existe el backup indicado: $InputFile"
}

pg_restore --host=$Host --port=$Port --username=$User --dbname=$Database --no-owner --no-privileges --exit-on-error $InputFile
if ($LASTEXITCODE -ne 0) {
    throw "pg_restore terminó con código $LASTEXITCODE."
}

Write-Host "Backup restaurado en $Database"
