@echo off
echo ============================================================
echo   CHIEF OF STAFF EMAIL TRIAGE AGENT - GITHUB PUSH SCRIPT
echo ============================================================
echo.
echo This script will safely push your project to your GitHub repository:
echo https://github.com/Rehansheikh787/Cheif-of-staff-Ai.git
echo.
echo It respects your .gitignore, so your OAuth credentials and API keys
echo will NOT be uploaded to the public repository.
echo.
pause

echo.
echo [*] Initializing git repository...
git init

echo.
echo [*] Adding files (respecting .gitignore)...
git add .

echo.
echo [*] Creating commit...
git commit -m "Initial commit: Connected Gmail MCP & Gemini Triage Agent"

echo.
echo [*] Setting main branch...
git branch -M main

echo.
echo [*] Setting remote origin...
git remote remove origin >nul 2>&1
git remote add origin https://github.com/Rehansheikh787/Cheif-of-staff-Ai.git

echo.
echo [*] Pushing to GitHub...
echo.
echo Note: If prompted by Git, please authenticate in the browser window that opens.
echo.
git push -u origin main

echo.
echo ============================================================
echo   PUSH COMPLETE! Your repository is now live on GitHub.
echo ============================================================
echo.
pause
