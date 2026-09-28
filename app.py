import streamlit as st
import pandas as pd
import glob
import os
import re
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
backup_all_df = df_filtered[df_filtered['관리대상'].astype(str).str.contains('backup', na=False, case=False)].copy()
backup_target_count = len(backup_all_df) # backup 대상장비수량(대)

# [수정] 상호 배타적 엄격 분류 함수 (완료 '+'가 포함된 경우 보증/임대/PM 등에서 철저히 제외)
def strict_exclusive_classify(val):
    val_str = str(val)
    # 1. 완료(+)가 포함된 경우 무조건 'Backup 완료 (+)'로 최우선 분류
    if re.search(r'\+', val_str):
        return 'Backup 완료 (+)'
    
    # 2. 보증 포함 건 (+ 제외)
    if '보증' in val_str:
        return 'Backup (보증)'
    
    # 3. 임대 포함 건 (+ 제외)
    if '임대' in val_str:
        return 'Backup (임대)'
        
    # 4. PM 포함 건 (+ 제외)
    if re.search(r'pm', val_str, re.IGNORECASE):
        return 'Backup (PM)'
        
    # 5. BACKUP-(*) 괄호 세부 유형
    match = re.search(r'(BACKUP\s*-\s*\([^)]+\))', val_str, re.IGNORECASE)
    if match:
        sub = match.group(1).upper()
        if sub not in ['BACKUP-(PM)', 'BACKUP-(보증)', 'BACKUP-(임대)']:
            return sub
            
    # 6. 기본 BACKUP- 형태
    if re.search(r'BACKUP-', val_str, re.IGNORECASE):
        return 'BACKUP-'
        
    return '기타'

backup_all_df['세부유형'] = backup_all_df['관리대상'].apply(strict_exclusive_classify)

# 각 항목별 카운트 계산
backup_completed_count = len(backup_all_df[backup_all_df['세부유형'] == 'Backup 완료 (+)'])
backup_minus_count = len(backup_all_df[backup_all_df['세부유형'] == 'BACKUP-'])
backup_pm_count = len(backup_all_df[backup_all_df['세부유형'] == 'Backup (PM)'])
backup_warranty_count = len(backup_all_df[backup_all_df['세부유형'] == 'Backup (보증)'])
backup_rental_count = len(backup_all_df[backup_all_df['세부유형'] == 'Backup (임대)'])

# 기타 괄호형 세부유형 집계
excluded_types = ['Backup 완료 (+)', 'BACKUP-', 'Backup (PM)', 'Backup (보증)', 'Backup (임대)', '기타']
specific_backup_counts = backup_all_df[~backup_all_df['세부유형'].isin(excluded_types)].groupby('세부유형').size()

# --- 화면 UI 구성 ---
st.title("🏥 의료기기 백업(Backup) 현황 조회 대시보드")

# 참고 파일 및 기준일 안내 박스
st.info(f"📁 **참고 파일명:** `{filename}` &nbsp;&nbsp;|&nbsp;&nbsp; 📅 **기준일:** `{기준일}`")

# 4. 요약 대시보드 카드 (1단: 전체 및 주요 지표)
st.subheader("📊 전체 백업 현황 요약")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="전체 장비수량", value=f"{total_equipment_count:,} 대")
with col2:
    st.metric(label="Backup 대상장비수량", value=f"{backup_target_count:,} 대")
with col3:
    st.metric(label="Backup 완료 (+)", value=f"{backup_completed_count:,} 대")

# 요약 대시보드 카드 (2단: 구분 지표 및 BACKUP-)
col4, col5, col6, col7 = st.columns(4)
with col4:
    st.metric(label="BACKUP-", value=f"{backup_minus_count:,} 대")
with col5:
    st.metric(label="Backup (PM)", value=f"{backup_pm_count:,} 대")
with col6:
    st.metric(label="Backup (보증)", value=f"{backup_warranty_count:,} 대")
with col7:
    st.metric(label="Backup (임대)", value=f"{backup_rental_count:,} 대")

# 요약 대시보드 카드 (3단: 기타 Backup-(*) 개별 세부 항목 동적 표시)
if not specific_backup_counts.empty:
    st.subheader("📌 기타 Backup-(*) 세부 유형별 현황")
    sub_cols = st.columns(len(specific_backup_counts) if len(specific_backup_counts) <= 4 else 4)
    for idx, (sub_type, count) in enumerate(specific_backup_counts.items()):
        with sub_cols[idx % len(sub_cols)]:
            st.metric(label=sub_type, value=f"{count:,} 대")

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
    filter_options = ["전체보기", "Backup 완료 (+)", "BACKUP-", "Backup (PM)", "Backup (보증)", "Backup (임대)"] + list(specific_backup_counts.index)
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
    view_df = view_df[view_df['세부유형'] == category_filter]

# 6. 결과 테이블 출력
st.subheader(f"📋 백업 대상 장비 목록 (총 {len(view_df):,}건)")

display_columns = [col for col in ['관리번호', '장비명/구성품명', '사용 부서', '모델', '일련번호', '관리대상', '취득일자'] if col in view_df.columns]

st.dataframe(
    view_df[display_columns],
    use_container_width=True,
    hide_index=True
)