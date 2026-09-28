import streamlit as st
import pandas as pd
import glob
import os
import re
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm

# --- [한글 폰트 깨짐 방지 및 다크/라이트 모드 스타일 설정] ---
plt.rcParams['axes.unicode_minus'] = False

def set_korean_font():
    font_candidates = [
        # Linux / Streamlit Cloud 환경
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
        '/usr/share/fonts/nanum/NanumGothic.ttf',
        # Windows 환경
        'C:/Windows/Fonts/malgun.ttf',
        'C:/Windows/Fonts/NanumGothic.ttf',
        # macOS 환경
        '/Library/Fonts/AppleGothic.ttf'
    ]
    
    applied_font = None
    for path in font_candidates:
        if os.path.exists(path):
            try:
                fm.fontManager.addfont(path)
                font_prop = fm.FontProperties(fname=path)
                font_name = font_prop.get_name()
                plt.rc('font', family=font_name)
                applied_font = font_name
                break
            except Exception:
                continue
                
    if not applied_font:
        system_fonts = [f.name for f in fm.fontManager.ttflist]
        for target in ['NanumGothic', 'Malgun Gothic', 'AppleGothic', 'DejaVu Sans']:
            if target in system_fonts:
                plt.rc('font', family=target)
                break

set_korean_font()
sns.set_theme(style="whitegrid")

# 다크 모드와 라이트 모드 대응 텍스트 컬러 설정
plt.rcParams['text.color'] = '#E0E0E0'
plt.rcParams['axes.labelcolor'] = '#E0E0E0'
plt.rcParams['xtick.color'] = '#E0E0E0'
plt.rcParams['ytick.color'] = '#E0E0E0'

# 페이지 설정 (사이드바 기본 열림)
st.set_page_config(
    page_title="의료기기 백업 현황 대시보드",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 1. 다크 모드와 라이트 모드를 모두 지원하는 유연한 CSS 주입
st.markdown(
    """
    <style>
    .stApp {
        color-scheme: light dark;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 2. 사이드바 구성 (제작 및 문의 이메일 링크 및 개발 앱 목록)
with st.sidebar:
    st.markdown("### 📧 제작 및 문의")
    st.markdown(
        """
        <div style="font-size: 1.15em; font-weight: bold; margin-bottom: 10px;">
        <a href="mailto:dhkoh@inhauh.com" target="_blank" style="text-decoration: none; color: #4FA8F7;">
        ✉️ dhkoh@inhauh.com
        </a>
        </div>
        <div style="font-size: 0.9em; opacity: 0.8;">
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

with col_left:
    st.metric(label="✅ Backup 완료 (통합 합계)", value=f"{backup_completed_total_count:,} 대")
    st.markdown("<p style='font-size: 0.95em; opacity: 0.7; margin-bottom: 5px;'>세부 항목 (PM / 보증 / 임대)</p>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="font-size: 1.05em; line-height: 1.6; padding-left: 10px; border-left: 3px solid #4CAF50;">
        • <b>Backup (PM):</b> {backup_pm_count:,} 대<br>
        • <b>Backup (보증):</b> {backup_warranty_count:,} 대<br>
        • <b>Backup (임대):</b> {backup_rental_count:,} 대
        </div>
        """,
        unsafe_allow_html=True
    )

with col_right:
    st.metric(label="⚠️ Backup 미완료 또는 불가 (세부 유형 포함)", value=f"{backup_minus_total_count:,} 대")
    st.markdown("<p style='font-size: 0.95em; opacity: 0.7; margin-bottom: 5px;'>나머지 세부 항목</p>", unsafe_allow_html=True)
    sub_items_html = f"• <b>기본 BACKUP-:</b> {backup_minus_base_count:,} 대<br>"
    for sub_type, count in specific_backup_counts.items():
        sub_items_html += f"• <b>{sub_type}:</b> {count:,} 대<br>"
    st.markdown(
        f"""
        <div style="font-size: 1.05em; line-height: 1.6; padding-left: 10px; border-left: 3px solid #FF9800;">
        {sub_items_html}
        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()

# 7. 파이그래프 시각화 영역
st.subheader("📈 백업 완료 vs 미완료 현황 비율")

fig, ax = plt.subplots(figsize=(5, 5), dpi=150)
labels = ['Backup Completed', 'Backup Pending / N/A']
sizes = [backup_completed_total_count, backup_minus_total_count]
colors = ['#4CAF50', '#FF9800']

wedges, texts, autotexts = ax.pie(
    sizes, 
    labels=labels, 
    autopct=lambda p: f'{p:.1f}%\n({int(p*sum(sizes)/100):,} Units)', 
    startangle=90, 
    colors=colors,
    textprops=dict(color="#E0E0E0", fontsize=13)
)

plt.setp(texts, size=13, weight="bold")
plt.setp(autotexts, size=14, weight="bold")
ax.set_title("Backup Status Ratio", fontsize=15, pad=20, weight="bold", color="#E0E0E0")

col_chart1, col_chart2, col_chart3 = st.columns([1, 2, 1])
with col_chart2:
    st.pyplot(fig)

st.divider()

# 8. [크기 50% 축소 및 폰트 깨짐 방지 적용] '의공담당'별 백업 미완료 또는 불가 현황 그래프 및 상세표
st.subheader("👤 의공담당별 백업 미완료 또는 불가 현황")

manager_col = '의공담당'

if manager_col in df_filtered.columns:
    pending_df = backup_all_df[backup_all_df['세부유형'].isin(['BACKUP-'] + list(specific_backup_counts.index))].copy()
    
    if not pending_df.empty:
        manager_counts = pending_df[manager_col].astype(str).value_counts().reset_index()
        manager_counts.columns = ['의공담당', '미완료_건수']
        
        # 막대그래프 크기 50% 컴팩트 축소 (figsize=(5, 2.5)) 적용
        fig_m, ax_m = plt.subplots(figsize=(5, 2.5), dpi=150)
        sns.barplot(data=manager_counts, x='의공담당', y='미완료_건수', ax=ax_m, palette='Oranges_r')
        
        ax_m.set_title("의공담당별 백업 미완료/불가 장비 수량", fontsize=10, weight='bold', pad=8, color='#E0E0E0')
        ax_m.set_xlabel("의공담당", fontsize=9, weight='bold', color='#E0E0E0')
        ax_m.set_ylabel("미완료 수량 (대)", fontsize=9, weight='bold', color='#E0E0E0')
        plt.xticks(rotation=45, ha='right', fontsize=8)
        plt.yticks(fontsize=8)
        
        plt.tight_layout()
        
        # 중앙에 보기 좋게 배치 (컬럼 비율 1:2:1)
        col_m1, col_m2, col_m3 = st.columns([1, 2, 1])
        with col_m2:
            st.pyplot(fig_m)
        
        st.markdown("#### 📋 의공담당별 미완료/불가 상세 목록")
        
        selected_manager = st.selectbox("의공담당 선택", ["전체 담당자"] + sorted(manager_counts['의공담당'].unique().tolist()))
        
        table_view_df = pending_df.copy()
        if selected_manager != "전체 담당자":
            table_view_df = table_view_df[table_view_df[manager_col].astype(str) == selected_manager]
            
        display_cols = [col for col in ['관리번호', '장비명/구성품명', '사용 부서', '의공담당', '모델', '일련번호', '관리대상', '취득일자'] if col in table_view_df.columns]
        
        st.dataframe(
            table_view_df[display_cols],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("현재 백업 미완료 또는 불가 항목이 존재하지 않습니다.")
else:
    st.warning("엑셀 파일 내에 '의공담당' 컬럼이 존재하지 않습니다. 컬럼명을 확인해 주세요.")

st.divider()

# 9. 일반 검색 및 전체 필터 영역
st.subheader("🔍 전체 장비 검색 및 필터")
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

# 결과 테이블 출력
st.subheader(f"📋 백업 대상 장비 목록 (총 {len(view_df):,}건)")

display_columns = [col for col in ['관리번호', '장비명/구성품명', '사용 부서', '의공담당', '모델', '일련번호', '관리대상', '취득일자'] if col in view_df.columns]

st.dataframe(
    view_df[display_columns],
    use_container_width=True,
    hide_index=True
)