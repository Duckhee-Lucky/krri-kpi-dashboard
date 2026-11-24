# 🚄 한국철도기술연구원(KRRI) 보직자 전용 직원 KPI 성과관리 대시보드

> **Executive Employee KPI Management & Performance Analytics System**  
> 본 웹 애플리케이션은 한국철도기술연구원(KRRI)의 보직자(본부장, 센터장, 실장)가 관할 연구원 및 직원의 KPI 목표 설정, 실적 진행 상황 모니터링, 정량·정성 평가, 면담록 작성 및 AI 기반 성과 분석을 종합 수행할 수 있도록 개발된 Python Flask 기반 대시보드입니다.

---

## 🌟 주요 기능 (Key Features)

### 1. 📊 보직자 통합 성과 대시보드 (Executive Dashboard)
- **요약 KPI 메트릭 카드**: 관할 전체 직원 수, 평균 KPI 목표 달성률(%), S/A등급 우수 성과자 수, 관심/지연 집중관리 인원 자동 센싱
- **부서별 달성률 비교 (Bar Chart)**: 미래교통물류연구소, 차세대철도차량연구센터, 스마트전력·신호연구실, 철도구조·해상교량연구실, 철도안전·환경연구실 비교
- **분기별 성과 진행 추이 (Line Chart)**: Q1~Q4 진행 곡선 추적
- **KPI 영역별 가중치/달성도 (Radar Chart)**: 논문/R&D, 특허/IP, 과제수주, 기술이전/사업화, 안전/관리
- **보직자 성과 평가 등급 분포 (Donut Chart)**: S, A, B, C, D 등급 비중 시각화

### 2. 📋 직원별 세부 KPI & 보직자 1:1 평가 관리 (Employee Detail & Evaluation)
- **직원 프로필 배너**: 사번, 성명, 직급, 소속 부서, 주요 연구 분야, 이메일
- **세부 KPI 항목 테이블**: 실적치 수치 수정, 신규 KPI 항목 추가(`+ KPI 목표 추가`), 항목 삭제
- **보직자 1:1 평가 & 면담록**: 
  - 정량/정성 평가 점수 (0~100점)
  - 성과 등급 부여 (S/A/B/C/D)
  - 보직자 피드백 / 코칭 메시지 및 면담록 등록 (PostgreSQL DB 영속 저장)

### 3. 🤖 AI 보직자 성과 분석 & 리포트 (AI Executive Advisor)
- 버튼 클릭 한 번으로 관할 조직 성과 데이터 다차원 분석
- 부서별 성과 병목 원인 분석, 우수 연구원 추천 사유, C/D등급 위험군 1:1 면담 코칭 가이드 자동 작성

### 4. 📁 편리한 기능 및 데이터 내보내기 (Export & Theme)
- **다크 모드 / 라이트 모드**: 우측 상단 해/달 아이콘 클릭 시 즉시 테마 전환 (설정 유지)
- **CSV 데이터 다운로드**: 엑셀 한글 깨짐 방지(UTF-8 BOM)가 적용된 CSV 원클릭 내보내기

---

## 🛠️ 기술 스택 (Tech Stack)

- **Backend**: Python 3.12, Flask
- **Database**: PostgreSQL (예: Vercel Postgres / Neon)
- **Frontend**: HTML5, Vanilla CSS3 (KRRI Navy/Cyan Palette), JavaScript (ES6+)
- **Data Visualization**: Chart.js
- **Deployment**: Vercel (서버리스, `@vercel/python`)

---

## 🚀 시작하기 (Getting Started)

### 1. 사전 요구사항
- Python 3.8 이상 설치
- PostgreSQL 데이터베이스 (로컬 Postgres, 또는 Neon/Vercel Postgres 등 무료 호스팅 DB)

### 2. 환경변수 설정 (필수)
이 앱은 SQLite 대신 PostgreSQL을 사용합니다. 프로젝트 루트에 `.env` 파일을 만들고 연결 문자열을 지정합니다.
```
DATABASE_URL=postgresql://user:password@host:5432/dbname?sslmode=require
```
(Vercel Postgres/Neon을 쓴다면 해당 대시보드에서 발급된 connection string을 그대로 붙여넣으면 됩니다.)

### 3. 로그인 계정 준비 (필수)
모든 화면과 API는 로그인한 사용자만 쓸 수 있습니다. 역할은 두 가지입니다.
- **admin (관리자)**: 전체 부서 열람·관리
- **manager (보직자)**: 자기 소속 부서 직원만 열람·평가·KPI 수정 (다른 부서를 요청해도 서버가 자기 부서로 고정)

`.env`에 세션 서명 키와 최초 관리자 계정을 지정합니다. 사용자가 한 명도 없을 때 첫 실행에서 관리자 계정이 자동 생성됩니다.
```
SECRET_KEY=임의의-긴-문자열   # python -c "import secrets; print(secrets.token_hex(32))"
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=충분히-긴-비밀번호
```
보직자 계정은 명령어로 만듭니다 (같은 아이디로 다시 실행하면 비밀번호 재설정):
```bash
flask --app app create-user --username ftl_head --name "홍길동 연구소장" --role manager --dept-code FTL
flask --app app deactivate-user ftl_head   # 계정 비활성화 (즉시 로그아웃)
```
부서 코드: `FTL` 미래교통물류연구소, `NRV` 차세대철도차량연구센터, `SPS` 스마트전력·신호연구실, `SMB` 철도구조·해상교량연구실, `RSE` 철도안전·환경연구실.
Vercel에 배포한 경우에도 로컬에서 같은 `DATABASE_URL`을 지정하고 위 명령을 실행하면 됩니다.

### 4. 프로젝트 설치 및 실행

#### Windows (원클릭 실행)
`run.bat` 파일을 더블 클릭하여 실행합니다. (`.env`에 `DATABASE_URL`이 없으면 안내 메시지를 띄우고 종료합니다.)

#### 명령 프롬프트 (CMD / PowerShell)
```bash
# 1. 필수 패키지 설치
pip install -r requirements.txt

# 2. Flask 서버 구동
python app.py
```
최초 실행 시 테이블 생성 및 더미 시드 데이터 삽입이 자동으로 수행됩니다.

### 5. 브라우저 접속
서버 구동 후 웹 브라우저에서 다음 주소로 접속합니다.
- **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

### 6. 환경변수 목록
- `DATABASE_URL` (또는 `POSTGRES_URL`) : PostgreSQL 연결 문자열 (**필수**)
- `SECRET_KEY` : 로그인 세션 서명 키 (**필수**, `FLASK_DEBUG=1`일 때만 생략 가능하며 재시작마다 로그아웃됨)
- `INITIAL_ADMIN_USERNAME` / `INITIAL_ADMIN_PASSWORD` : 사용자가 없을 때 만들 최초 관리자 계정
- `SESSION_COOKIE_SECURE` : `1`이면 HTTPS에서만 세션 쿠키 전송 (Vercel에서는 자동으로 `1`)
- `FLASK_HOST` : 바인딩 주소 (기본 `127.0.0.1`, 원내망 공유 시 `0.0.0.0`) — 로컬 실행 시에만 적용
- `FLASK_PORT` : 포트 (기본 `5000`) — 로컬 실행 시에만 적용
- `FLASK_DEBUG` : `1`로 설정하면 디버그 모드 활성화 (운영 환경에서는 절대 사용 금지)

---

## ☁️ Vercel 배포 (Deployment)

이 저장소는 Vercel 서버리스(`@vercel/python`)로 배포할 수 있도록 `vercel.json`과 `api/index.py`가 포함되어 있습니다.

1. **[vercel.com](https://vercel.com)** 에서 이 GitHub 저장소를 Import 합니다 (New Project → Import Git Repository).
2. 프로젝트 생성 후 **Storage** 탭에서 Postgres 데이터베이스를 생성하고 프로젝트에 연결합니다.
   - Vercel이 자동으로 `DATABASE_URL`(또는 `POSTGRES_URL`) 환경변수를 프로젝트에 주입합니다.
   - **Settings → Environment Variables**에 `SECRET_KEY`, `INITIAL_ADMIN_USERNAME`, `INITIAL_ADMIN_PASSWORD`를 추가합니다.
3. **Deploy**를 실행합니다. 첫 요청 시 `app.py`의 `init_db()`가 실행되어 테이블 생성과 시드 데이터 삽입이 자동으로 이루어집니다.
4. 배포 완료 후 발급된 `https://*.vercel.app` 주소로 접속하면 됩니다.

> ⚠️ **주의**: Vercel 서버리스 함수는 파일시스템이 읽기전용이라 SQLite 파일 기반 저장은 동작하지 않습니다. 이 때문에 DB를 PostgreSQL로 전환했습니다 — 로컬 개발 시에도 반드시 `DATABASE_URL`을 PostgreSQL 연결 문자열로 지정해야 합니다.

> ℹ️ 동시에 여러 서버리스 인스턴스가 최초 콜드 스타트를 겪을 경우 시드 데이터가 중복 삽입될 가능성이 이론적으로 존재합니다 (부서/직원 테이블은 `ON CONFLICT DO NOTHING`으로 보호되어 있으나 KPI 테이블은 그렇지 않음). 트래픽이 매우 적은 내부 도구 특성상 실제 발생 가능성은 낮지만, 만약 중복이 발견되면 DB에서 수동으로 정리해주세요.

---

## 📂 프로젝트 구조 (Directory Structure)

```
직원관리용KPI대시보드/
├── app.py                     # Flask 백엔드 메인 서버 (REST API & PostgreSQL DB 초기화)
├── api/
│   └── index.py                # Vercel 서버리스 함수 진입점 (app.py의 Flask 앱을 그대로 사용)
├── vercel.json                 # Vercel 빌드/라우팅 설정
├── requirements.txt           # Python 패키지 의존성 파일
├── run.bat                    # 윈도우 원클릭 서버 실행 배치 파일
├── .gitignore                 # Git 버전 관리 제외 설정 파일
├── README.md                  # 프로젝트 설명서
├── static/
│   ├── css/
│   │   └── style.css          # KRRI 브랜드 디자인 시스템 & 다크모드 테마
│   └── js/
│       └── main.js            # Chart.js 시각화 및 대시보드 인터랙션 로직
└── templates/
    ├── index.html             # 메인 대시보드 및 모달 HTML 레이아웃
    └── login.html             # 로그인 화면
```

---

## 🔒 보안 및 라이선스
- 본 프로그램은 한국철도기술연구원(KRRI) 업무 효율화를 위해 제작된 KPI 성과관리용 내부 프로그램입니다.
