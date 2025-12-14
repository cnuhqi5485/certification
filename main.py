import streamlit as st
import pandas as pd

# [핵심] 캐시 삭제
st.cache_data.clear()

st.set_page_config(layout="wide")
st.title("🏥 2025년도 인증 조사 평가 시스템")

# =========================================================
# 👇 여기에 복사해온 정보를 입력하세요! (따옴표 안에 넣으세요)
# =========================================================
sheet_id = "1sbsE7aRpQYf3E_GZhIuvC4Ht6d9R22zs"  # 시트 ID (주소 중간에 있는 긴 문자열)

# 1. admin 시트의 gid 숫자 (주소창 맨 끝 gid=... 확인)
gid_admin = "1468393137"  # 예시입니다! 강사님 시트의 숫자로 바꾸세요.

# 2. 설문데이터 시트의 gid 숫자
gid_main = "0"            # 보통 첫 번째 시트는 0입니다. (확인 필요)
# =========================================================

try:
    # 3. 판다스로 직접 불러오기 (Connection 안 씀 -> 에러 해결!)
    base_url = f"https://docs.google.com/spreadsheets/d/1sbsE7aRpQYf3E_GZhIuvC4Ht6d9R22zs/export?format=csv&gid="
    
    # (1) 관리자 데이터 읽기
    df_admin = pd.read_csv(base_url + gid_admin)
    # 이름과 기준번호 열만 남기기 (공백 제거 포함)
    df_admin.columns = df_admin.columns.str.strip() 
    df_admin = df_admin[['이름', '기준번호']]

    # (2) 설문 데이터 읽기 (skiprows=1 적용)
    df_main = pd.read_csv(base_url + gid_main, skiprows=1)
    
    # (3) 데이터 다듬기
    df_main = df_main.dropna(subset=['기준번호'])
    df_main['기준번호'] = df_main['기준번호'].astype(str)

except Exception as e:
    st.error(f"❌ 데이터 로딩 실패! GID 숫자를 정확히 입력했는지 확인해주세요.\n에러 내용: {e}")
    st.stop()

# --- 사이드바 로그인 ---
with st.sidebar:
    st.header("🔐 위원 로그인")
    input_name = st.text_input("성함 입력", placeholder="예: 김철수")

# --- 메인 로직 ---
if input_name:
    # 이름 찾기
    user_row = df_admin[df_admin['이름'] == input_name]
    
    if user_row.empty:
        st.error(f"⛔ '{input_name}' 위원님은 등록되지 않았습니다.")
        with st.expander("등록된 위원 명단 보기"):
            st.dataframe(df_admin)
    else:
        st.success(f"👋 환영합니다, **{input_name}** 위원님!")
        
        # 권한 가져오기
        permission_str = str(user_row.iloc[0]['기준번호'])
        target_ids = [x.strip() for x in permission_str.split(',')]
        
        # 필터링
        my_data = df_main[df_main['기준번호'].isin(target_ids)]
        
        if my_data.empty:
            st.warning(f"배정된 문항({target_ids})을 찾을 수 없습니다.")
        else:
            st.write(f"총 **{len(my_data)}개**의 평가 문항이 배정되었습니다.")
            
            # 평가 화면
            st.data_editor(
                my_data,
                hide_index=True,
                use_container_width=True,
                height=600,
                key="editor"
            )
else:
    st.info("👈 왼쪽 사이드바에 성함을 입력해주세요.")