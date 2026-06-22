import streamlit as st
import pandas as pd

# ==============================
# Page setup
# ==============================
st.set_page_config(
    page_title="Grade Check",
    page_icon="📘",
    layout="centered"
)

st.title("📘 성적 확인")
st.caption("학번 뒷자리 5숫자와 Passcode를 입력하세요.")

# ==============================
# CSV URL
# ==============================
CSV_URL = "https://raw.githubusercontent.com/MK316/temporary/refs/heads/main/data/26Sphonf.csv"



# ==============================
# Load data
# ==============================
@st.cache_data
def load_data(url):
    df = pd.read_csv(url, dtype=str)
    df.columns = df.columns.str.strip()

    # 모든 값을 문자열로 처리하고 공백 제거
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    return df


try:
    df = load_data(CSV_URL)
except Exception as e:
    st.error("CSV 파일을 불러오지 못했습니다. GitHub raw CSV 주소를 확인하세요.")
    st.stop()


# ==============================
# Required columns
# ==============================
required_columns = [
    "Names", "SID", "Passcode",
    "Group1", "Group2",
    "Written", "Transcription", "Midterm_Total",
    "Final_Exam", "Group_Activities", "Final_Score",
    "Assignments", "Attendance",
    "Midterm_30", "Final_40", "Total"
]

missing = [col for col in required_columns if col not in df.columns]

if missing:
    st.error("CSV 파일에 다음 컬럼이 없습니다:")
    st.write(missing)
    st.stop()


# ==============================
# Login inputs
# ==============================
with st.form("login_form"):
    sid_input = st.text_input(
        "학번 뒷자리 5숫자",
        max_chars=5,
        placeholder="예: 12345"
    )

    passcode_input = st.text_input(
        "Passcode",
        type="password",
        placeholder="예: kg22658, KM2773, 928"
    )

    submitted = st.form_submit_button("성적 확인")


# ==============================
# Helper functions
# ==============================
def clean_text(x):
    return str(x).strip()


def clean_passcode(x):
    return str(x).strip().lower()


def fmt(x):
    """
    숫자처럼 보이는 값은 불필요한 .0을 제거하고,
    그 외에는 원래 문자열로 표시
    """
    try:
        value = float(x)
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")
    except:
        return str(x)


# ==============================
# Result display
# ==============================
if submitted:
    sid_input_clean = clean_text(sid_input)
    passcode_input_clean = clean_passcode(passcode_input)

    if not sid_input_clean or not passcode_input_clean:
        st.warning("학번 뒷자리 5숫자와 Passcode를 모두 입력하세요.")
        st.stop()

    if not sid_input_clean.isdigit() or len(sid_input_clean) != 5:
        st.warning("학번 뒷자리는 숫자 5자리로 입력하세요.")
        st.stop()

    # SID와 Passcode 비교
    df["SID_clean"] = df["SID"].apply(clean_text)
    df["Passcode_clean"] = df["Passcode"].apply(clean_passcode)

    matched = df[
        (df["SID_clean"] == sid_input_clean) &
        (df["Passcode_clean"] == passcode_input_clean)
    ]

    if matched.empty:
        st.error("입력한 정보와 일치하는 학생을 찾을 수 없습니다. 학번 뒷자리와 Passcode를 다시 확인하세요.")
        st.stop()

    student = matched.iloc[0]

    st.success("성적 정보가 확인되었습니다.")

    st.markdown("---")

    # 0) 이름
    st.subheader(f"👤 이름: {student['Names']}")

    # 1) 그룹소속
    st.markdown(
        f"""
        <div style="padding:16px; border-radius:12px; border:1px solid #ddd; margin-bottom:12px;">
        <b>1) 그룹소속</b><br>
        {student['Group1']}, {student['Group2']}
        </div>
        """,
        unsafe_allow_html=True
    )

    # 2) 중간고사
    st.markdown(
        f"""
        <div style="padding:16px; border-radius:12px; border:1px solid #ddd; margin-bottom:12px;">
        <b>2) 중간고사(30%)</b><br>
        {fmt(student['Written'])} + {fmt(student['Transcription'])} 
        = <b>{fmt(student['Midterm_Total'])} points</b> 
        <span style="color:gray;">(total 100 points)</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 3) 기말고사
    st.markdown(
        f"""
        <div style="padding:16px; border-radius:12px; border:1px solid #ddd; margin-bottom:12px;">
        <b>3) 기말고사(40%)</b><br>
        {fmt(student['Final_Exam'])} + {fmt(student['Group_Activities'])} 
        = <b>{fmt(student['Final_Score'])} points</b> 
        <span style="color:gray;">(total 80 points)</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 4) 과제
    st.markdown(
        f"""
        <div style="padding:16px; border-radius:12px; border:1px solid #ddd; margin-bottom:12px;">
        <b>4) 과제(20%)</b><br>
        <b>{fmt(student['Assignments'])}%</b>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 5) 출석
    st.markdown(
        f"""
        <div style="padding:16px; border-radius:12px; border:1px solid #ddd; margin-bottom:12px;">
        <b>5) 출석(10%)</b><br>
        <b>{fmt(student['Attendance'])}%</b>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 6) 총계
    st.markdown(
        f"""
        <div style="padding:18px; border-radius:12px; border:2px solid #888; margin-bottom:16px;">
        <b>6) 총계</b><br><br>
        중간(30% 환산) + 기말(40% 환산) + 과제(20%) + 출석(10%)<br>
        = {fmt(student['Midterm_30'])} + {fmt(student['Final_40'])} 
        + {fmt(student['Assignments'])} + {fmt(student['Attendance'])}<br><br>
        <span style="font-size:22px;"><b>Total: {fmt(student['Total'])}</b></span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 안내 문구
    st.markdown(
        """
        <div style="
            padding:18px; 
            border-radius:12px; 
            background-color:#fff3cd; 
            border:1px solid #ffeeba;
            color:#5c4400;
            font-size:16px;
            margin-top:18px;
            margin-bottom:18px;">
        <b>안내</b><br>
        지금 확인하는 점수는 시험 결과 그대로의 성적이며, 
        최종 성적은 전체적으로 약간의 상향 조정이 있을 수 있다는 점 숙지하기 바랍니다.
        </div>
        """,
        unsafe_allow_html=True
    )

    # Letter grade box
    st.markdown("### Letter Grade 기준")

    st.markdown(
        """
        <div style="padding:16px; border-radius:12px; border:1px solid #ddd;">
        <table style="width:100%; border-collapse:collapse;">
            <tr>
                <th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">Letter Grade</th>
                <th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">Range</th>
            </tr>
            <tr>
                <td style="padding:8px;">A+</td>
                <td style="padding:8px;">95 and above</td>
            </tr>
            <tr>
                <td style="padding:8px;">A</td>
                <td style="padding:8px;">90 and above</td>
            </tr>
            <tr>
                <td style="padding:8px;">B+</td>
                <td style="padding:8px;">85 and above</td>
            </tr>
            <tr>
                <td style="padding:8px;">B</td>
                <td style="padding:8px;">80 and above</td>
            </tr>
            <tr>
                <td style="padding:8px;">C+</td>
                <td style="padding:8px;">75 and above</td>
            </tr>
            <tr>
                <td style="padding:8px;">C</td>
                <td style="padding:8px;">70 and above</td>
            </tr>
            <tr>
                <td style="padding:8px;">D+</td>
                <td style="padding:8px;">65 and above</td>
            </tr>
            <tr>
                <td style="padding:8px;">D</td>
                <td style="padding:8px;">60 and above</td>
            </tr>
            <tr>
                <td style="padding:8px;">F</td>
                <td style="padding:8px;">Below 60</td>
            </tr>
        </table>
        </div>
        """,
        unsafe_allow_html=True
    )

else:
    st.info("정보를 입력한 후 성적 확인 버튼을 누르세요.")
