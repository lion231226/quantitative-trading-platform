@echo off
echo Starting deployment...

cd frontend

if not exist ".env.local" (
    echo Creating .env.local from template...
    copy .env.example .env.local
    echo Please edit frontend\.env.local file with your settings
    pause
)

echo Building static files...
call npm run deploy:static

echo.
echo Deployment complete!
echo Static files are in frontend\out\ directory
echo You can upload these files to any static hosting service
echo.
echo For more options, see: frontend\DEPLOYMENT.md

pause