@echo off
setlocal EnableExtensions
cd /d "%~dp0"

where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    py -3 "%~dp0reformat_pdf_windows.py" %*
) else (
    python "%~dp0reformat_pdf_windows.py" %*
)

endlocal & exit /b %ERRORLEVEL%
