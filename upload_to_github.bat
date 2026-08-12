@echo off
chcp 65001 > nul
echo ========================================================
echo   한국철도기술연구원 (KRRI) KPI 대시보드 - GitHub 업로드 도구
echo ========================================================
echo.

REM 1. Check if git command exists
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Git이 아직 시스템 환경변수(PATH)에 등록되지 않았거나 설치 중입니다.
    echo [!] Git 설치 완료 후 이 명령을 다시 실행해 주세요.
    pause
    exit /b
)

REM 2. Git init
if not exist ".git" (
    echo [1/4] Git 저장소(repository)를 초기화합니다...
    git init
    git branch -M main
) else (
    echo [1/4] 이미 Git 저장소가 설정되어 있습니다.
)

REM 3. Git add & commit
echo [2/4] 소스코드 및 커밋 대상을 추가합니다...
git add .
git commit -m "Initial commit: KRRI Executive Employee KPI Management Dashboard"

echo.
echo ========================================================
echo   GitHub 저장소 URL을 입력해 주세요.
echo   (예: https://github.com/내아이디/krri-kpi-dashboard.git)
echo ========================================================
set /p REPO_URL="GitHub Repository URL: "

if "%REPO_URL%"=="" (
    echo [!] URL이 입력되지 않았습니다. 커밋까지만 완료되었습니다.
    pause
    exit /b
)

REM 4. Remote add & Push
git remote remove origin >nul 2>nul
git remote add origin %REPO_URL%

echo.
echo [3/4] GitHub로 코드 업로드를 시작합니다...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo [ 성공! ] GitHub 저장소로 완벽하게 업로드되었습니다!
) else (
    echo.
    echo [!] 업로드 중 오류가 발생했습니다. GitHub 로그인 상태 또는 URL을 확인해 주세요.
)

echo.
pause
