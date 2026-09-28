import platform
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

# 1. 운영체제별 사용 가능한 대표 한글 폰트 자동 지정
os_name = platform.system()
if os_name == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'
elif os_name == 'Darwin':  # Mac
    plt.rcParams['font.family'] = 'AppleGothic'
else:  # Linux (Streamlit Cloud 등)
    # 시스템에 설치된 나눔고딕 계열 자동 탐색
    font_list = [f.name for f in fm.fontManager.ttflist]
    nanum_fonts = [f for f in font_list if 'Nanum' in f or 'Gothic' in f]
    if nanum_fonts:
        plt.rcParams['font.family'] = nanum_fonts[0]
    else:
        plt.rcParams['font.family'] = 'DejaVu Sans'  # 최후의 대안

# 2. 마이너스 기호 깨짐 방지 및 Seaborn 스타일 적용
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid") # 배경 격자 추가로 시인성 확보

# 3. Streamlit 라이트/다크모드 대응 텍스트 컬러 강제 지정 (선택 사항)
# 배경색이 흰색(라이트 모드)일 때 글자 색상을 검은색으로 고정하여 조화 유지
plt.rcParams['text.color'] = '#000000'
plt.rcParams['axes.labelcolor'] = '#000000'
plt.rcParams['xtick.color'] = '#000000'
plt.rcParams['ytick.color'] = '#000000'