import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import matplotlib
matplotlib.rcParams['font.family'] = ['DejaVu Sans', 'NanumGothic', 'sans-serif']

st.set_page_config(
    page_title="Pronunciation Assessment Dashboard",
    page_icon="🎙️",
    layout="wide"
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'DM Serif Display', serif; }
.section-label {
    font-size: 0.72rem; font-weight: 500; letter-spacing: 0.12em;
    text-transform: uppercase; color: #9b8ea0; margin-bottom: 4px;
}
.student-name {
    font-family: 'DM Serif Display', serif;
    font-size: 2.4rem; color: #1a1a2e; line-height: 1.1;
}
.meeting-badge {
    display: inline-block; background: #1a1a2e; color: #f7f5f2;
    font-size: 0.75rem; font-weight: 500; letter-spacing: 0.08em;
    padding: 4px 12px; border-radius: 20px; margin-top: 6px;
}
.notes-box {
    background: #ffffff; border-left: 4px solid #c9a84c;
    padding: 16px 20px; border-radius: 0 8px 8px 0;
    color: #333; font-size: 0.95rem; line-height: 1.7; margin-top: 8px;
}
.later-box {
    background: #fff8e1; border-left: 4px solid #ffc107;
    padding: 16px 20px; border-radius: 0 8px 8px 0;
    color: #856404; font-size: 0.95rem; line-height: 1.7; margin-top: 8px;
}
</style>
""", unsafe_allow_html=True)

# ── Data ────────────────────────────────────────────────────────────────────
DATA_URL = "https://raw.githubusercontent.com/MK316/temporary/refs/heads/main/data/consulting-260531.csv"

@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv(DATA_URL)
    return df

df = load_data()

# ── Rating scale ─────────────────────────────────────────────────────────────
RATING_ORDER = ["L", "ML", "M", "MH", "H"]
RATING_NUM   = {r: i for i, r in enumerate(RATING_ORDER)}

V_COLS = [c for c in df.columns if c.startswith("V-")]
C_COLS = [c for c in df.columns if c.startswith("C-")]
P_COLS = [c for c in df.columns if c.startswith("P-")]

# ── Colormap: red (L) → white (M) → blue (H) ─────────────────────────────
cmap = LinearSegmentedColormap.from_list(
    "lh_map", ["#d62728", "#f7b89b", "#ffffff", "#9ecae1", "#1f77b4"], N=256
)

def rating_color(val):
    if val not in RATING_NUM:
        return "#eeeeee"
    norm = RATING_NUM[val] / (len(RATING_ORDER) - 1)
    r, g, b, _ = cmap(norm)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

def text_color(bg_hex):
    r = int(bg_hex[1:3], 16) / 255
    g = int(bg_hex[3:5], 16) / 255
    b = int(bg_hex[5:7], 16) / 255
    lum = 0.299*r + 0.587*g + 0.114*b
    return "#1a1a2e" if lum > 0.5 else "#ffffff"

# ── Dropdown ─────────────────────────────────────────────────────────────────
df["_label"] = df["SID"].astype(str) + " · " + df["Meeting"] + " · " + df["Name"]
labels = df["_label"].tolist()

st.markdown("## 🎙️ Pronunciation Assessment Dashboard")
st.markdown("---")

selected_label = st.selectbox("학생 선택 (SID · Meeting · Name)", labels)
row = df[df["_label"] == selected_label].iloc[0]

is_later = str(row.get("Notes", "")).strip() == "Later"

st.markdown(f"""
<div style='margin: 20px 0 28px 0;'>
  <div class='section-label'>Selected Student</div>
  <div class='student-name'>{row['Name']}</div>
  <span class='meeting-badge'>{row['Meeting']}</span>
</div>
""", unsafe_allow_html=True)

# ── 1. Grades table ───────────────────────────────────────────────────────────
st.markdown("### 📋 성적")

hw_cols = ["HW01", "HW02", "HW03", "HW04", "HW05"]
grade_data = {
    "항목": ["Midterm"] + hw_cols + ["HW-Song-extra"],
    "값":   [row["Midterm"]] + [row[h] for h in hw_cols] + [row["HW-Song-extra"]],
}
grade_df = pd.DataFrame(grade_data)

def style_grade(v):
    if v == "Completed":
        return "background-color:#d4edda; color:#155724; font-weight:500;"
    elif isinstance(v, str) and v not in ("Completed",):
        return "background-color:#f8d7da; color:#721c24;"
    return ""

styled = (
    grade_df.style
    .map(style_grade, subset=["값"])
    .set_properties(**{"text-align": "center"})
    .set_table_styles([
        {"selector": "th", "props": [
            ("background-color", "#1a1a2e"), ("color", "#f7f5f2"),
            ("font-size", "0.8rem"), ("letter-spacing", "0.06em"), ("text-align", "center")
        ]},
        {"selector": "td", "props": [("font-size", "0.95rem"), ("padding", "8px 16px")]},
    ])
)
st.dataframe(styled, use_container_width=True, hide_index=True)

st.markdown("---")

if is_later:
    st.info("⏳ 이 학생의 발음 평가 데이터는 아직 입력되지 않았습니다 (Later).")
else:
    # ── 2. Feature heatmaps ────────────────────────────────────────────────────
    def draw_heatmap(title, cols, row_data, emoji):
        st.markdown(f"### {emoji} {title}")
        labels_list = [c.split("-", 1)[1] for c in cols]
        values      = [str(row_data[c]).strip() for c in cols]
        colors      = [rating_color(v) for v in values]
        txt_colors  = [text_color(c) for c in colors]

        fig, ax = plt.subplots(figsize=(len(cols) * 1.35, 1.6))
        fig.patch.set_facecolor("#f7f5f2")
        ax.set_facecolor("#f7f5f2")

        for i, (lbl, val, bg, tc) in enumerate(zip(labels_list, values, colors, txt_colors)):
            rect = mpatches.FancyBboxPatch(
                (i, 0), 0.88, 0.78,
                boxstyle="round,pad=0.05",
                linewidth=0,
                facecolor=bg,
            )
            ax.add_patch(rect)
            ax.text(i + 0.44, 0.6,  val, ha="center", va="center",
                    fontsize=13, fontweight="bold", color=tc)
            ax.text(i + 0.44, 0.18, lbl, ha="center", va="center",
                    fontsize=7.5, color="#555")

        ax.set_xlim(-0.1, len(cols))
        ax.set_ylim(-0.05, 0.9)
        ax.axis("off")
        plt.tight_layout(pad=0.2)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

        legend_html = "<div style='display:flex; gap:8px; flex-wrap:wrap; margin:-8px 0 16px 0;'>"
        for r in RATING_ORDER:
            bg = rating_color(r)
            tc = text_color(bg)
            legend_html += (
                f"<span style='background:{bg}; color:{tc}; padding:2px 10px; "
                f"border-radius:12px; font-size:0.75rem; font-weight:600;'>{r}</span>"
            )
        legend_html += "</div>"
        st.markdown(legend_html, unsafe_allow_html=True)

    draw_heatmap("모음 (Vowels)", V_COLS, row, "🔵")
    draw_heatmap("자음 (Consonants)", C_COLS, row, "🟠")
    draw_heatmap("운율 (Prosody)", P_COLS, row, "🟢")

    st.markdown("---")

    # ── 3. Notes ───────────────────────────────────────────────────────────────
    st.markdown("### 📝 Notes")
    notes_text = str(row["Notes"]).strip() if pd.notna(row["Notes"]) and str(row["Notes"]).strip() not in ("", "Later") else ""
    if notes_text:
        st.markdown(f"<div class='notes-box'>{notes_text}</div>", unsafe_allow_html=True)
    else:
        st.markdown("_노트 없음_")

    st.markdown("---")

    # ── 4. Radar chart ─────────────────────────────────────────────────────────
    st.markdown("### 📡 발음 평가 (Accuracy / Fluency / Intelligibility)")

    acc  = float(row["Accuracy"])
    flu  = float(row["Fluency"])
    intel = float(row["Intelligibility"])

    if acc == 0 and flu == 0 and intel == 0:
        st.info("⏳ 평가 점수가 아직 입력되지 않았습니다.")
    else:
        radar_labels = ["Accuracy", "Fluency", "Intelligibility"]
        radar_values = [acc, flu, intel]

        angles      = np.linspace(0, 2 * np.pi, 3, endpoint=False).tolist()
        values_plot = radar_values + [radar_values[0]]
        angles_plot = angles + [angles[0]]

        fig, ax = plt.subplots(figsize=(4.5, 4.5), subplot_kw=dict(polar=True))
        fig.patch.set_facecolor("#f7f5f2")
        ax.set_facecolor("#f7f5f2")

        for r in [20, 40, 60, 80, 100]:
            ring_v = [r] * 3 + [r]
            ax.plot(angles_plot, ring_v, color="#cccccc", linewidth=0.6, linestyle="--", zorder=1)

        ax.fill(angles_plot, values_plot, color="#1f77b4", alpha=0.25, zorder=2)
        ax.plot(angles_plot, values_plot, color="#1f77b4", linewidth=2.5, zorder=3)
        ax.scatter(angles, radar_values, s=70, color="#1a1a2e", zorder=4)

        for angle, lbl, val in zip(angles, radar_labels, radar_values):
            ax.text(angle, val + 12, f"{lbl}\n{int(val)}", ha="center", va="center",
                    fontsize=9.5, fontweight="600", color="#1a1a2e")

        ax.set_ylim(0, 115)
        ax.set_yticks([])
        ax.set_xticks([])
        ax.spines["polar"].set_visible(False)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.pyplot(fig, use_container_width=True)
        plt.close(fig)
