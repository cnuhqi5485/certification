import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="체크리스트 평가 시스템", layout="wide")

st.title("📋 우리 부서 체크리스트 시스템")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 데이터 가져오기 및 '순서'로 강제 이름 붙이기
try:
    # 엑셀의 두 번째 줄(header=1)을 읽어옵니다.
    df = conn.read(header=1)
    
    # [핵심 해결책] 글자로 찾지 않고, '순서'대로 이름을 강제로 붙여버립니다.
    # 엑셀 파일 순서: [기준 번호, 조사 장소, 대상, 환자, Question, Answer, 조사결과]
    # 컴퓨터는 0번부터 셉니다.
    
    # 데이터프레임의 컬럼 개수가 충분한지 확인
    if len(df.columns) >= 7:
        # 기존 컬럼 이름을 우리가 원하는 이름으로 1:1 교체
        df = df.rename(columns={
            df.columns[0]: "문항",      # 첫 번째 칸 (A열)
            df.columns[1]: "평가장소",  # 두 번째 칸 (B열)
            df.columns[2]: "평가대상",  # 세 번째 칸 (C열)
            # df.columns[3]은 '환자'인데 안 씀
            df.columns[4]: "질문",      # 다섯 번째 칸 (E열)
            df.columns[5]: "답변",      # 여섯 번째 칸 (F열)
            df.columns[6]: "평가"       # 일곱 번째 칸 (G열)
        })
    else:
        st.error("엑셀 파일의 칸(열) 개수가 부족합니다. A열부터 G열까지 내용이 있는지 확인해주세요.")
        st.stop()

    # 3. 데이터 다듬기
    # '문항' 컬럼을 글자(String)로 변환 (숫자 1.1과 문자 1.1을 똑같이 처리)
    df['문항'] = df['문항'].astype(str)
    
    # 쓸모없는 행 제거 (제목이 섞여 들어간 경우 등)
    # '문항' 칸이 비어있거나 'nan', 'None'이라고 된 줄은 지웁니다.
    df = df[~df['문항'].isin(['nan', 'None', '', 'NaN'])]
    
    # '담당위원' 컬럼 처리 (없으면 만들고, 있으면 빈칸 채우기)
    if '담당위원' not in df.columns:
        df['담당위원'] = ""
    else:
        df['담당위원'] = df['담당위원'].fillna("")

    # '평가' 컬럼 빈칸 처리
    df['평가'] = df['평가'].fillna("")

except Exception as e:
    st.error(f"데이터 처리 중 문제가 발생했습니다: {e}")
    # 디버깅을 위해 현재 컬럼 상태를 보여줌
    st.write("현재 인식된 컬럼명:", df.columns.tolist())
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
            
            # 보여줄 컬럼
            cols_to_show = ['문항', '평가장소', '질문', '답변', '평가']
            # 실제로 존재하는 컬럼만 선택 (에러 방지)
            valid_cols = [c for c in cols_to_show if c in df.columns]

            edited_df = st.data_editor(
                my_tasks[valid_cols],
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
                    
                    # '문항' 컬럼을 문자열로 바꿔서 비교
                    mask = df['문항'].astype(str).isin(id_list)
                    
                    if mask.any():
                        df.loc[mask, '담당위원'] = target_member
                        conn.update(data=df)
                        st.success(f"'{target_member}' 위원에게 {mask.sum()}개의 문항이 배정되었습니다.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"문항 번호를 찾지 못했습니다. (입력값: {id_list})")
                except Exception as e:
                    st.error(f"오류: {e}")
            else:
                st.warning("이름과 번호를 모두 입력해주세요.")

        st.divider()
        st.subheader("2. 전체 결과 확인")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("전체 결과 CSV 다운로드", csv, 'checklist_result.csv', 'text/csv')