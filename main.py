import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="체크리스트 평가 시스템", layout="wide")

st.title("📋 우리 부서 체크리스트 시스템")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 데이터 가져오기 (절대 삭제하지 않는 안전 모드)
try:
    # 엑셀의 구조를 파악해서 읽어옵니다.
    # header=1은 '두 번째 줄'을 제목으로 본다는 뜻입니다.
    # (첫 번째 줄인 '2025년도...' 제목은 데이터 처리를 위해 어쩔 수 없이 무시됩니다)
    df = conn.read(header=1, ttl=0)
    
    # -----------------------------------------------------------
    # [핵심 수정 1] 병합된 셀(Merged Cell) 채우기
    # 엑셀에서 셀을 합쳐놓으면 컴퓨터는 첫 줄만 읽고 나머지는 빈칸으로 봅니다.
    # ffill() 명령어를 써서 빈칸이 있으면 '바로 위 칸의 내용'을 복사해서 채우게 합니다.
    # 이렇게 해야 1.1 문항의 세부 내용들이 삭제되지 않습니다.
    # -----------------------------------------------------------
    # 1단계: 컬럼 이름 정리 (순서대로 강제 지정)
    # 엑셀 칸 순서: [문항, 장소, 대상, 환자, 질문, 답변, 결과(평가)]
    if len(df.columns) >= 7:
        df.columns.values[0] = "문항"
        df.columns[1] = "평가장소"
        df.columns[2] = "평가대상"
        df.columns[4] = "질문"
        df.columns[5] = "답변"
        df.columns[6] = "평가"
    
    # 2단계: '문항'과 '평가장소', '질문'이 병합되어 있다면 위 내용을 채워넣기
    # "문항" 컬럼의 빈칸을 위에서 아래로 채움
    df['문항'] = df['문항'].fillna(method='ffill')
    df['평가장소'] = df['평가장소'].fillna(method='ffill')
    df['질문'] = df['질문'].fillna(method='ffill')

    # 3단계: 진짜 쓸모없는 빈 줄만 제거 (문항 번호 자체가 아예 없는 경우만)
    df = df[df['문항'].notna()]
    
    # 담당위원 컬럼 처리
    if '담당위원' not in df.columns:
        df['담당위원'] = ""
    else:
        df['담당위원'] = df['담당위원'].fillna("") # 위원 이름도 빈칸이면 채우기

    # 평가 컬럼 처리
    if '평가' not in df.columns:
        df['평가'] = ""
    else:
        df['평가'] = df['평가'].fillna("")

except Exception as e:
    st.error(f"데이터 로딩 중 오류 발생: {e}")
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
        safe_name = user_name.strip()
        
        # 내 이름이 포함된 행 찾기
        my_tasks = df[df['담당위원'].astype(str).str.contains(safe_name, na=False)]

        if my_tasks.empty:
            st.warning(f"'{safe_name}' 위원님께 배정된 문항이 없습니다.")
        else:
            st.success(f"반갑습니다 {safe_name} 위원님! 총 {len(my_tasks)}개의 행(세부 질문 포함)이 있습니다.")
            
            # 보여줄 컬럼
            cols_to_show = ['문항', '평가장소', '질문', '답변', '평가']
            valid_cols = [c for c in cols_to_show if c in df.columns]

            edited_df = st.data_editor(
                my_tasks[valid_cols],
                column_config={
                    "평가": st.column_config.SelectboxColumn(
                        "평가 결과",
                        options=["상", "중", "하", "해당없음"],
                        required=False
                    ),
                    "문항": st.column_config.Column(disabled=True),
                    "질문": st.column_config.Column(disabled=True, width="large"),
                    "답변": st.column_config.Column(disabled=True, width="large"),
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
                    st.toast("✅ 저장되었습니다! (주의: 원본 엑셀의 병합이 풀릴 수 있습니다)", icon="💾")
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
        st.warning("주의: '배정 실행'을 누르면 엑셀 파일의 셀 병합이 풀리고 데이터베이스 형태로 저장됩니다.")
        
        col1, col2 = st.columns(2)
        with col1:
            target_member = st.text_input("배정할 위원 이름 (예: 김철수)")
        with col2:
            target_ids = st.text_input("배정할 문항 번호 (콤마로 구분, 예: 1.1, 1.2)")

        if st.button("위원 배정 실행"):
            if target_member and target_ids:
                try:
                    id_list = [x.strip() for x in target_ids.split(',')]
                    
                    # 문항 번호가 포함된 모든 행을 찾음 (1.1을 찾으면 그 아래 세부 내용들도 다 포함)
                    mask = df['문항'].astype(str).isin(id_list)
                    
                    if mask.any():
                        df.loc[mask, '담당위원'] = target_member.strip()
                        conn.update(data=df)
                        st.success(f"'{target_member}' 위원에게 배정 완료.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"문항 번호를 찾을 수 없습니다: {id_list}")
                except Exception as e:
                    st.error(f"오류: {e}")

        st.divider()
        st.subheader("2. 전체 결과 확인")
        st.dataframe(df)