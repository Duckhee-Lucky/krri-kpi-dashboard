@echo off
chcp 65001 > nul
echo ========================================================
echo   한국철도기술연구원 (KRRI) - 보직자 전용 직원 KPI 성과관리 대시보드
echo ========================================================
echo.

if "%DATABASE_URL%"=="" if "%POSTGRES_URL%"=="" (
    echo [!] DATABASE_URL 또는 POSTGRES_URL 환경변수가 설정되어 있지 않습니다.
    echo [!] 이 앱은 PostgreSQL 연결이 필요합니다. .env 파일에 DATABASE_URL을 설정하거나
    echo [!] "set DATABASE_URL=postgresql://..." 로 환경변수를 지정한 뒤 다시 실행해주세요.
    echo.
    pause
    exit /b
)

echo [1/2] 필수 파이썬 패키지 설치 확인 중...
python -m pip install -r requirements.txt
echo.
echo [2/2] KRRI KPI 대시보드 서버를 시작합니다...
echo.
echo  - 접속 주소: http://127.0.0.1:5000
echo  - 종료 방법: Ctrl + C
echo.
python app.py
pause
