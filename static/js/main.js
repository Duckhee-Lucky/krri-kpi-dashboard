/* ========================================================
   KRRI Executive Employee KPI Management Dashboard - JS
   ======================================================== */

let deptChartInstance = null;
let trendChartInstance = null;
let categoryChartInstance = null;
let gradeChartInstance = null;

let currentEmpId = null;
let currentFilterStatus = '';
let currentFilterGrade = '';
let searchTimeout = null;

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadDashboardData();
    loadEmployeeTable();
});

// Theme Management
function initTheme() {
    const savedTheme = localStorage.getItem('krri_theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
    }
}

function toggleTheme() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    localStorage.setItem('krri_theme', isDark ? 'dark' : 'light');
    showToast(isDark ? '다크 모드가 적용되었습니다.' : '라이트 모드가 적용되었습니다.');

    // Re-render charts with updated theme colors if needed
    loadDashboardData();
}

// Toast Notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
        <span style="color: var(--krri-cyan)">ℹ️</span>
        <span>${message}</span>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Escape user-supplied text before inserting via innerHTML
function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Debounce Search
function debounceSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        loadEmployeeTable();
    }, 300);
}

function resetFilters() {
    document.getElementById('deptSelect').value = '';
    document.getElementById('searchInput').value = '';
    currentFilterStatus = '';
    currentFilterGrade = '';

    document.querySelectorAll('.pill-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.pill-btn')[0].classList.add('active');

    loadDashboardData();
    loadEmployeeTable();
    showToast('모든 검색 필터가 초기화되었습니다.');
}

// Load Dashboard Summary Stats and Charts
async function loadDashboardData() {
    const deptId = document.getElementById('deptSelect').value;
    try {
        const res = await fetch(`/api/dashboard/summary?dept_id=${deptId}`);
        const data = await res.json();

        // Update Cards
        document.getElementById('cardTotalEmp').innerText = `${data.total_employees}명`;
        document.getElementById('cardAvgPct').innerText = `${data.avg_achievement}%`;
        document.getElementById('cardTopCount').innerText = `${data.top_performers}명`;
        document.getElementById('cardRiskCount').innerText = `${data.risk_employees}명`;

        // Render Charts
        renderDeptChart(data.dept_stats);
        renderTrendChart(data.quarterly_trend);
        renderCategoryChart(data.category_dist);
        renderGradeChart(data.grade_dist);

        // Also reload table to reflect dept filter
        loadEmployeeTable();
    } catch (err) {
        console.error('Error loading dashboard summary:', err);
    }
}

// Chart 1: Department Comparison
function renderDeptChart(deptStats) {
    const ctx = document.getElementById('deptChart').getContext('2d');
    const isDark = document.body.classList.contains('dark-mode');
    const textColor = isDark ? '#94a3b8' : '#64748b';

    const labels = deptStats.map(d => d.name);
    const dataValues = deptStats.map(d => d.avg_pct);

    if (deptChartInstance) deptChartInstance.destroy();

    deptChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '평균 달성률 (%)',
                data: dataValues,
                backgroundColor: 'rgba(0, 163, 224, 0.75)',
                borderColor: '#00a3e0',
                borderWidth: 1.5,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { color: textColor }
                },
                x: { ticks: { color: textColor, font: { size: 10 } } }
            }
        }
    });
}

// Chart 2: Quarterly Progress Trend
function renderTrendChart(trendData) {
    const ctx = document.getElementById('trendChart').getContext('2d');
    const isDark = document.body.classList.contains('dark-mode');
    const textColor = isDark ? '#94a3b8' : '#64748b';

    const labels = trendData.map(t => t.quarter);
    const dataValues = trendData.map(t => t.achievement);

    if (trendChartInstance) trendChartInstance.destroy();

    trendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '진행 추이 (%)',
                data: dataValues,
                fill: true,
                backgroundColor: 'rgba(56, 189, 248, 0.15)',
                borderColor: '#38bdf8',
                borderWidth: 3,
                tension: 0.35,
                pointBackgroundColor: '#0284c7',
                pointRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, max: 100, ticks: { color: textColor } },
                x: { ticks: { color: textColor } }
            }
        }
    });
}

// Chart 3: KPI Category Radar Chart
function renderCategoryChart(catData) {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    const isDark = document.body.classList.contains('dark-mode');
    const textColor = isDark ? '#94a3b8' : '#64748b';

    const labels = catData.map(c => c.category);
    const dataValues = catData.map(c => c.avg_pct);

    if (categoryChartInstance) categoryChartInstance.destroy();

    categoryChartInstance = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: '영역별 달성도 (%)',
                data: dataValues,
                backgroundColor: 'rgba(139, 92, 246, 0.25)',
                borderColor: '#8b5cf6',
                borderWidth: 2,
                pointBackgroundColor: '#8b5cf6'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                r: {
                    min: 0,
                    max: 100,
                    ticks: { display: false },
                    pointLabels: { color: textColor, font: { size: 11, weight: 'bold' } }
                }
            }
        }
    });
}

// Chart 4: Grade Distribution Donut
function renderGradeChart(gradeData) {
    const ctx = document.getElementById('gradeChart').getContext('2d');
    const isDark = document.body.classList.contains('dark-mode');
    const textColor = isDark ? '#94a3b8' : '#64748b';

    const labels = gradeData.map(g => `${g.grade}등급`);
    const dataValues = gradeData.map(g => g.count);

    if (gradeChartInstance) gradeChartInstance.destroy();

    gradeChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: dataValues,
                backgroundColor: ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444'],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: textColor, font: { size: 11 } }
                }
            },
            cutout: '65%'
        }
    });
}

// Table Data Loading
async function loadEmployeeTable() {
    const deptId = document.getElementById('deptSelect').value;
    const search = document.getElementById('searchInput').value;

    let url = `/api/employees?dept_id=${deptId}&search=${encodeURIComponent(search)}`;
    if (currentFilterStatus) url += `&status=${encodeURIComponent(currentFilterStatus)}`;
    if (currentFilterGrade) url += `&grade=${encodeURIComponent(currentFilterGrade)}`;

    try {
        const res = await fetch(url);
        const employees = await res.json();

        const tbody = document.getElementById('employeeTableBody');
        tbody.innerHTML = '';

        if (employees.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: 2rem; color: var(--text-muted);">
                        검색 조건에 해당되는 직원 데이터가 없습니다.
                    </td>
                </tr>
            `;
            return;
        }

        employees.forEach(emp => {
            const tr = document.createElement('tr');

            // Grade Badge Class
            let gradeClass = `badge-${emp.eval_grade.toLowerCase()}`;

            // Status Badge Class
            let statusClass = 'badge-status-normal';
            if (emp.status === '달성우수') statusClass = 'badge-status-excel';
            if (emp.status === '관심필요') statusClass = 'badge-status-danger';

            // Progress bar color fill
            let fillClass = 'fill-info';
            if (emp.avg_kpi_pct >= 90) fillClass = 'fill-success';
            if (emp.avg_kpi_pct < 70) fillClass = 'fill-danger';

            tr.innerHTML = `
                <td style="font-family: monospace; font-weight: 600;">${escapeHtml(emp.emp_no)}</td>
                <td>
                    <div style="font-weight: 700;">${escapeHtml(emp.name)}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(emp.email)}</div>
                </td>
                <td>${escapeHtml(emp.dept_name)}</td>
                <td><span class="badge" style="background: var(--bg-main); color: var(--text-main); border: 1px solid var(--border-color);">${escapeHtml(emp.position)}</span></td>
                <td style="max-width: 220px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" title="${escapeHtml(emp.research_area)}">
                    ${escapeHtml(emp.research_area)}
                </td>
                <td class="progress-cell">
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill ${fillClass}" style="width: ${Math.min(100, emp.avg_kpi_pct)}%;"></div>
                    </div>
                    <span class="progress-text">${emp.avg_kpi_pct}% (${emp.kpi_count}개 항목)</span>
                </td>
                <td>
                    <span class="badge ${gradeClass}">${emp.eval_grade}등급</span>
                    <span style="font-size: 0.78rem; font-weight: 700; color: var(--text-muted); margin-left: 0.25rem;">(${emp.eval_score}점)</span>
                </td>
                <td><span class="badge ${statusClass}">${emp.status}</span></td>
                <td>
                    <button class="btn btn-secondary" style="padding: 0.3rem 0.6rem; font-size: 0.78rem;" onclick="openEmployeeModal(${emp.id})">
                        상세/평가
                    </button>
                </td>
            `;

            tbody.appendChild(tr);
        });

    } catch (err) {
        console.error('Error loading employee table:', err);
    }
}

// Table Filter Buttons
function filterTableStatus(status, evt) {
    currentFilterStatus = status;
    currentFilterGrade = '';
    updatePillButtons(evt ? evt.target : null);
    loadEmployeeTable();
}

function filterTableGrade(grade, evt) {
    currentFilterGrade = grade;
    currentFilterStatus = '';
    updatePillButtons(evt ? evt.target : null);
    loadEmployeeTable();
}

function updatePillButtons(clickedBtn) {
    document.querySelectorAll('.pill-btn').forEach(btn => btn.classList.remove('active'));
    if (clickedBtn) clickedBtn.classList.add('active');
}

// Employee Detail Modal
async function openEmployeeModal(empId) {
    currentEmpId = empId;
    try {
        const res = await fetch(`/api/employees/${empId}`);
        const data = await res.json();
        const emp = data.employee;
        const kpis = data.kpis;

        // Profile banner (innerText is used here, so no HTML-escaping is needed)
        document.getElementById('empModalAvatar').innerText = emp.name[0];
        document.getElementById('empModalNamePos').innerText = `${emp.name} ${emp.position}`;
        document.getElementById('empModalDept').innerText = emp.dept_name;
        document.getElementById('empModalNoEmail').innerText = `${emp.emp_no} | ${emp.email}`;
        document.getElementById('empModalResearch').innerText = emp.research_area;

        // Render KPI Table in Modal
        const kpiBody = document.getElementById('kpiListBody');
        kpiBody.innerHTML = '';

        if (kpis.length === 0) {
            kpiBody.innerHTML = `<tr><td colspan="8" style="text-align:center;">등록된 KPI가 없습니다.</td></tr>`;
        } else {
            kpis.forEach(k => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="font-weight: 600;">${escapeHtml(k.title)}</td>
                    <td><span class="badge" style="background: var(--bg-main); color: var(--text-main); border:1px solid var(--border-color);">${escapeHtml(k.category)}</span></td>
                    <td style="font-weight: 700;">${k.weight}%</td>
                    <td>${k.target_val} ${escapeHtml(k.unit)}</td>
                    <td>
                        <input type="number" step="0.1" value="${k.current_val}" style="width: 70px; padding: 0.2rem;" class="text-input" onchange="updateKpiCurrent(${k.id}, this.value, ${k.target_val})"> ${escapeHtml(k.unit)}
                    </td>
                    <td style="font-weight: 700; color: ${k.progress_pct >= 100 ? 'var(--status-success)' : 'var(--krri-navy)'}">
                        ${k.progress_pct}%
                    </td>
                    <td>
                        <span class="badge ${k.status === '완료' ? 'badge-status-excel' : (k.status === '지연' ? 'badge-status-danger' : 'badge-status-normal')}">
                            ${k.status}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-secondary" style="padding: 0.2rem 0.5rem; font-size: 0.72rem; color: var(--status-danger);" onclick="deleteKpiItem(${k.id})">삭제</button>
                    </td>
                `;
                kpiBody.appendChild(tr);
            });
        }

        // Pre-fill Evaluation Form
        document.getElementById('evalEmpId').value = emp.id;
        document.getElementById('evalScoreInput').value = emp.eval_score;
        document.getElementById('evalGradeSelect').value = emp.eval_grade;
        document.getElementById('evalFeedbackText').value = emp.eval_feedback || '';

        openModal('empDetailModal');

    } catch (err) {
        console.error('Error loading employee detail:', err);
    }
}

// Modal Helpers
function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// Save Evaluation & Feedback
async function saveEvaluation(event) {
    event.preventDefault();
    const empId = document.getElementById('evalEmpId').value;
    const score = document.getElementById('evalScoreInput').value;
    const grade = document.getElementById('evalGradeSelect').value;
    const feedback = document.getElementById('evalFeedbackText').value;

    try {
        const res = await fetch(`/api/employees/${empId}/eval`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                eval_score: score,
                eval_grade: grade,
                eval_feedback: feedback
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast('보직자 성과 평가 및 면담 피드백이 저장되었습니다.');
            closeModal('empDetailModal');
            loadDashboardData();
            loadEmployeeTable();
        } else {
            showToast(data.error || '평가 저장에 실패했습니다.');
        }
    } catch (err) {
        console.error('Error saving evaluation:', err);
        showToast('평가 저장 중 오류가 발생했습니다.');
    }
}

// Add KPI Modal
function openAddKpiModal() {
    if (!currentEmpId) return;
    openModal('addKpiModal');
}

async function saveNewKpi(event) {
    event.preventDefault();
    if (!currentEmpId) return;

    const payload = {
        title: document.getElementById('kpiTitle').value,
        category: document.getElementById('kpiCategory').value,
        weight: document.getElementById('kpiWeight').value,
        target_val: document.getElementById('kpiTarget').value,
        current_val: document.getElementById('kpiCurrent').value,
        unit: document.getElementById('kpiUnit').value,
        target_date: document.getElementById('kpiTargetDate').value,
        description: document.getElementById('kpiDesc').value
    };

    try {
        const res = await fetch(`/api/employees/${currentEmpId}/kpis`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast('신규 KPI 항목이 성공적으로 등록되었습니다.');
            closeModal('addKpiModal');
            openEmployeeModal(currentEmpId);
            loadDashboardData();
        } else {
            showToast(data.error || 'KPI 등록에 실패했습니다.');
        }
    } catch (err) {
        console.error('Error adding KPI:', err);
        showToast('KPI 등록 중 오류가 발생했습니다.');
    }
}

// Update KPI current value inline
async function updateKpiCurrent(kpiId, newVal, targetVal) {
    try {
        await fetch(`/api/kpis/${kpiId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_val: newVal,
                target_val: targetVal
            })
        });
        showToast('KPI 실적이 업데이트 되었습니다.');
        if (currentEmpId) openEmployeeModal(currentEmpId);
        loadDashboardData();
    } catch (err) {
        console.error('Error updating KPI:', err);
    }
}

// Delete KPI item
async function deleteKpiItem(kpiId) {
    if (!confirm('이 KPI 항목을 삭제하시겠습니까?')) return;
    try {
        await fetch(`/api/kpis/${kpiId}`, { method: 'DELETE' });
        showToast('KPI 항목이 삭제되었습니다.');
        if (currentEmpId) openEmployeeModal(currentEmpId);
        loadDashboardData();
    } catch (err) {
        console.error('Error deleting KPI:', err);
    }
}

// AI Report Modal
async function openAIReportModal() {
    openModal('aiReportModal');
    const reportBox = document.getElementById('aiReportText');
    reportBox.innerText = '🤖 KRRI 연구원 성과 데이터 실시간 다차원 분석 중...';

    const deptId = document.getElementById('deptSelect').value;

    try {
        const res = await fetch('/api/ai/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dept_id: deptId })
        });
        const data = await res.json();
        reportBox.innerHTML = formatMarkdownText(data.analysis);
    } catch (err) {
        reportBox.innerText = 'AI 분석 리포트 생성 실패';
    }
}

function formatMarkdownText(text) {
    return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
               .replace(/### (.*?)\n/g, '<h3 style="margin-top:0.5rem; margin-bottom:0.3rem; color:var(--krri-navy); font-size:1.1rem;">$1</h3>')
               .replace(/\n/g, '<br>');
}

// Export CSV
function exportCSV() {
    window.location.href = '/api/export/csv';
}
