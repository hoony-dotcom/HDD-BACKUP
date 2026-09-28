import streamlit as st
import pandas as pd
import glob
import os
import re
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# --- [그래프 한글 깨짐 방지 핵심 설정] ---
plt.rcParams['axes.unicode_minus'] = False # 마이너스 기호 깨짐 방지

# 사용 가능한 한글 폰트 탐색 및 강제 적용
font_list = [f.name for f in fm.fontManager.ttflist]
target_fonts = ['NanumGothic', 'Nanum Gothic', 'Malgun Gothic', 'AppleGothic', 'DejaVu Sans']

applied_font = 'DejaVu Sans'
for tf in target_fonts:
    if tf in font_list:
        applied_font = tf
        break

plt.rcParams['font.family'] = applied_font

# 페이지 설정 (사이드바 기본 열림)
st.set_page_config(
    page_title="의료기기 백업 현황 대시보드",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 1. 항상 라이트 모드로 보이도록 Streamlit 테마 설정 주입 (CSS 주입)
st.markdown(
    """
    <style>
    .stApp {
        background-color: #FFFFFF;
        color: #000000;
    }
    sidebar .stApp {
        background-color: #F8F9FA;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 2. 사이드바 구성 (제작 및 문의 이메일 링크 최상단 배치 및 1번 링크 수정 반영)
with st.sidebar:
    st.markdown("### 📧 제작 및 문의")
    st.markdown(
        """
        <div style="font-size: 1.15em; font-weight: bold; margin-bottom: 10px;">
        <a href="mailto:dhkoh@inhauh.com" target="_blank" style="text-decoration: none; color: #1E88E5;">
        ✉️ dhkoh@inhauh.com
        </a>
        </div>
        <div style="font-size: 0.9em; color: #555555;">
        인하대병원 의용공학팀
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("---")
    st.markdown("#### 🛠️ 개발 앱 목록")
    st.markdown("""
    1. [의료장비 투자집행 계획 실적](https://buly.kr/DEbvdwF)
    2. [인하대병원 의료장비 보유 현황](https://buly.kr/7mERs3u)
    3. [건강보험심사평가원 의료장비 상세현황 조회](http://buly.kr/uWvRbg)
    4. [인하대병원 의료장비 조회 시스템](https://buly.kr/6BzfJgY)
    5. **[현재] [의료기기 백업 현황 대시보드](https://buly.kr/2Jr1qXA)**
    """)

# 3. 최신 엑셀 파일 자동 탐색 및 기준일 파싱 함수
@st.cache_data(ttl=60)
def load_latest_data():
    files = glob.glob('의료기기 현황조회_*.xlsx')
    if not files:
        return None, None, None, None
    
    latest_file = sorted(files)[-1]
    filename = os.path.basename(latest_file)
    
    try:
        date_str = filename.split('_')[1][:8]
        기준일 = datetime.strptime(date_str, '%Y%m%d').strftime('%Y년 %m월 %d일')
    except Exception:
        mtime = os.path.getmtime(latest_file)
        기준일 = datetime.fromtimestamp(mtime).strftime('%Y년 %m월 %d일')
        
    df = pd.read_excel(latest_file)
    df.columns = df.columns.str.replace('\n', ' ')
    
    return df, filename, 기준일, latest_file

# 데이터 로드
df, filename, 기준일, latest_file = load_latest_data()

if df is None:
    st.error("참고할 '의료기기 현황조회_*.xlsx' 파일이 존재하지 않습니다. 파일을 업로드해 주세요.")
    st.stop()

# 4. 전처리: 사용부서가 '88'인 항목 제외 및 취득일자가 공란인 항목 제외
df_filtered = df[df['사용 부서'].astype(str).str.strip() != '88'].copy()
if '취득일자' in df_filtered.columns:
    df_filtered = df_filtered[df_filtered['취득일자'].notna()].copy()

# 5. 대시보드 지표 계산
total_equipment_count = len(df_filtered) # 전체 장비수량(대)

# Backup 전체 대상
backup_all_df = df_filtered[df_filtered['관리대상'].astype(str).str.contains('backup', na=False, case=False)].copy()
backup_target_count = len(backup_all_df) # backup 대상장비수량(대)

# 분류 함수
def classify_backup(val):
    val_str = str(val)
    if re.search(r'\+', val_str):
        return 'Backup 완료 (+)'
    if '보증' in val_str:
        return 'Backup (보증)'
    if '임대' in val_str:
        return 'Backup (임대)'
    if re.search(r'pm', val_str, re.IGNORECASE):
        return 'Backup (PM)'
        
    match = re.search(r'(BACKUP\s*-\s*\([^)]+\))', val_str, re.IGNORECASE)
    if match:
        sub = match.group(1).upper()
        if sub not in ['BACKUP-(PM)', 'BACKUP-(보증)', 'BACKUP-(임대)']:
            return sub
            
    if re.search(r'BACKUP-', val_str, re.IGNORECASE):
        return 'BACKUP-'
        
    return '기타'

backup_all_df['세부유형'] = backup_all_df['관리대상'].apply(classify_backup)

# 개별 항목별 카운트 계산
base_completed_count = len(backup_all_df[backup_all_df['세부유형'] == 'Backup 완료 (+)'])
backup_pm_count = len(backup_all_df[backup_all_df['세부유형'] == 'Backup (PM)'])
backup_warranty_count = len(backup_all_df[backup_all_df['세부유형'] == 'Backup (보증)'])
backup_rental_count = len(backup_all_df[backup_all_df['세부유형'] == 'Backup (임대)'])

# Backup 완료 통합 합계 (완료 + PM + 보증 + 임대)
backup_completed_total_count = base_completed_count + backup_pm_count + backup_warranty_count + backup_rental_count

# 기타 괄호형 세부유형 집계
excluded_types = ['Backup 완료 (+)', 'BACKUP-', 'Backup (PM)', 'Backup (보증)', 'Backup (임대)', '기타']
specific_backup_counts = backup_all_df[~backup_all_df['세부유형'].isin(excluded_types)].groupby('세부유형').size()

# Backup 미완료 또는 불가
backup_minus_base_count = len(backup_all_df[backup_all_df['세부유형'] == 'BACKUP-'])
backup_minus_total_count = backup_minus_base_count + specific_backup_counts.sum()

# --- 화면 메인 UI 구성 ---
st.title("의료기기 백업 현황 대시보드")

# 참고 파일 및 기준일 안내 박스
st.info(f"📁 **참고 파일명:** `{filename}` &nbsp;&nbsp;|&nbsp;&nbsp; 📅 **기준일:** `{기준일}`")

# 전체 장비 및 대상 수량
top_col1, top_col2 = st.columns(2)
with top_col1:
    st.metric(label="전체 장비수량", value=f"{total_equipment_count:,} 대")
with top_col2:
    st.metric(label="Backup 대상장비수량", value=f"{backup_target_count:,} 대")

st.divider()

# 6. 2열 메인 배치 (Backup 완료 vs Backup 미완료 또는 불가)
col_left, col_right = st.columns(2)

# --- [왼쪽 컬럼] Backup 완료 ---
with col_left:
    st.metric(label="✅ Backup 완료 (통합 합계)", value=f"{backup_completed_total_count:,} 대")
    
    st.markdown("<p style='font-size: 0.8em; color: gray; margin-bottom: 5px;'>세부 항목 (PM / 보증 / 임대)</p>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="font-size: 0.9em; line-height: 1.6; padding-left: 10px; border-left: 3px solid #4CAF50;">
        • <b>Backup (PM):</b> {backup_pm_count:,} 대<br>
        • <b>Backup (보증):</b> {backup_warranty_count:,} 대<br>
        • <b>Backup (임대):</b> {backup_rental_count:,} 대
        </div>
        """,
        unsafe_allow_html=True
    )

# --- [오른쪽 컬럼] Backup 미완료 또는 불가 ---
with col_right:
    st.metric(label="⚠️ Backup 미완료 또는 불가 (세부 유형 포함)", value=f"{backup_minus_total_count:,} 대")
    
    st.markdown("<p style='font-size: 0.8em; color: gray; margin-bottom: 5px;'>나머지 세부 항목</p>", unsafe_allow_html=True)
    
    sub_items_html = f"• <b>기본 BACKUP-:</b> {backup_minus_base_count:,} 대<br>"
    for sub_type, count in specific_backup_counts.items():
        sub_items_html += f"• <b>{sub_type}:</b> {count:,} 대<br>"
        
    st.markdown(
        f"""
        <div style="font-size: 0.9em; line-height: 1.6; padding-left: 10px; border-left: 3px solid #FF9800;">
        {sub_items_html}
        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()

# 7. 파이그래프 시각화 영역
st.subheader("📈 백업 완료 vs 미완료 현황 비율")

fig, ax = plt.subplots(figsize=(6, 6))
labels = ['Backup 완료', 'Backup 미완료 또는 불가']
sizes = [backup_completed_total_count, backup_minus_total_count]
colors = ['#4CAF50', '#FF9800']

wedges, texts, autotexts = ax.pie(
    sizes, 
    labels=labels, 
    autopct=lambda p: f'{p:.1f}%\n({int(p*sum(sizes)/100):,}대)', 
    startangle=90, 
    colors=colors,
    textprops=dict(color="black", fontsize=11)
)
plt.setp(autotexts, size=11, weight="bold")
ax.set_title("백업 완료 및 미완료 비율", fontsize=13, pad=15, weight="bold")

col_chart1, col_chart2, col_chart3 = st.columns([1, 2, 1])
with col_chart2:
    st.pyplot(fig)

st.divider()

# 8. 검색 및 필터 영역
st.subheader("🔍 검색 및 필터")
filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    search_query = st.text_input("장비명 또는 관리번호 검색", placeholder="검색어를 입력하세요")

with filter_col2:
    departments = sorted([str(d) for d in df_filtered['사용 부서'].dropna().unique()])
    selected_dept = st.selectbox("사용부서 선택", ["전체 부서"] + departments)

with filter_col3:
    filter_options = ["전체보기", "Backup 완료 (통합)", "Backup 미완료 또는 불가 (세부 유형 포함)", "Backup (PM)", "Backup (보증)", "Backup (임대)"] + list(specific_backup_counts.index)
    category_filter = st.selectbox("백업 세부 유형 필터", filter_options)

# 필터 적용 로직
view_df = backup_all_df.copy()

if search_query:
    view_df = view_df[
        view_df['장비명/구성품명'].str.contains(search_query, na=False, case=False) |
        view_df['관리번호'].str.contains(search_query, na=False, case=False)
    ]

if selected_dept != "전체 부서":
    view_df = view_df[view_df['사용 부서'].astype(str) == selected_dept]

if category_filter != "전체보기":
    if category_filter == "Backup 완료 (통합)":
        view_df = view_df[view_df['세부유형'].isin(['Backup 완료 (+)', 'Backup (PM)', 'Backup (보증)', 'Backup (임대)'])]
    elif category_filter == "Backup 미완료 또는 불가 (세부 유형 포함)":
        view_df = view_df[view_df['세부유형'].isin(['BACKUP-'] + list(specific_backup_counts.index))]
    else:
        view_df = view_df[view_df['세부유형'] == category_filter]

# 9. 결과 테이블 출력
st.subheader(f"📋 백업 대상 장비 목록 (총 {len(view_df):,}건)")

display_columns = [col for col in ['관리번호', '장비명/구성품명', '사용 부서', '모델', '일련번호', '관리대상', '취득일자'] if col in view_df.columns]

st.dataframe(
    view_df[display_columns],
    use_container_width=True,
    hide_index=True
)