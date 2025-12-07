import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="체크리스트 평가 시스템", layout="wide")

st.title("📋 우리 부서 체크리스트 시스템")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 데이터 가져오기 (에러 완벽 수정 버전)
try:
    # 엑셀 읽기 (헤더는 2번째 줄로 가정)
    df = conn.read(header=1, ttl=0)
    
    # -----------------------------------------------------------
    # [수정된 부분] 이름표 교체 방식 변경
    # "하나만 고쳐!" (X) -> "새 명단으로 갈아끼워!" (O)
    # -----------------------------------------------------------
    
    # 현재 컬럼 이름들을 리스트(목록)로 가져옵니다. (리스트는 수정 가능함)
    new_columns = list(df.columns)
    
    # 컬럼 개수가 충분한지 확인 후 이름 변경
    if len(new_columns) >= 7:
        new_columns[0] = "문항"      # 첫 번째 칸
        new_columns[1] = "평가장소"  # 두 번째 칸
        new_columns[2] = "평가대상"  # 세 번째 칸
        # new_columns[3] 은 건너뜀 (환자)
        new_columns[4] = "질문"      # 다섯 번째 칸
        new_columns[5] = "답변"      # 여섯 번째 칸
        new_columns[6] = "평가"      # 일곱 번째 칸
        
        # [중요] 수정된 리스트를 데이터프레임의 컬럼으로 통째로 덮어씌움
        df.columns = new_columns
    
    # -----------------------------------------------------------
    # [데이터 살리기] 병합된 셀(Merged Cells) 채우기
    # -----------------------------------------------------------
    # 문항 번호가 비어있으면 바로 윗줄의 번호를 가져와서 채움 (Forward Fill)
    df['문항'] = df['문항'].fillna(method='ffill')
    df['평가장소'] = df['평가장소'].fillna(method='ffill')
    df['질문'] = df['질문'].fillna(method='ffill')
    
    # 이제 진짜 쓸모없는 행(헤더 찌꺼기 등) 제거
    # '문항' 칸이 진짜로 비어있거나, 이상한 글자가 들어간 경우 제외
    df = df[~df['문항'].isin(['nan', 'None', '', 'NaN', '기준 번호'])]
    
    # 담당위원 및 평가 컬럼 빈칸 채우기
    if '담당위원' not in df.columns:
        df['담당위원'] = ""
    else:
        df['담당위원'] = df['담당위원'].fillna("")

    if '평가' not in df.columns:
        df['평가'] = ""
    else:
        df['평가'] = df['평가'].fillna("")

except Exception as e:
    st.error(f"데이터 로딩 중 오류 발생: {e}")
    # 디버깅용: 현재 컬럼 상태 보여주기
    # st.write(df.columns) 
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
        
        # 내 이름 찾기
        my_tasks = df[df['담당위원'].astype(str).str.contains(safe_name, na=False)]

        if my_tasks.empty:
            st.warning(f"'{safe_name}' 위원님께 배정된 문항이 없습니다.")
        else:
            st.success(f"반갑습니다 {safe_name} 위원님! 총 {len(my_tasks)}개의 항목이 있습니다.")
            
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
                    st.toast("✅ 저장 완료!", icon="💾")
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
        st.info("문항 번호를 입력하면 해당 문항의 세부 내용까지 모두 배정됩니다.")
        
        col1, col2 = st.columns(2)
        with col1:
            target_member = st.text_input("배정할 위원 이름 (예: 김철수)")
        with col2:
            target_ids = st.text_input("배정할 문항 번호 (콤마로 구분, 예: 1.1, 1.2)")

        if st.button("위원 배정 실행"):
            if target_member and target_ids:
                try:
                    id_list = [x.strip() for x in target_ids.split(',')]
                    
                    # 문항 번호 포함 여부 확인
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
        
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("전체 결과 CSV 다운로드", csv, 'checklist_result.csv', 'text/csv')