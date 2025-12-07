import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="체크리스트 평가 시스템", layout="wide")

st.title("📋 우리 부서 체크리스트 시스템")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 데이터 가져오기 및 청소 (Cleaning)
try:
    # 엑셀의 두 번째 줄(header=1)을 제목으로 읽어옵니다.
    df = conn.read(header=1, ttl=0)
    
    # -----------------------------------------------------------
    # [1단계] 컬럼 이름 강제 지정 (순서대로)
    # -----------------------------------------------------------
    new_columns = list(df.columns)
    if len(new_columns) >= 7:
        new_columns[0] = "문항"      
        new_columns[1] = "평가장소"  
        new_columns[2] = "평가대상"  
        new_columns[4] = "질문"      
        new_columns[5] = "답변"      
        new_columns[6] = "평가"      
        df.columns = new_columns

    # -----------------------------------------------------------
    # [2단계] 데이터 빈칸 채우기 (병합된 셀 처리)
    # -----------------------------------------------------------
    # '문항'과 '질문'이 비어있으면 윗줄 내용을 복사해옴
    df['문항'] = df['문항'].fillna(method='ffill')
    df['평가장소'] = df['평가장소'].fillna(method='ffill')
    df['질문'] = df['질문'].fillna(method='ffill')
    
    # -----------------------------------------------------------
    # [3단계] 문항 번호 대청소 (이게 핵심!)
    # -----------------------------------------------------------
    # 1. 문자로 변환
    df['문항'] = df['문항'].astype(str)
    # 2. 앞뒤 공백 제거 ( " 1.1 " -> "1.1" )
    df['문항'] = df['문항'].str.strip()
    # 3. 쓸모없는 행 제거 ('nan', 'None' 등)
    df = df[~df['문항'].isin(['nan', 'None', '', 'NaN', '기준 번호'])]

    # 담당위원 및 평가 컬럼 초기화
    if '담당위원' not in df.columns:
        df['담당위원'] = ""
    else:
        df['담당위원'] = df['담당위원'].fillna("") # 빈칸은 공백으로
        df['담당위원'] = df['담당위원'].astype(str).str.strip() # 담당위원 이름도 공백 제거

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
        safe_name = user_name.strip() # 입력한 이름 공백 제거
        
        # 내 이름이 포함된 행 찾기
        my_tasks = df[df['담당위원'].str.contains(safe_name, na=False)]

        if my_tasks.empty:
            st.warning(f"'{safe_name}' 위원님께 배정된 문항이 없습니다.")
            st.info("관리자 탭에서 문항이 정상적으로 배정되었는지 확인해주세요.")
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
        
        # [NEW] 현재 존재하는 문항 번호 보여주기 (복사해서 쓰시라고)
        unique_ids = df['문항'].unique()
        with st.expander("ℹ️ 현재 엑셀에 있는 '문항 번호' 목록 보기 (클릭)"):
            st.code(", ".join(unique_ids))
            st.caption("위 목록에 있는 번호를 그대로 복사해서 입력하세요.")

        col1, col2 = st.columns(2)
        with col1:
            target_member = st.text_input("배정할 위원 이름 (예: 최준석)")
        with col2:
            target_ids = st.text_input("배정할 문항 번호 (예: 1.1, 1.2)")

        if st.button("위원 배정 실행"):
            if target_member and target_ids:
                try:
                    # 입력받은 번호들 공백 제거
                    id_list = [x.strip() for x in target_ids.split(',')]
                    
                    # 엑셀에 있는 번호와 비교
                    mask = df['문항'].isin(id_list)
                    
                    if mask.any():
                        # 배정 실행
                        df.loc[mask, '담당위원'] = target_member.strip()
                        conn.update(data=df)
                        
                        st.success(f"'{target_member}' 위원에게 총 {mask.sum()}개의 행이 배정되었습니다.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("입력하신 문항 번호를 찾을 수 없습니다.")
                        st.warning(f"입력값: {id_list}")
                        st.info("팁: 위 '문항 번호 목록'을 열어서 번호가 정확한지 확인해보세요.")
                except Exception as e:
                    st.error(f"오류: {e}")

        st.divider()
        st.subheader("2. 전체 결과 확인")
        st.dataframe(df)
        
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("전체 결과 CSV 다운로드", csv, 'checklist_result.csv', 'text/csv')