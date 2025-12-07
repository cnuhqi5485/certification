import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="체크리스트 평가 시스템", layout="wide")

st.title("📋 우리 부서 체크리스트 시스템")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 데이터 가져오기 및 전처리
try:
    # [핵심 수정] header=1 : 엑셀의 첫 줄(제목)을 건너뛰고 두 번째 줄부터 읽습니다.
    data = conn.read(ttl=0, header=1)
    df = pd.DataFrame(data)

    # 엑셀의 영어/한글 컬럼명을 코드가 이해하는 이름으로 바꿉니다.
    rename_map = {
        "기준 번호": "문항",
        "Question": "질문",
        "조사결과": "평가",
        "Answer": "답변",
        "조사 장소": "평가장소",
        "대상": "평가대상"
    }
    # 실제 컬럼명 변경 적용
    df = df.rename(columns=rename_map)

    # '문항' 컬럼을 문자열(글자)로 변환 (1.5, 2.2.1 같은 숫자를 문자로 인식시키기 위해)
    if '문항' in df.columns:
        df['문항'] = df['문항'].astype(str)

    # '담당위원' 컬럼이 없으면 새로 만듭니다.
    if '담당위원' not in df.columns:
        df['담당위원'] = ""
    else:
        # 기존 담당위원이 있다면 빈칸(NaN)을 공백("")으로 채움
        df['담당위원'] = df['담당위원'].fillna("")

    # '평가' 컬럼도 빈칸 처리
    if '평가' not in df.columns:
        df['평가'] = ""
    else:
        df['평가'] = df['평가'].fillna("")

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
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
        # 담당위원이 내 이름인 것만 필터링
        my_tasks = df[df['담당위원'] == user_name]

        if my_tasks.empty:
            st.warning(f"'{user_name}' 위원님께 배정된 문항이 없습니다. 관리자에게 문의하세요.")
        else:
            st.success(f"반갑습니다 {user_name} 위원님! 총 {len(my_tasks)}개의 문항이 있습니다.")
            
            # 보여줄 컬럼만 선택 (문항, 질문, 답변, 평가)
            # 엑셀에 있는 컬럼만 보여주도록 필터링
            cols_to_show = ['문항', '평가장소', '질문', '답변', '평가']
            available_cols = [c for c in cols_to_show if c in my_tasks.columns]

            edited_df = st.data_editor(
                my_tasks[available_cols],
                column_config={
                    "평가": st.column_config.TextColumn(
                        "평가 결과 (상/중/하)",
                        help="여기에 평가 내용을 입력하세요",
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
                    # 원본 데이터(df)의 '평가' 컬럼을 업데이트
                    # edited_df의 인덱스를 사용하여 원본 위치에 값을 넣음
                    df.loc[my_tasks.index, '평가'] = edited_df['평가']
                    
                    # 구글 시트에 업데이트
                    conn.update(data=df)
                    
                    st.toast("✅ 평가 내용이 저장되었습니다!", icon="💾")
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
        st.info("엑셀의 '기준 번호'를 기준으로 배정합니다.")
        
        col1, col2 = st.columns(2)
        with col1:
            target_member = st.text_input("배정할 위원 이름 (예: 김철수)")
        with col2:
            target_ids = st.text_input("배정할 문항 번호 (콤마로 구분, 예: 1.1, 2.2.1)")

        if st.button("위원 배정 실행"):
            if target_member and target_ids:
                try:
                    # 입력된 문항 번호를 리스트로 만듦 (공백 제거)
                    id_list = [x.strip() for x in target_ids.split(',')]
                    
                    # [중요] 엑셀의 문항 번호와 비교 (둘 다 문자열로)
                    mask = df['문항'].astype(str).isin(id_list)
                    
                    if mask.any():
                        # 해당 문항의 담당위원을 업데이트
                        df.loc[mask, '담당위원'] = target_member
                        
                        # 구글 시트 저장
                        conn.update(data=df)
                        
                        st.success(f"'{target_member}' 위원에게 문항 {len(df[mask])}개가 배정되었습니다.")
                        st.rerun()
                    else:
                        st.error(f"입력하신 문항 번호({target_ids})를 찾을 수 없습니다. '기준 번호'를 확인해주세요.")
                except Exception as e:
                    st.error(f"오류 발생: {e}")
            else:
                st.warning("이름과 문항 번호를 입력해주세요.")

        st.divider()
        st.subheader("2. 전체 결과 확인")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="전체 결과 CSV 다운로드",
            data=csv,
            file_name='checklist_result.csv',
            mime='text/csv',
        )