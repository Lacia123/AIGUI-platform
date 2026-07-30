@echo off
setlocal
cd /d "%~dp0"

REM Prefer project uv venv at repo root
set "ROOT=%~dp0..\.."
if exist "%ROOT%\.venv\Scripts\python.exe" (
  "%ROOT%\.venv\Scripts\python.exe" "%~dp0start_server.py" %*
  goto :eof
)

where uv >nul 2>nul
if %ERRORLEVEL%==0 (
  uv run --directory "%ROOT%" python "%~dp0start_server.py" %*
  goto :eof
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python start_server.py %*
  goto :eof
)

echo [提示] 未找到 uv/.venv/python，改用 npx serve...
npx --yes serve -l 8000 .
