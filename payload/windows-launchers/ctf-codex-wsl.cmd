@echo off
setlocal

REM ctf-codex.cmd -- wrapper for ctf-codex-wsl.ps1
REM Usage:
REM   ctf-codex.cmd <challenge>
REM   ctf-codex.cmd <challenge> -Resume
REM
REM Keep the original CMD role: only call the PowerShell launcher.
REM The PowerShell launcher then starts Codex inside Kali WSL.

set "SCRIPT_DIR=%~dp0"
set "PS1=%SCRIPT_DIR%ctf-codex-wsl.ps1"

if not exist "%PS1%" (
    set "PS1=%USERPROFILE%\ctf-codex-wsl.ps1"
)

if not exist "%PS1%" (
    echo [!] Cannot find ctf-codex-wsl.ps1
    echo [!] Put ctf-codex-wsl.ps1 in the same folder as this CMD file, or run ctf-codex-toolkit install-launchers
    exit /b 1
)

set "CTF_CODEX_CMD_WRAPPER=1"
where pwsh.exe >nul 2>nul
if errorlevel 1 (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
) else (
    pwsh.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
)

set "LAUNCH_EXIT=%ERRORLEVEL%"
if not "%LAUNCH_EXIT%"=="0" (
    echo.
    echo [!] CTF Codex WSL launcher exited with code %LAUNCH_EXIT%.
    echo [!] Review the error above. Press any key to close this window.
    pause >nul
)

exit /b %LAUNCH_EXIT%
