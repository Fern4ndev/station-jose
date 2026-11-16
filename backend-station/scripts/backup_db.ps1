[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Database,
    [Parameter(Mandatory = $true)]
    [string]$OutputFile,
    [string]$Host = "localhost",
    [int]$Port = 5432,
    [string]$User = "postgres"
)

$ErrorActionPreference = "Stop"
$outputDirectory = Split-Path -Parent $OutputFile
if ($outputDirectory) {
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
}

pg_dump --format=custom --file=$OutputFile --host=$Host --port=$Port --username=$User --dbname=$Database --no-owner --no-privileges
if ($LASTEXITCODE -ne 0) {
    throw "pg_dump terminó con código $LASTEXITCODE."
}

Write-Host "Backup creado en $OutputFile"
