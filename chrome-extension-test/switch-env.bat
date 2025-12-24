@echo off
setlocal

if "%1"=="" (
    echo Usage: switch-env.bat [dev^|prod]
    echo.
    echo   dev  - Switch to development mode (local testing)
    echo   prod - Switch to production mode (Web Store)
    exit /b 1
)

if "%1"=="dev" (
    echo Switching to DEVELOPMENT mode...
    copy /Y manifest.dev.json manifest.json
    echo.
    echo [DEV] manifest.json updated with dev client_id
    echo [DEV] Reload extension in chrome://extensions/
    exit /b 0
)

if "%1"=="prod" (
    echo Switching to PRODUCTION mode...
    git checkout manifest.json
    echo.
    echo [PROD] manifest.json restored to production version
    echo [PROD] DO NOT upload to Web Store with dev client_id!
    exit /b 0
)

echo Unknown option: %1
echo Use 'dev' or 'prod'
exit /b 1
