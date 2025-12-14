import streamlit as st
import pandas as pd
import requests # 통신을 위한 라이브러리 (상단 import에 추가하세요)
import json

# [핵심] 캐시 삭제
st.cache_data.clear()

st.set_page_config(layout="wide")
st.title("🏥 2025년도 인증 조사 평가 시스템")

# =========================================================
# 👇 아까 복사한 '웹 앱 URL'을 여기에 붙여넣으세요!
# =========================================================
save_url = "https://script.google.com/macros/s/AKfycbwj-No9iza2of5G9UdwpWDu3oV8TaaYQXNXgOlsjJ0WDEDTYioAlXgUFnnV_5rKmNM0/exec" 

# =========================================================
# 👇 여기에 복사해온 정보를 입력하세요! (따옴표 안에 넣으세요)
# =========================================================
sheet_id = "1fOa1O-bMf83Vn7xiurqbYqVqTeYavdQrTOgsSQyq4a8"  # 시트 ID (주소 중간에 있는 긴 문자열)

# 1. admin 시트의 gid 숫자 (주소창 맨 끝 gid=... 확인)
gid_admin = "2119713345"  # 예시입니다! 강사님 시트의 숫자로 바꾸세요.

# 2. 설문데이터 시트의 gid 숫자
gid_main = "0"            # 보통 첫 번째 시트는 0입니다. (확인 필요)
# =========================================================

try:
    # 3. 판다스로 직접 불러오기 (Connection 안 씀 -> 에러 해결!)
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid="
    
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
    user_row = df_admin[df_admin['이름'] == input_name]
    
    if user_row.empty:
        st.error(f"⛔ '{input_name}' 위원님은 등록되지 않았습니다.")
    else:
        st.success(f"👋 환영합니다, **{input_name}** 위원님!")
        
        # 권한 가져오기
        permission_str = str(user_row.iloc[0]['기준번호'])
        target_ids = [x.strip() for x in permission_str.split(',')]
        
        # 내 번호만 필터링
        my_data = df_main[df_main['기준번호'].isin(target_ids)]
        
        if my_data.empty:
            st.warning("배정된 문항이 없습니다.")
        else:
            st.info("내용을 수정하고 '저장하기' 버튼을 누르세요.")
            
            # 1. 데이터 편집기
            edited_df = st.data_editor(
                my_data,
                hide_index=True,
                use_container_width=True,
                height=600,
                key="editor"
            )
            
            # 2. 진짜 저장 버튼 (클라우드로 전송)
            if st.button("☁️ 클라우드에 저장하기", type="primary"):
                with st.spinner("저장 중입니다..."):
                    try:
                        # 1) 보낼 데이터 준비 (기준번호와 Answer만 추려서 보냄)
                        # 'Question'이나 다른 컬럼은 수정 안 할거니까, 식별자(기준번호)랑 답변만 보냅니다.
                        # 주의: 시트의 컬럼명과 정확히 일치해야 합니다! ('Answer')
                        data_to_send = edited_df[['기준번호', 'Answer']].to_dict(orient='records')
                        
                        # 2) 전송할 보따리 만들기
                        payload = {
                            "user_name": input_name,
                            "data": data_to_send
                        }
                        
                        # 3) Apps Script로 전송 (POST 요청)
                        response = requests.post(save_url, json=payload)
                        
                        # 4) 결과 확인
                        if "성공" in response.text:
                            st.success("✅ 저장 완료! 구글 시트가 업데이트되었습니다.")
                            st.cache_data.clear() # 캐시 비워서 새로고침 시 반영되게 함
                        else:
                            st.error(f"저장 실패. 서버 응답: {response.text}")
                            
                    except Exception as e:
                        st.error(f"에러가 발생했습니다: {e}")

else:
    st.info("👈 왼쪽 사이드바에 성함을 입력해주세요.")