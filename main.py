import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.title("우리 부서 체크리스트 ✅")

# 1. 구글 시트 연결하기
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 데이터 읽어오기 (엑셀이랑 똑같이 생겼어요!)
data = conn.read()

# 3. 내 이름으로 필터링하기 (학생이 구현할 부분)
name = st.text_input("이름을 입력하세요")
if name:
    my_data = data[data['해당직원'] == name]
    st.dataframe(my_data)
    
    # 4. 여기서 데이터 편집 기능 추가 (st.data_editor 활용)
    # 편집 후 구글 시트로 다시 업데이트하는 로직은 
    # gspread 같은 라이브러리를 섞어서 쓰거나 
    # Streamlit 최신 기능을 활용하면 됩니다.
