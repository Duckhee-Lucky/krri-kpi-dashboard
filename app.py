import os
import csv
import io
import secrets
from datetime import date, timedelta
from functools import wraps
import click
import psycopg2
import psycopg2.extras
from flask import (Flask, render_template, request, jsonify, Response,
                   session, redirect, url_for, g)
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__, template_folder='templates', static_folder='static')


def _load_secret_key():
    key = os.environ.get('SECRET_KEY')
    if key:
        return key
    if os.environ.get('FLASK_DEBUG', '0') == '1':
        # Local debugging only: sessions reset on every restart.
        return secrets.token_hex(32)
    raise RuntimeError(
        'SECRET_KEY 환경변수가 설정되어 있지 않습니다. 로그인 세션 서명에 필요하므로 '
        '임의의 긴 문자열(예: python -c "import secrets; print(secrets.token_hex(32))")을 설정해주세요.'
    )


app.config.update(
    SECRET_KEY=_load_secret_key(),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    # Vercel sets VERCEL=1; there the site is always served over HTTPS.
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', '1' if os.environ.get('VERCEL') else '0') == '1',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)

ROLE_ADMIN = 'admin'      # 전체 부서 열람/관리 (예: 원장, 기획부서)
ROLE_MANAGER = 'manager'  # 자기 부서 소속 직원만 열람/관리 (본부장/센터장/실장)

# Per-employee KPI achievement, weighted by each KPI's weight (consistent
# across the summary, table and detail views instead of a plain average).
EMP_SCORE_CTE = '''
WITH emp_scores AS (
    SELECT e.id AS emp_id,
           CASE WHEN SUM(k.weight) > 0
                THEN SUM(k.progress_pct * k.weight)::float / SUM(k.weight)
                ELSE 0 END AS weighted_pct,
           COUNT(k.id) AS kpi_count,
           SUM(CASE WHEN k.status = '지연' THEN 1 ELSE 0 END) AS delayed_kpi_cnt
    FROM employees e
    LEFT JOIN kpis k ON k.emp_id = e.id
    GROUP BY e.id
)
'''

def get_database_url():
    for key in ('DATABASE_URL', 'POSTGRES_URL', 'POSTGRES_PRISMA_URL'):
        value = os.environ.get(key)
        if value:
            return value
    raise RuntimeError(
        'DATABASE_URL (또는 POSTGRES_URL) 환경변수가 설정되어 있지 않습니다. '
        'PostgreSQL 연결 문자열을 환경변수로 설정한 뒤 다시 실행해주세요.'
    )

def get_db():
    conn = psycopg2.connect(get_database_url(), cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

def parse_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def parse_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS departments (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        code TEXT NOT NULL UNIQUE
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id SERIAL PRIMARY KEY,
        emp_no TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        dept_id INTEGER NOT NULL,
        position TEXT NOT NULL,
        email TEXT,
        research_area TEXT,
        project_participation_pct INTEGER DEFAULT 100,
        eval_grade TEXT DEFAULT 'B',
        eval_score INTEGER DEFAULT 80,
        eval_feedback TEXT,
        eval_date TEXT,
        FOREIGN KEY (dept_id) REFERENCES departments(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS kpis (
        id SERIAL PRIMARY KEY,
        emp_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        weight INTEGER NOT NULL,
        target_val REAL NOT NULL,
        current_val REAL NOT NULL,
        unit TEXT NOT NULL,
        status TEXT NOT NULL, -- '완료', '정상진행', '관심필요', '지연'
        target_date TEXT,
        progress_pct INTEGER NOT NULL,
        description TEXT,
        FOREIGN KEY (emp_id) REFERENCES employees(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        display_name TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('admin', 'manager')),
        dept_id INTEGER REFERENCES departments(id),
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CHECK (role = 'admin' OR dept_id IS NOT NULL)
    )
    ''')

    # Check if seed data exists
    cursor.execute('SELECT COUNT(*) AS cnt FROM departments')
    if cursor.fetchone()['cnt'] == 0:
        seed_data(cursor)

    bootstrap_admin(cursor)

    conn.commit()
    cursor.close()
    conn.close()

def seed_data(cursor):
    departments = [
        ("미래교통물류연구소", "FTL"),
        ("차세대철도차량연구센터", "NRV"),
        ("스마트전력·신호연구실", "SPS"),
        ("철도구조·해상교량연구실", "SMB"),
        ("철도안전·환경연구실", "RSE")
    ]
    cursor.executemany('INSERT INTO departments (name, code) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING', departments)

    employees = [
        # 미래교통물류연구소
        ("KR201501", "김철수", 1, "수석연구원", "cskim@krri.re.kr", "하이퍼튜브 기밀시스템 및 추진기술", 90, "S", 96, "국가 대형 과제 주도 및 SCI 최우수 논문 게재. 하이퍼튜브 연구 성과 우수.", "2026-06-30"),
        ("KR201804", "박지민", 1, "책임연구원", "jmpark@krri.re.kr", "스마트 도시철도 물류 자동화", 85, "A", 88, "물류 모듈 시험 검증 완료. 하반기 특허 추가 등록 추진 필요.", "2026-06-28"),
        ("KR202110", "이민준", 1, "선임연구원", "mjlee@krri.re.kr", "자율주행 셔틀 철도 연계 제어", 80, "B", 78, "기술이전 협상 진행 중, 실적 중간 점검 관리 필요.", "2026-06-25"),
        ("KR202302", "최서연", 1, "연구원", "sychoi@krri.re.kr", "미래 물류 수요 예측 AI 모델", 75, "C", 64, "논문 제출 일정 지연. 보직자 면담을 통한 추진 차질 보완 조치 필요.", "2026-07-02"),

        # 차세대철도차량연구센터
        ("KR201402", "정성훈", 2, "수석연구원", "shjung@krri.re.kr", "수소전기열차 하이브리드 동력원", 95, "S", 98, "수소열차 실증 주행 성공 및 산업부/국토부 장관상 대상 후보.", "2026-06-29"),
        ("KR201708", "강현우", 2, "책임연구원", "hwkang@krri.re.kr", "고속철도 차축 댐핑 및 추진제어", 85, "A", 91, "특허 출원 4건 목표 조기 달성. 기술이전 수지 확보 우수.", "2026-06-27"),
        ("KR202012", "윤아름", 2, "선임연구원", "aryoon@krri.re.kr", "철도차량 경량 복합소재 구조체", 80, "B", 82, "시험 수행 절차 정상 진행 중. 목표 달성 무난 예상.", "2026-06-30"),
        ("KR202205", "임동현", 2, "연구원", "dhlim@krri.re.kr", "차량 진동 대역 센싱 시뮬레이션", 70, "B", 79, "신입 연구원으로서 업무 적응도 높음, 학술활동 독려 필요.", "2026-06-20"),

        # 스마트전력·신호연구실
        ("KR201205", "한동진", 3, "수석연구원", "djhan@krri.re.kr", "KTCS-3 무선통합 신호제어", 90, "A", 92, "철도 신호 국산화 표준화 기여. 연구비 수주 목표 달성.", "2026-06-26"),
        ("KR201903", "오세훈", 3, "책임연구원", "shoh@krri.re.kr", "스마트 무선급전 수신기 전력변환", 85, "B", 84, "무선급전 효율 92% 달성. 연구 성과 논문 작성 중.", "2026-06-24"),
        ("KR202107", "송지은", 3, "선임연구원", "jesong@krri.re.kr", "차세대 변전소 에너지 저장장치(ESS)", 80, "A", 87, "ESS 과제 중간평가 우수 판정. 사업화 추진 양호.", "2026-06-28"),
        ("KR202401", "배현준", 3, "연구원", "hjbae@krri.re.kr", "디지털트윈 기반 전력망 모니터링", 75, "C", 68, "연구 데이터 수집 지연으로 인한 실적 보완 필요.", "2026-07-01"),

        # 철도구조·해상교량연구실
        ("KR201309", "임재범", 4, "수석연구원", "jblim@krri.re.kr", "해상철도 교량 장대화 및 내진 설계", 95, "S", 95, "해상교량 모니터링 기술 완성도 높음. 과제 수주 35억원 수주 완료.", "2026-06-30"),
        ("KR201611", "권유진", 4, "책임연구원", "yjkwon@krri.re.kr", "철도 구조물 3D 가상점검 시스템", 85, "A", 90, "현장 실증 테스트 완료. 지자체 기술 이전 협약 체결.", "2026-06-27"),
        ("KR202004", "신동욱", 4, "선임연구원", "dwshin@krri.re.kr", "콘크리트 궤도 균열 자동 복구재", 80, "B", 81, "특허 등록 완료, 시험편 내구성 검증 진행 중.", "2026-06-22"),
        ("KR202309", "황보람", 4, "연구원", "brhwang@krri.re.kr", "교량 하부 구조 진동 데이터 분석", 70, "D", 58, "실적 목표 대비 달성률 미진 (58%). 1:1 보직자 집중 면담 대상.", "2026-07-03"),

        # 철도안전·환경연구실
        ("KR201103", "장태성", 5, "수석연구원", "tsjang@krri.re.kr", "철도 터널 미세먼지 수집 및 공기청정", 90, "A", 89, "지하철역사 미세먼지 저감장치 설치 완료, 실증 우수.", "2026-06-29"),
        ("KR201801", "문소희", 5, "책임연구원", "shmoon@krri.re.kr", "철도 소음·진동 저감 댐퍼", 85, "A", 87, "소음 저감 효과 5dB 확인, 기술이전 계약 체결 완료.", "2026-06-25"),
        ("KR202109", "서진우", 5, "선임연구원", "jwseo@krri.re.kr", "철도 사고 위험 예측 Big Data 시스템", 80, "B", 80, "안전 관리 데이터 구축 정상 추진 중.", "2026-06-28"),
        ("KR202311", "조은지", 5, "연구원", "ejcho@krri.re.kr", "친환경 철도 방음벽 소재 연구", 75, "C", 66, "시험 데이터 수집 일정이 순연됨. 3분기 내 만회 계획 작성 필요.", "2026-07-02")
    ]
    cursor.executemany('''
    INSERT INTO employees (emp_no, name, dept_id, position, email, research_area, project_participation_pct, eval_grade, eval_score, eval_feedback, eval_date)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (emp_no) DO NOTHING
    ''', employees)

    # Specific KPIs
    kpis = [
        # 김철수 (emp_id 1)
        (1, "SCI(E)급 논문 게재 (IF > 4.0)", "논문/R&D", 30, 2.0, 2.0, "건", "완료", "2026-06-30", 100, "하이퍼튜브 관련 Q1 저널 2편 게재 완료"),
        (1, "국내외 특허 출원 및 등록", "특허/IP", 25, 4.0, 5.0, "건", "완료", "2026-08-30", 125, "국제특허(PCT) 1건 포함 총 5건 출원"),
        (1, "정부 R&D 대형과제 수주", "과제수주", 25, 30.0, 35.0, "억원", "완료", "2026-11-30", 116, "국토교통부 과제 35억원 수주"),
        (1, "기술이전 계약 체결 실적", "기술이전/사업화", 20, 2.0, 1.5, "억원", "정상진행", "2026-12-15", 75, "기술료 1.5억원 협약 체결 완료"),

        # 박지민 (emp_id 2)
        (2, "SCI급 논문 게재", "논문/R&D", 25, 2.0, 2.0, "건", "완료", "2026-06-30", 100, "물류 자동화 논문 2편 게재"),
        (2, "특허 출원 실적", "특허/IP", 25, 3.0, 2.0, "건", "정상진행", "2026-10-31", 66, "2건 출원 완료, 1건 작성 중"),
        (2, "도시철도 물류 실증 시험", "과제수주", 30, 100.0, 90.0, "%", "정상진행", "2026-09-30", 90, "1호선 시험선로 시험 90% 완료"),
        (2, "부서 내 연구 안전 및 협업", "안전/관리", 20, 100.0, 100.0, "점", "완료", "2026-06-30", 100, "안전점검 무사고 달성"),

        # 최서연 (emp_id 4)
        (4, "KCI/SCI 논문 작성 및 제출", "논문/R&D", 35, 2.0, 0.5, "건", "지연", "2026-06-30", 25, "실험 데이터 재분석으로 초고 제출 지연"),
        (4, "AI 물류 예측 특허 출원", "특허/IP", 25, 1.0, 1.0, "건", "완료", "2026-05-15", 100, "국내 특허 출원 완료"),
        (4, "위탁 연구 과제 관리", "과제수주", 20, 100.0, 70.0, "%", "관심필요", "2026-09-30", 70, "위탁 기관 중간 보고서 수정 중"),
        (4, "학술대회 발표", "논문/R&D", 20, 2.0, 1.0, "건", "정상진행", "2026-11-20", 50, "춘계학술대회 1건 발표 완료"),

        # 정성훈 (emp_id 5)
        (5, "수소열차 최고 평가 실증", "과제수주", 35, 100.0, 100.0, "%", "완료", "2026-05-31", 100, "주행거리 5,000km 무고장 실증 성공"),
        (5, "국제 저널 SCI 논문", "논문/R&D", 25, 3.0, 3.0, "건", "완료", "2026-06-30", 100, "Applied Energy 등 저널 3편"),
        (5, "핵심 기술이전 수지", "기술이전/사업화", 25, 3.0, 3.2, "억원", "완료", "2026-06-15", 106, "현대로템 기술이전 완료"),
        (5, "특허 등록 실적", "특허/IP", 15, 2.0, 2.0, "건", "완료", "2026-04-30", 100, "특허 2건 등록 결정"),

        # 황보람 (emp_id 16)
        (16, "교량 진동 데이터 수집 및 분석", "논문/R&D", 40, 100.0, 50.0, "%", "지연", "2026-06-30", 50, "현장 계측 장비 고장으로 데이터 수집 지연"),
        (16, "특허 출원", "특허/IP", 30, 1.0, 0.0, "건", "지연", "2026-09-30", 0, "명세서 검토 단계 미착수"),
        (16, "연구실 안전 관리", "안전/관리", 30, 100.0, 80.0, "%", "정상진행", "2026-12-31", 80, "정기 안전 교육 이수 완료")
    ]

    # Populate dummy KPIs for other employees so every employee has at least 3 KPIs
    category_list = ["논문/R&D", "특허/IP", "과제수주", "기술이전/사업화", "안전/관리"]
    for emp_id in range(1, 21):
        if emp_id not in [1, 2, 4, 5, 16]:
            kpis.append((emp_id, "SCI/KCI 학술 논문 게재", category_list[0], 30, 2.0, 1.5, "건", "정상진행", "2026-10-30", 75, "논문 작성 및 수정 진행 중"))
            kpis.append((emp_id, "연구 관련 지식재산권(특허) 출원", category_list[1], 25, 2.0, 2.0, "건", "완료", "2026-06-20", 100, "특허 출원 완료"))
            kpis.append((emp_id, "주요 연구과제 세부목표 달성", category_list[2], 25, 100.0, 85.0, "%", "정상진행", "2026-11-15", 85, "연구 진도율 85% 달성"))
            kpis.append((emp_id, "기술지원 및 안전/관리 실적", category_list[4], 20, 100.0, 90.0, "점", "정상진행", "2026-12-01", 90, "원내 기술 지원 및 보안 준수"))

    cursor.executemany('''
    INSERT INTO kpis (emp_id, title, category, weight, target_val, current_val, unit, status, target_date, progress_pct, description)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', kpis)

# ---------------------------------------------------------------------------
# Authentication & department-scoped authorization
# ---------------------------------------------------------------------------

def bootstrap_admin(cursor):
    """Create the first admin from env vars when no user exists yet."""
    cursor.execute('SELECT COUNT(*) AS cnt FROM users')
    if cursor.fetchone()['cnt'] > 0:
        return
    username = (os.environ.get('INITIAL_ADMIN_USERNAME') or '').strip()
    password = os.environ.get('INITIAL_ADMIN_PASSWORD') or ''
    if not username or not password:
        print('[auth] 등록된 사용자가 없습니다. INITIAL_ADMIN_USERNAME / INITIAL_ADMIN_PASSWORD 환경변수를 '
              '설정하거나 `flask --app app create-user` 명령으로 계정을 만들어주세요.')
        return
    cursor.execute('''
    INSERT INTO users (username, password_hash, display_name, role)
    VALUES (%s, %s, %s, 'admin')
    ON CONFLICT (username) DO NOTHING
    ''', (username, generate_password_hash(password), '시스템 관리자'))


PUBLIC_ENDPOINTS = {'login', 'static'}


@app.before_request
def load_current_user():
    g.user = None
    user_id = session.get('user_id')
    if user_id:
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT u.id, u.username, u.display_name, u.role, u.dept_id, d.name AS dept_name
            FROM users u
            LEFT JOIN departments d ON d.id = u.dept_id
            WHERE u.id = %s AND u.is_active
            ''', (user_id,))
            g.user = cursor.fetchone()
        finally:
            conn.close()
        if g.user is None:
            session.clear()

    if request.endpoint in PUBLIC_ENDPOINTS:
        return None

    is_api = request.path.startswith('/api/')
    if g.user is None:
        if is_api:
            return jsonify({'error': '로그인이 필요합니다.'}), 401
        return redirect(url_for('login', next=request.path))

    # CSRF defence for state-changing API calls: browsers will not attach this
    # custom header on a cross-site request without a CORS preflight, which
    # this app never grants.
    if is_api and request.method not in ('GET', 'HEAD', 'OPTIONS'):
        if request.headers.get('X-Requested-With') != 'fetch':
            return jsonify({'error': '잘못된 요청입니다.'}), 403
    return None


def is_admin():
    return g.user is not None and g.user['role'] == ROLE_ADMIN


def scoped_dept_id(requested):
    """Department filter the current user may apply.

    Admins get whatever they asked for (None = all departments). Managers are
    always pinned to their own department, whatever they requested.
    """
    if is_admin():
        return requested or None
    return g.user['dept_id']


def can_access_employee(cursor, emp_id):
    """Returns True/False for an existing employee, None if it does not exist."""
    cursor.execute('SELECT dept_id FROM employees WHERE id = %s', (emp_id,))
    row = cursor.fetchone()
    if row is None:
        return None
    return is_admin() or row['dept_id'] == g.user['dept_id']


def _safe_next(target):
    # Only allow same-site relative paths to avoid open redirects.
    if target and target.startswith('/') and not target.startswith('//'):
        return target
    return url_for('index')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if g.user is not None:
            return redirect(url_for('index'))
        return render_template('login.html', error=None, next=request.args.get('next', ''))

    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''
    next_url = request.form.get('next', '')

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id, password_hash, is_active FROM users WHERE username = %s', (username,))
        row = cursor.fetchone()
    finally:
        conn.close()

    if row is None or not row['is_active'] or not check_password_hash(row['password_hash'], password):
        return render_template('login.html', error='아이디 또는 비밀번호가 올바르지 않습니다.',
                               next=next_url, username=username), 401

    session.clear()
    session.permanent = True
    session['user_id'] = row['id']
    return redirect(_safe_next(next_url))


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/api/me')
def api_me():
    return jsonify({
        'username': g.user['username'],
        'display_name': g.user['display_name'],
        'role': g.user['role'],
        'dept_id': g.user['dept_id'],
        'dept_name': g.user['dept_name'],
    })


@app.cli.command('create-user')
@click.option('--username', prompt='아이디')
@click.option('--name', 'display_name', prompt='표시 이름 (예: 홍길동 센터장)')
@click.option('--role', type=click.Choice([ROLE_ADMIN, ROLE_MANAGER]), prompt='역할', default=ROLE_MANAGER)
@click.option('--dept-code', default='', help='manager 역할일 때 소속 부서 코드 (예: FTL)')
@click.password_option('--password', prompt='비밀번호')
def create_user_command(username, display_name, role, dept_code, password):
    """보직자/관리자 계정을 생성하거나 비밀번호를 재설정합니다."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        dept_id = None
        if role == ROLE_MANAGER:
            if not dept_code:
                cursor.execute('SELECT code, name FROM departments ORDER BY id')
                for d in cursor.fetchall():
                    click.echo(f"  {d['code']}: {d['name']}")
                dept_code = click.prompt('소속 부서 코드')
            cursor.execute('SELECT id FROM departments WHERE code = %s', (dept_code.strip().upper(),))
            dept = cursor.fetchone()
            if dept is None:
                raise click.ClickException(f'부서 코드 {dept_code} 를 찾을 수 없습니다.')
            dept_id = dept['id']
        if len(password) < 8:
            raise click.ClickException('비밀번호는 8자 이상이어야 합니다.')
        cursor.execute('''
        INSERT INTO users (username, password_hash, display_name, role, dept_id)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (username) DO UPDATE
        SET password_hash = EXCLUDED.password_hash, display_name = EXCLUDED.display_name,
            role = EXCLUDED.role, dept_id = EXCLUDED.dept_id, is_active = TRUE
        ''', (username.strip(), generate_password_hash(password), display_name.strip(), role, dept_id))
        conn.commit()
    finally:
        conn.close()
    click.echo(f'계정 {username} 저장 완료 ({role}).')


@app.cli.command('deactivate-user')
@click.argument('username')
def deactivate_user_command(username):
    """계정을 비활성화합니다 (즉시 로그아웃 처리)."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_active = FALSE WHERE username = %s', (username,))
        changed = cursor.rowcount
        conn.commit()
    finally:
        conn.close()
    click.echo(f'{username} 비활성화 완료.' if changed else f'{username} 계정을 찾을 수 없습니다.')


@app.route('/')
def index():
    conn = get_db()
    try:
        cursor = conn.cursor()
        if is_admin():
            cursor.execute('SELECT id, name FROM departments ORDER BY id')
        else:
            cursor.execute('SELECT id, name FROM departments WHERE id = %s', (g.user['dept_id'],))
        departments = cursor.fetchall()
    finally:
        conn.close()
    return render_template('index.html', user=g.user, departments=departments, is_admin=is_admin())

@app.route('/api/dashboard/summary')
def dashboard_summary():
    dept_id = scoped_dept_id(request.args.get('dept_id', type=int))
    conn = get_db()
    cursor = conn.cursor()

    query = EMP_SCORE_CTE + '''
    SELECT e.id, e.name, e.dept_id, d.name as dept_name, e.position, e.eval_grade, e.eval_score,
           es.weighted_pct as avg_kpi_pct, es.kpi_count as kpi_count
    FROM employees e
    JOIN departments d ON e.dept_id = d.id
    JOIN emp_scores es ON es.emp_id = e.id
    '''
    params = []
    if dept_id:
        query += ' WHERE e.dept_id = %s'
        params.append(dept_id)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    total_employees = len(rows)
    if total_employees == 0:
        conn.close()
        return jsonify({
            'total_employees': 0, 'avg_achievement': 0,
            'top_performers': 0, 'risk_employees': 0,
            'dept_stats': [], 'quarterly_trend': [],
            'category_dist': [], 'grade_dist': []
        })

    sum_achievement = sum(row['avg_kpi_pct'] or 0 for row in rows)
    avg_achievement = round(sum_achievement / total_employees, 1)

    top_performers = sum(1 for row in rows if row['eval_grade'] in ['S', 'A'])
    risk_employees = sum(1 for row in rows if (row['avg_kpi_pct'] or 0) < 70 or row['eval_grade'] in ['C', 'D'])

    # Department level stats (average of each employee's weighted score)
    cursor.execute(EMP_SCORE_CTE + '''
    SELECT d.id, d.name, AVG(es.weighted_pct) as avg_pct, COUNT(DISTINCT e.id) as emp_cnt
    FROM departments d
    JOIN employees e ON d.id = e.dept_id
    JOIN emp_scores es ON es.emp_id = e.id
    ''' + ('' if is_admin() else ' WHERE d.id = %s') + '''
    GROUP BY d.id
    ORDER BY d.id
    ''', [] if is_admin() else [g.user['dept_id']])
    dept_rows = cursor.fetchall()
    dept_stats = [{'id': r['id'], 'name': r['name'], 'avg_pct': round(r['avg_pct'] or 0, 1), 'emp_cnt': r['emp_cnt']} for r in dept_rows]

    # Category Breakdown
    cat_query = '''
    SELECT k.category, AVG(k.progress_pct)::float as avg_pct, COUNT(k.id) as count
    FROM kpis k
    JOIN employees e ON k.emp_id = e.id
    '''
    if dept_id:
        cat_query += ' WHERE e.dept_id = %s'
        cursor.execute(cat_query + ' GROUP BY k.category', [dept_id])
    else:
        cursor.execute(cat_query + ' GROUP BY k.category')
    cat_rows = cursor.fetchall()
    category_dist = [{'category': r['category'], 'avg_pct': round(r['avg_pct'] or 0, 1), 'count': r['count']} for r in cat_rows]

    # Grade Distribution
    grade_counts = {'S': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0}
    for r in rows:
        grade = r['eval_grade']
        if grade in grade_counts:
            grade_counts[grade] += 1
    grade_dist = [{'grade': gr, 'count': cnt} for gr, cnt in grade_counts.items()]

    # Quarterly Trend (Mock baseline with actual current avg for Q2/Q3)
    quarterly_trend = [
        {'quarter': '1분기 (Q1)', 'achievement': round(avg_achievement * 0.72, 1)},
        {'quarter': '2분기 (Q2)', 'achievement': round(avg_achievement * 0.88, 1)},
        {'quarter': '3분기 (현재 Q3)', 'achievement': avg_achievement},
        {'quarter': '4분기 (목표 Q4)', 'achievement': min(100.0, round(avg_achievement * 1.15, 1))}
    ]

    conn.close()
    return jsonify({
        'total_employees': total_employees,
        'avg_achievement': avg_achievement,
        'top_performers': top_performers,
        'risk_employees': risk_employees,
        'dept_stats': dept_stats,
        'quarterly_trend': quarterly_trend,
        'category_dist': category_dist,
        'grade_dist': grade_dist
    })

@app.route('/api/employees')
def get_employees():
    dept_id = scoped_dept_id(request.args.get('dept_id', type=int))
    search = request.args.get('search', '', type=str).strip()
    status_filter = request.args.get('status', '', type=str)
    grade_filter = request.args.get('grade', '', type=str)

    conn = get_db()
    cursor = conn.cursor()

    query = EMP_SCORE_CTE + '''
    SELECT e.*, d.name as dept_name,
           es.weighted_pct as avg_kpi_pct,
           es.kpi_count as kpi_count,
           es.delayed_kpi_cnt as delayed_kpi_cnt
    FROM employees e
    JOIN departments d ON e.dept_id = d.id
    JOIN emp_scores es ON es.emp_id = e.id
    WHERE 1=1
    '''
    params = []

    if dept_id:
        query += ' AND e.dept_id = %s'
        params.append(dept_id)

    if search:
        query += ' AND (e.name LIKE %s OR e.emp_no LIKE %s OR e.research_area LIKE %s OR e.position LIKE %s)'
        pattern = f'%{search}%'
        params.extend([pattern, pattern, pattern, pattern])

    if grade_filter:
        if grade_filter == 'CD':
            query += ' AND e.eval_grade IN (%s, %s)'
            params.extend(['C', 'D'])
        else:
            query += ' AND e.eval_grade = %s'
            params.append(grade_filter)

    query += ' ORDER BY e.eval_score DESC'

    cursor.execute(query, params)
    rows = cursor.fetchall()

    result = []
    for r in rows:
        avg_pct = round(r['avg_kpi_pct'] or 0, 1)

        # Status badge determination
        if r['delayed_kpi_cnt'] > 0 or avg_pct < 65:
            computed_status = '관심필요'
        elif avg_pct >= 90:
            computed_status = '달성우수'
        else:
            computed_status = '정상진행'

        if status_filter and status_filter != computed_status:
            continue

        result.append({
            'id': r['id'],
            'emp_no': r['emp_no'],
            'name': r['name'],
            'dept_id': r['dept_id'],
            'dept_name': r['dept_name'],
            'position': r['position'],
            'email': r['email'],
            'research_area': r['research_area'],
            'project_participation_pct': r['project_participation_pct'],
            'eval_grade': r['eval_grade'],
            'eval_score': r['eval_score'],
            'eval_feedback': r['eval_feedback'],
            'eval_date': r['eval_date'],
            'avg_kpi_pct': avg_pct,
            'kpi_count': r['kpi_count'],
            'status': computed_status
        })

    conn.close()
    return jsonify(result)

@app.route('/api/employees/<int:emp_id>')
def get_employee_detail(emp_id):
    conn = get_db()
    cursor = conn.cursor()

    if not can_access_employee(cursor, emp_id):
        conn.close()
        return jsonify({'error': 'Employee not found'}), 404

    cursor.execute('''
    SELECT e.*, d.name as dept_name
    FROM employees e
    JOIN departments d ON e.dept_id = d.id
    WHERE e.id = %s
    ''', (emp_id,))
    emp_row = cursor.fetchone()

    if not emp_row:
        conn.close()
        return jsonify({'error': 'Employee not found'}), 404

    cursor.execute('''
    SELECT * FROM kpis WHERE emp_id = %s ORDER BY id ASC
    ''', (emp_id,))
    kpi_rows = cursor.fetchall()

    employee = dict(emp_row)
    kpis = [dict(k) for k in kpi_rows]

    # Calculate overall weight-adjusted score
    total_weight = sum(k['weight'] for k in kpis) or 1
    weighted_score = sum((k['progress_pct'] * k['weight']) for k in kpis) / total_weight
    employee['weighted_score'] = round(weighted_score, 1)

    conn.close()
    return jsonify({'employee': employee, 'kpis': kpis})

@app.route('/api/employees/<int:emp_id>/kpis', methods=['POST'])
def add_kpi(emp_id):
    data = request.json or {}

    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'title은 필수 항목입니다.'}), 400

    target_val = parse_float(data.get('target_val'), 1.0)
    current_val = parse_float(data.get('current_val'), 0.0)
    weight = parse_int(data.get('weight'), 20)
    if target_val is None or current_val is None or weight is None:
        return jsonify({'error': '목표치/현재실적/가중치는 숫자여야 합니다.'}), 400

    conn = get_db()
    cursor = conn.cursor()

    if not can_access_employee(cursor, emp_id):
        conn.close()
        return jsonify({'error': 'Employee not found'}), 404

    if target_val > 0:
        progress_pct = min(200, int((current_val / target_val) * 100))
    else:
        progress_pct = 0

    status = data.get('status', '정상진행')
    if progress_pct >= 100:
        status = '완료'

    cursor.execute('''
    INSERT INTO kpis (emp_id, title, category, weight, target_val, current_val, unit, status, target_date, progress_pct, description)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    ''', (
        emp_id,
        title,
        data.get('category', '논문/R&D'),
        weight,
        target_val,
        current_val,
        data.get('unit', '건'),
        status,
        data.get('target_date', '2026-12-31'),
        progress_pct,
        data.get('description', '')
    ))

    new_id = cursor.fetchone()['id']
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'id': new_id})

@app.route('/api/kpis/<int:kpi_id>', methods=['PUT'])
def update_kpi(kpi_id):
    data = request.json or {}
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM kpis WHERE id = %s', (kpi_id,))
    existing = cursor.fetchone()
    if not existing or not can_access_employee(cursor, existing['emp_id']):
        conn.close()
        return jsonify({'error': 'KPI not found'}), 404

    target_val = parse_float(data.get('target_val'), existing['target_val'])
    current_val = parse_float(data.get('current_val'), existing['current_val'])
    weight = parse_int(data.get('weight'), existing['weight'])
    if target_val is None or current_val is None or weight is None:
        conn.close()
        return jsonify({'error': '목표치/현재실적/가중치는 숫자여야 합니다.'}), 400

    if target_val > 0:
        progress_pct = min(200, int((current_val / target_val) * 100))
    else:
        progress_pct = 0

    status = data.get('status', existing['status'] or '정상진행')
    if progress_pct >= 100:
        status = '완료'

    cursor.execute('''
    UPDATE kpis
    SET title = %s, category = %s, weight = %s, target_val = %s, current_val = %s, unit = %s, status = %s, target_date = %s, progress_pct = %s, description = %s
    WHERE id = %s
    ''', (
        data.get('title', existing['title']),
        data.get('category', existing['category']),
        weight,
        target_val,
        current_val,
        data.get('unit', existing['unit']),
        status,
        data.get('target_date', existing['target_date']),
        progress_pct,
        data.get('description', existing['description']),
        kpi_id
    ))

    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/kpis/<int:kpi_id>', methods=['DELETE'])
def delete_kpi(kpi_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT emp_id FROM kpis WHERE id = %s', (kpi_id,))
    existing = cursor.fetchone()
    if not existing or not can_access_employee(cursor, existing['emp_id']):
        conn.close()
        return jsonify({'error': 'KPI not found'}), 404

    cursor.execute('DELETE FROM kpis WHERE id = %s', (kpi_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/employees/<int:emp_id>/eval', methods=['POST'])
def save_evaluation(emp_id):
    data = request.json or {}
    conn = get_db()
    cursor = conn.cursor()

    if not can_access_employee(cursor, emp_id):
        conn.close()
        return jsonify({'error': 'Employee not found'}), 404

    eval_score = parse_int(data.get('eval_score'), 80)
    if eval_score is None or not (0 <= eval_score <= 100):
        conn.close()
        return jsonify({'error': '평가 점수는 0~100 사이의 숫자여야 합니다.'}), 400

    eval_grade = data.get('eval_grade', 'B')
    if eval_grade not in ('S', 'A', 'B', 'C', 'D'):
        conn.close()
        return jsonify({'error': '유효하지 않은 평가 등급입니다.'}), 400

    eval_feedback = data.get('eval_feedback', '')
    eval_date = data.get('eval_date') or date.today().isoformat()

    cursor.execute('''
    UPDATE employees
    SET eval_score = %s, eval_grade = %s, eval_feedback = %s, eval_date = %s
    WHERE id = %s
    ''', (eval_score, eval_grade, eval_feedback, eval_date, emp_id))

    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/ai/analyze', methods=['POST'])
def ai_analyze():
    data = request.json or {}
    dept_id = scoped_dept_id(parse_int(data.get('dept_id')))

    conn = get_db()
    cursor = conn.cursor()

    query = '''
    SELECT e.name, e.position, d.name as dept_name, e.eval_grade, e.eval_score, e.research_area,
           AVG(k.progress_pct)::float as avg_pct,
           SUM(CASE WHEN k.status = '지연' THEN 1 ELSE 0 END) as delayed_cnt
    FROM employees e
    JOIN departments d ON e.dept_id = d.id
    LEFT JOIN kpis k ON e.id = k.emp_id
    '''
    group_by = ' GROUP BY e.id, e.name, e.position, d.name, e.eval_grade, e.eval_score, e.research_area'
    if dept_id:
        query += ' WHERE e.dept_id = %s'
        cursor.execute(query + group_by, [dept_id])
    else:
        cursor.execute(query + group_by)

    rows = cursor.fetchall()
    conn.close()

    total = len(rows)
    if total == 0:
        return jsonify({'analysis': '분석할 직원 데이터가 없습니다.'})

    top_staff = [r for r in rows if r['eval_grade'] in ['S', 'A']]
    risk_staff = [r for r in rows if (r['avg_pct'] or 0) < 70 or r['delayed_cnt'] > 0]

    dept_label = "전체 부서" if not dept_id else rows[0]['dept_name']

    report = f"### 🤖 KRRI 보직자 AI 성과 분석 및 리포트 ({dept_label})\n\n"
    report += f"**1. 현황 종합 요약**\n"
    report += f"- 관할 총 인원: **{total}명** | 우수 성과자(S/A): **{len(top_staff)}명** | 관심/지연 필요 인원: **{len(risk_staff)}명**\n\n"

    report += f"**2. 우수 성과 리더십 요인**\n"
    if top_staff:
        names = ", ".join([f"{r['name']} {r['position']}" for r in top_staff[:3]])
        report += f"- 주요 우수자: **{names}** 등\n"
        report += f"- 특징: 국책 대형과제 수주 및 SCI급 대표 연구 성과 창출 우수. 원내 기술 상용화 기여도가 매우 높음.\n\n"
    else:
        report += f"- 현재 S/A 등급 기준을 달성한 인원이 적습니다. 3분기 목표 조정을 권장합니다.\n\n"

    report += f"**3. 주의 및 지연 항목 위험 분석 (Risk Management)**\n"
    if risk_staff:
        for r in risk_staff:
            report += f"- ⚠️ **{r['name']} {r['position']}** ({r['dept_name']}): 현재 평균 KPI 달성률 {round(r['avg_pct'] or 0, 1)}%, 지연 항목 {r['delayed_cnt']}건 발생. 원인: 연구 데이터 계측 지연 및 외부 시험 일정 수렴 차질.\n"
        report += f"\n👉 **보직자 코칭 조언**: 1:1 면담을 통해 연구 기자재 보완 지원 및 학술 논문 명세서 수정을 지원할 필요가 있습니다.\n\n"
    else:
        report += f"- 모든 직원이 계획 대비 순조롭게 성과 달성 중입니다.\n\n"

    report += f"**4. 보직자 조치 권고사항 (Executive Next Steps)**\n"
    report += f"1) 하반기 기술이전 협상 진행 건에 대한 원내 지식재산팀 연계 지원\n"
    report += f"2) C/D 등급 우려 직원에 대한 KPI 가중치 재조정 및 중간 점검 면담 실시\n"
    report += f"3) 2026 연구원 포상 추천 후보자 서류 사전 검토"

    return jsonify({'analysis': report, 'risk_count': len(risk_staff), 'top_count': len(top_staff)})

@app.route('/api/export/csv')
def export_csv():
    dept_id = scoped_dept_id(request.args.get('dept_id', type=int))
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(EMP_SCORE_CTE + '''
    SELECT e.emp_no, e.name, d.name as dept_name, e.position, e.eval_grade, e.eval_score,
           es.weighted_pct as avg_kpi_pct, e.research_area
    FROM employees e
    JOIN departments d ON e.dept_id = d.id
    JOIN emp_scores es ON es.emp_id = e.id
    WHERE (%s::int IS NULL OR e.dept_id = %s::int)
    ORDER BY e.eval_score DESC
    ''', [dept_id, dept_id])
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    output.write('﻿') # UTF-8 BOM for Excel
    writer = csv.writer(output)
    writer.writerow(['사번', '성명', '소속부서', '직급', '평가등급', '평가점수', 'KPI평균달성률(%)', '주요연구분야'])

    for r in rows:
        writer.writerow([
            r['emp_no'],
            r['name'],
            r['dept_name'],
            r['position'],
            r['eval_grade'],
            r['eval_score'],
            round(r['avg_kpi_pct'] or 0, 1),
            r['research_area']
        ])

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=KRRI_KPI_Employee_Report.csv'
    return response

# Runs on every cold start (both local `python app.py` and Vercel's serverless
# import of this module), not just under __main__, since Vercel never executes
# the __main__ block below.
init_db()

if __name__ == '__main__':
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    print(f"Starting KRRI Executive KPI Dashboard server on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug_mode)
