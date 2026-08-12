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
  - 보직자 피드백 / 코칭 메시지 및 면담록 등록 (SQLite DB 영속 저장)

### 3. 🤖 AI 보직자 성과 분석 & 리포트 (AI Executive Advisor)
- 버튼 클릭 한 번으로 관할 조직 성과 데이터 다차원 분석
- 부서별 성과 병목 원인 분석, 우수 연구원 추천 사유, C/D등급 위험군 1:1 면담 코칭 가이드 자동 작성

### 4. 📁 편리한 기능 및 데이터 내보내기 (Export & Theme)
- **다크 모드 / 라이트 모드**: 우측 상단 해/달 아이콘 클릭 시 즉시 테마 전환 (설정 유지)
- **CSV 데이터 다운로드**: 엑셀 한글 깨짐 방지(UTF-8 BOM)가 적용된 CSV 원클릭 내보내기

---

## 🛠️ 기술 스택 (Tech Stack)

- **Backend**: Python 3.12, Flask
- **Database**: SQLite 3
- **Frontend**: HTML5, Vanilla CSS3 (KRRI Navy/Cyan Palette), JavaScript (ES6+)
- **Data Visualization**: Chart.js

---

## 🚀 시작하기 (Getting Started)

### 1. 사전 요구사항
- Python 3.8 이상 설치

### 2. 프로젝트 설치 및 실행

#### Windows (원클릭 실행)
`run.bat` 파일을 더블 클릭하여 실행합니다.

#### 명령 프롬프트 (CMD / PowerShell)
```bash
# 1. 필수 패키지 설치
pip install -r requirements.txt

# 2. Flask 서버 구동
python app.py
```

### 3. 브라우저 접속
서버 구동 후 웹 브라우저에서 다음 주소로 접속합니다.
- **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

### 4. 환경변수 (선택)
기본값은 로컬 전용(`127.0.0.1`) · 디버그 모드 꺼짐입니다. 필요 시 아래 환경변수로 조정합니다.
- `FLASK_HOST` : 바인딩 주소 (기본 `127.0.0.1`, 원내망 공유 시 `0.0.0.0`)
- `FLASK_PORT` : 포트 (기본 `5000`)
- `FLASK_DEBUG` : `1`로 설정하면 디버그 모드 활성화 (운영 환경에서는 절대 사용 금지)

---

## 📂 프로젝트 구조 (Directory Structure)

```
직원관리용KPI대시보드/
├── app.py                     # Flask 백엔드 메인 서버 (REST API & SQLite DB 초기화)
├── kpi_database.db            # SQLite 데이터베이스 (앱 실행 시 자동 생성 및 데이터 시딩)
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
    └── index.html             # 메인 대시보드 및 모달 HTML 레이아웃
```

---

## 🔒 보안 및 라이선스
- 본 프로그램은 한국철도기술연구원(KRRI) 업무 효율화를 위해 제작된 KPI 성과관리용 내부 프로그램입니다.
