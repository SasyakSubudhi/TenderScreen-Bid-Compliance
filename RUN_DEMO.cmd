@echo off
setlocal
cd /d "%~dp0"
where docker >nul 2>&1
if errorlevel 1 goto use_wsl
if not exist .env docker run --rm -v "%CD%:/workspace" -w /workspace python:3.12-slim python scripts/configure.py
if not exist .env exit /b 1
docker compose up --build
exit /b %errorlevel%
:use_wsl
for /f "delims=" %%i in ('wsl -d Ubuntu -u root -- wslpath -u "%CD%"') do set "TENDER_LINUX_PATH=%%i"
if not defined TENDER_LINUX_PATH exit /b 1
wsl -d Ubuntu -u root -- docker info >nul 2>&1
if errorlevel 1 (
 echo Docker is not available. Start Docker Desktop or the Docker service in WSL Ubuntu.
 exit /b 1
)
if not exist .env wsl -d Ubuntu -u root --cd "%TENDER_LINUX_PATH%" -- python3 scripts/configure.py --build-network host
if not exist .env exit /b 1
echo Leave this window open while using the demo. Read API_TOKEN and API_PORT in your private .env file.
wsl -d Ubuntu -u root --cd "%TENDER_LINUX_PATH%" -- docker compose up --build
exit /b %errorlevel%
