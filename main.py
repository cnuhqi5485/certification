import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="체크리스트 평가 시스템", layout="wide")

st.title("📋 우리 부서 체크리스트 시스템")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 데이터 가져오기 및 강력한 전처리
try:
    # 엑셀의 두 번째 줄(header=1)을 제목으로 읽어옵니다.
    df = conn.read(header=1)
    
    # [핵심 수정 1] 컬럼 이름의 앞뒤 공백을 싹 제거합니다.
    df.columns = df.columns.str.strip()

    # [핵심 수정 2] 이름이 정확하지 않아도 핵심 단어로 찾아서 바꿉니다.
    # 예: " 기준 번호 " -> "문항", "Question" -> "질문"
    new_columns = {}
    for col in df.columns:
        if "기준" in col and "번호" in col:
            new_columns[col] = "문항"
        elif "Question" in col or "질문" in col:
            new_columns[col] = "질문"
        elif "Answer" in col or "답변" in col:
            new_columns[col] = "답변"
        elif "조사 장소" in col or "장소" in col:
            new_columns[col] = "평가장소"
        elif "대상" in col:
            new_columns[col] = "평가대상"
        elif "조사결과" in col or "평가" in col:
            new_columns[col] = "평가"
            
    # 찾은 이름들을 실제로 적용
    df = df.rename(columns=new_columns)

    # "문항" 컬럼이 제대로 만들어졌는지 확인하고, 없으면 강제로 만듭니다.
    if "문항" not in df.columns:
        # 혹시라도 못 찾았으면 첫 번째 컬럼을 '문항'으로 간주
        df.columns.values[0] = "문항"

    # [데이터 정리]
    # 1. '문항' 컬럼을 글자(String)로 변환 (숫자 1.1과 문자 1.1을 똑같이 처리하기 위해)
    df['문항'] = df['문항'].astype(str)
    
    # 2. 문항 번호가 없거나(nan), 이상한 행(None) 제거
    # (사진에 보이는 Row 0 같은 불필요한 행을 지워줍니다)
    df = df[df['문항'] != 'nan'] 
    df = df[df['문항'] != 'None']

    # 3. '담당위원' 컬럼 처리
    if '담당위원' not in df.columns:
        df['담당위원'] = ""
    else:
        df['담당위원'] = df['담당위원'].fillna("")

    # 4. '평가' 컬럼 처리
    if '평가' not in df.columns:
        df['평가'] = ""
    else:
        df['평가'] = df['평가'].fillna("")

except Exception as e:
    st.error(f"데이터 처리 중 문제가 발생했습니다: {e}")
    st.write("현재 인식된 컬럼명:", df.columns.tolist()) # 에러 시 원인 파악용
    st.stop()

# 탭 나누기
tab1, tab2 = st.tabs(["📝 평가하기 (위원용)", "⚙️ 관리자 (담당 배정 및 결과)"])

# ==========================================
# [TAB 1] 평가 위원용 화면
# ==========================================
with tab1:
    st.header("위원 평가 페이지")
    
    user_name = st.text_input("위원님의 성함을 입력해주세요", placeholder="예: 최준석")

    if user_name:
        # 내 이름이 포함된 행 찾기
        my_tasks = df[df['담당위원'] == user_name]

        if my_tasks.empty:
            st.warning(f"'{user_name}' 위원님께 배정된 문항이 없습니다. 관리자에게 문의하세요.")
        else:
            st.success(f"반갑습니다 {user_name} 위원님! 총 {len(my_tasks)}개의 문항이 있습니다.")
            
            # 보여줄 컬럼 (존재하는 것만)
            target_cols = ['문항', '평가장소', '질문', '답변', '평가']
            cols_to_show = [c for c in target_cols if c in df.columns]

            edited_df = st.data_editor(
                my_tasks[cols_to_show],
                column_config={
                    "평가": st.column_config.TextColumn(
                        "평가 결과",
                        help="상 / 중 / 하 등을 입력하세요",
                        required=True
                    ),
                    "문항": st.column_config.Column(disabled=True),
                    "질문": st.column_config.Column(disabled=True, width="large"),
                    "답변": st.column_config.Column(disabled=True),
                    "평가장소": st.column_config.Column(disabled=True),
                },
                hide_index=True,
                use_container_width=True,
                key="editor"
            )

            if st.button("평가 완료 및 저장", type="primary"):
                try:
                    df.loc[my_tasks.index, '평가'] = edited_df['평가']
                    conn.update(data=df)
                    st.toast("저장 완료!", icon="✅")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")

# ==========================================
# [TAB 2] 관리자용 화면
# ==========================================
with tab2:
    st.header("관리자 페이지")
    
    admin_pw = st.text_input("관리자 비밀번호", type="password")
    if admin_pw == "1234":
        
        st.subheader("1. 문항 배정하기")
        
        col1, col2 = st.columns(2)
        with col1:
            target_member = st.text_input("배정할 위원 이름 (예: 김철수)")
        with col2:
            target_ids = st.text_input("배정할 문항 번호 (콤마로 구분, 예: 1.1, 2.2.1)")

        if st.button("위원 배정 실행"):
            if target_member and target_ids:
                try:
                    # 콤마로 쪼개고 공백 제거
                    id_list = [x.strip() for x in target_ids.split(',')]
                    
                    # [디버깅용] 어떤 번호를 찾으려 하는지 화면에 표시
                    # st.write(f"찾으려는 번호: {id_list}")
                    
                    # 비교 로직: '문항' 컬럼을 문자열로 바꿔서 비교
                    mask = df['문항'].astype(str).isin(id_list)
                    
                    if mask.any():
                        df.loc[mask, '담당위원'] = target_member
                        conn.update(data=df)
                        st.success(f"'{target_member}' 위원에게 {mask.sum()}개의 문항이 배정되었습니다.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"문항 번호를 찾지 못했습니다. (입력값: {id_list})")
                        st.warning("팁: 아래 전체 결과 표의 '문항' 컬럼에 있는 번호와 똑같이 입력했는지 확인해보세요.")
                except Exception as e:
                    st.error(f"오류: {e}")
            else:
                st.warning("이름과 번호를 모두 입력해주세요.")

        st.divider()
        st.subheader("2. 전체 결과 확인")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("전체 결과 CSV 다운로드", csv, 'checklist_result.csv', 'text/csv')