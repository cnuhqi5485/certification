import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.title("우리 부서 체크리스트 ✅")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 데이터 가져오기
data = conn.read()

# --- [여기서부터 텍스트 필드 추가 코드입니다] ---

# 1. 사용자에게 이름 물어보기 (로그인 역할)
user_name = st.text_input("위원님의 성함을 입력해주세요")

if user_name:
    # 2. 전체 데이터에서 '담당위원'이 내 이름이랑 같은 것만 뽑기 (이게 행 숨기기 기능!)
    # df는 전체 엑셀 데이터, my_tasks는 나한테 배정된 문제들
    my_tasks = df[df['담당위원'] == user_name]

    if my_tasks.empty:
        st.warning("배정된 문항이 없습니다. 관리자에게 문의하세요.")
    else:
        st.success(f"{user_name} 위원님, 총 {len(my_tasks)}개의 문항이 있습니다.")
        
        # 3. 내 문항만 화면에 보여주고 평가 입력받기
        # 필요한 컬럼만 딱 골라서 보여줄 수도 있습니다.
        columns_to_show = ['문항', '평가장소', '질문', '평가'] 
        
        # st.data_editor를 쓰면 엑셀처럼 바로 수정 가능!
        edited_df = st.data_editor(my_tasks[columns_to_show])
        
        # 4. 저장 버튼 (구글 시트 업데이트)
        if st.button("평가 완료 및 저장"):
            # 여기에 업데이트 코드 추가 (전체 데이터에서 내 부분만 교체)
            pass