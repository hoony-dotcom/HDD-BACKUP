import streamlit as st
import pandas as pd
import glob
import os
from datetime import datetime

# 페이지 설정
st.set_page_config(
    page_title="의료기기 백업 현황 대시보드",
    page_icon="🏥",
    layout="wide"
)

# 1. 최신 엑셀 파일 자동 탐색 및 기준일 파싱 함수
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

# 2. 전처리: 사용부서가 '88'인 항목 제외
df_filtered = df[df['사용 부서'].astype(str).str.strip() != '88'].copy()

# 3. 대시보드 지표 계산
total_equipment_count = len(df_filtered) # 전체 장비수량(대)

# Backup 전체 대상
backup_all_df = df_filtered[df_filtered['관리대상'].astype(str).str.contains('backup', na=False, case=False)]
backup_target_count = len(backup_all_df) # backup 대상장비수량(대)

# Backup 완료 (backup + 포함)
backup_completed_count = len(df_filtered[
    df_filtered['관리대상'].astype(str).str.contains('backup', na=False, case=False) & 
    df_filtered['관리대상'].astype(str).str.contains(r'\+', na=False, regex=True)
])

# [추가 구분 항목 계산]
backup_pm_count = len(backup_all_df[backup_all_df['관리대상'].astype(str).str.contains(r'pm', na=False, case=False)])
backup_warranty_count = len(backup_all_df[backup_all_df['관리대상'].astype(str).str.contains(r'보증', na=False, case=False)])
backup_rental_count = len(backup_all_df[backup_all_df['관리대상'].astype(str).str.contains(r'임대', na=False, case=False)])

# --- 화면 UI 구성 ---
st.title("🏥 의료기기 백업(Backup) 현황 조회 대시보드")

# 참고 파일 및 기준일 안내 박스
st.info(f"📁 **참고 파일명:** `{filename}` &nbsp;&nbsp;|&nbsp;&nbsp; 📅 **기준일:** `{기준일}`")

# 4. 요약 대시보드 카드 (1단: 전체 및 메인 백업 지표)
st.subheader("📊 전체 백업 현황 요약")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="전체 장비수량", value=f"{total_equipment_count:,} 대")
with col2:
    st.metric(label="Backup 대상장비수량", value=f"{backup_target_count:,} 대")
with col3:
    st.metric(label="Backup 완료 (+)", value=f"{backup_completed_count:,} 대")

# 요약 대시보드 카드 (2단: 상세 구분 지표)
col4, col5, col6 = st.columns(3)
with col4:
    st.metric(label="Backup (PM)", value=f"{backup_pm_count:,} 대")
with col5:
    st.metric(label="Backup (보증)", value=f"{backup_warranty_count:,} 대")
with col6:
    st.metric(label="Backup (임대)", value=f"{backup_rental_count:,} 대")

st.divider()

# 5. 검색 및 필터 영역
st.subheader("🔍 검색 및 필터")
filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    search_query = st.text_input("장비명 또는 관리번호 검색", placeholder="검색어를 입력하세요")

with filter_col2:
    departments = sorted([str(d) for d in df_filtered['사용 부서'].dropna().unique()])
    selected_dept = st.selectbox("사용부서 선택", ["전체 부서"] + departments)

with filter_col3:
    category_filter = st.selectbox("백업 세부 유형 필터", ["전체보기", "Backup 완료 (+)", "Backup (PM)", "Backup (보증)", "Backup (임대)"])

# 필터 적용 로직
view_df = backup_all_df.copy()

if search_query:
    view_df = view_df[
        view_df['장비명/구성품명'].str.contains(search_query, na=False, case=False) |
        view_df['관리번호'].str.contains(search_query, na=False, case=False)
    ]

if selected_dept != "전체 부서":
    view_df = view_df[view_df['사용 부서'].astype(str) == selected_dept]

if category_filter == "Backup 완료 (+)":
    view_df = view_df[view_df['관리대상'].astype(str).str.contains(r'\+', na=False, regex=True)]
elif category_filter == "Backup (PM)":
    view_df = view_df[view_df['관리대상'].astype(str).str.contains(r'pm', na=False, case=False)]
elif category_filter == "Backup (보증)":
    view_df = view_df[view_df['관리대상'].astype(str).str.contains(r'보증', na=False, case=False)]
elif category_filter == "Backup (임대)":
    view_df = view_df[view_df['관리대상'].astype(str).str.contains(r'임대', na=False, case=False)]

# 6. 결과 테이블 출력
st.subheader(f"📋 백업 대상 장비 목록 (총 {len(view_df):,}건)")

display_columns = [col for col in ['관리번호', '장비명/구성품명', '사용 부서', '모델', '일련번호', '관리대상', '취득일자'] if col in view_df.columns]

st.dataframe(
    view_df[display_columns],
    use_container_width=True,
    hide_index=True
)