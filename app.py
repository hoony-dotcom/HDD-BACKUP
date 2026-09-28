from flask import Flask, render_template, request
import pandas as pd
import glob
import os
from datetime import datetime

app = Flask(__name__)

def get_latest_excel_file():
    files = glob.glob('의료기기 현황조회_*.xlsx')
    if not files:
        return None, None, None
    
    latest_file = sorted(files)[-1]
    filename = os.path.basename(latest_file)
    
    try:
        date_str = filename.split('_')[1][:8]
        기준일 = datetime.strptime(date_str, '%Y%m%d').strftime('%Y년 %m월 %d일')
    except Exception:
        mtime = os.path.getmtime(latest_file)
        기준일 = datetime.fromtimestamp(mtime).strftime('%Y년 %m월 %d일')
        
    return latest_file, filename, 기준일

@app.route('/')
def index():
    search_query = request.args.get('q', '')
    department = request.args.get('dept', '')
    
    excel_path, filename, 기준일 = get_latest_excel_file()
    
    if not excel_path:
        return "참고할 의료기기 현황조회 엑셀 파일이 존재하지 않습니다.", 404
        
    df = pd.read_excel(excel_path)
    df.columns = df.columns.str.replace('\n', ' ')
    
    # 1. 사용부서가 '88'인 항목 제외
    df_filtered = df[df['사용 부서'].astype(str).str.strip() != '88'].copy()
    
    # [대시보드 통계 지표 계산]
    total_equipment_count = len(df_filtered) # 전체 장비수량 (대)
    
    # Backup이 들어간 대상 장비
    backup_all_df = df_filtered[df_filtered['관리대상'].astype(str).str.contains('backup', na=False, case=False)]
    backup_target_count = len(backup_all_df) # Backup 대상장비수량 (대)
    
    # Backup + (완료) 항목 (관리대상에 'backup'과 '+'가 모두 포함된 경우)
    backup_completed_count = len(df_filtered[
        df_filtered['관리대상'].astype(str).str.contains('backup', na=False, case=False) & 
        df_filtered['관리대상'].astype(str).str.contains(r'\+', na=False, regex=True)
    ]) # Backup 완료
    
    # 2. 기본 조회 목록: 기본적으로 'Backup' 대상 장비들을 보여주되, 검색/필터 적용 가능
    view_df = backup_all_df.copy()
    
    # 검색어 필터링
    if search_query:
        view_df = view_df[
            view_df['장비명/구성품명'].str.contains(search_query, na=False, case=False) |
            view_df['관리번호'].str.contains(search_query, na=False, case=False)
        ]
        
    # 부서별 필터링
    if department:
        view_df = view_df[view_df['사용 부서'].astype(str).str.contains(department, na=False)]
        
    data_list = view_df.fillna('').to_dict(orient='records')
    departments = [d for d in df['사용 부서'].dropna().unique() if str(d).strip() != '88']
    
    return render_template(
        'index.html', 
        data=data_list, 
        departments=departments, 
        query=search_query, 
        selected_dept=department,
        total_equipment_count=total_equipment_count,
        backup_target_count=backup_target_count,
        backup_completed_count=backup_completed_count,
        filename=filename,
        기준일=기준일
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)