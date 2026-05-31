param(
    [string]$InstallDir = "$env:ProgramFiles\Fixbot"
)

$ErrorActionPreference = "Stop"

function Test-Admin {
    $current = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($current)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
    $args = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -InstallDir `"$InstallDir`""
    Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $args
    exit 0
}

$sourceRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not (Test-Path $sourceRoot)) {
    Write-Error "Source folder not found: $sourceRoot"
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Warning "Python was not found in PATH. Fixbot needs Python 3.9+."
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$excludeDirs = @("venv", ".git", "reports", "memory", "__pycache__")
$robocopyArgs = @(
    $sourceRoot,
    $InstallDir,
    "/E",
    "/R:2",
    "/W:1",
    "/NFL",
    "/NDL",
    "/NP"
)
foreach ($dirName in $excludeDirs) {
    $robocopyArgs += "/XD"
    $robocopyArgs += (Join-Path $sourceRoot $dirName)
}

& robocopy @robocopyArgs | Out-Null

$fixbotCmdPath = Join-Path $InstallDir "fixbot.cmd"
$fixbotCmd = @"
@echo off
setlocal
cd /d "$InstallDir"
where python >nul 2>&1
if %errorlevel% neq 0 (
  where py >nul 2>&1
  if %errorlevel% neq 0 (
    echo Python not found. Install Python 3.9+ and retry.
    exit /b 1
  ) else (
    py -3 sysdoc\main.py %*
    exit /b %errorlevel%
  )
)
python sysdoc\main.py %*
"@
Set-Content -Path $fixbotCmdPath -Value $fixbotCmd -Encoding ASCII

$startAdminPath = Join-Path $InstallDir "start-fixbot-admin.ps1"
$startAdmin = @"
param([
    string]`$InstallDir = "$InstallDir"
])

`$cmdLine = "cd /d `"`$InstallDir`" ^& call `"`$InstallDir\fixbot.cmd`""
Start-Process -FilePath "cmd.exe" -Verb RunAs -ArgumentList "/k", `$cmdLine
"@
Set-Content -Path $startAdminPath -Value $startAdmin -Encoding ASCII

$envKey = "HKLM:\System\CurrentControlSet\Control\Session Manager\Environment"
$pathValue = (Get-ItemProperty -Path $envKey -Name Path).Path
$pathParts = $pathValue.Split(";", [System.StringSplitOptions]::RemoveEmptyEntries)
if ($pathParts -notcontains $InstallDir) {
    $newPath = ($pathParts + $InstallDir) -join ";"
    Set-ItemProperty -Path $envKey -Name Path -Value $newPath
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Fixbot (Admin).lnk"
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$startAdminPath`""
$shortcut.WorkingDirectory = $InstallDir
$shortcut.IconLocation = "$env:SystemRoot\System32\cmd.exe,0"
$shortcut.Save()

Write-Host "Fixbot installed to $InstallDir"
Write-Host "Desktop shortcut created: Fixbot (Admin)"
Write-Host "Open an elevated CMD and run: fixbot"
