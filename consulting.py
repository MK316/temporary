import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib
import io
matplotlib.rcParams['font.family'] = ['DejaVu Sans', 'sans-serif']

st.set_page_config(
    page_title="Pronunciation Assessment Dashboard",
    page_icon="🌱",
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
.passcode-wrap {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; padding: 60px 20px;
}
.passcode-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2rem; color: #1a1a2e; margin-bottom: 8px; text-align: center;
}
.passcode-sub {
    font-size: 0.9rem; color: #888; margin-bottom: 32px; text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ── Data ────────────────────────────────────────────────────────────────────
DATA_URL = "https://raw.githubusercontent.com/MK316/temporary/refs/heads/main/data/consulting-260531-updated.csv"

@st.cache_data(ttl=0)
def load_data():
    import requests
    from io import StringIO
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(DATA_URL, headers=headers)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text))

df = load_data()

# ── Rating scale ─────────────────────────────────────────────────────────────
RATING_ORDER = ["L", "ML", "M", "MH", "H"]
RATING_NUM   = {r: i for i, r in enumerate(RATING_ORDER)}

V_COLS = [c for c in df.columns if c.startswith("V-")]
C_COLS = [c for c in df.columns if c.startswith("C-")]
P_COLS = [c for c in df.columns if c.startswith("P-")]

# ── Colormap ─────────────────────────────────────────────────────────────────
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

# ── Session state ─────────────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "student_row" not in st.session_state:
    st.session_state.student_row = None

# ══════════════════════════════════════════════════════════════════════════════
# PDF GENERATION
# ══════════════════════════════════════════════════════════════════════════════
def generate_pdf(row):
    """Generate a one-page PDF report and return as bytes."""
    from matplotlib import font_manager as fm

    def kw(size=9, weight="normal"):
        return {"fontsize": size, "fontweight": weight}

    hw_cols = ["HW01", "HW02", "HW03", "HW04", "HW05"]
    acc   = float(row["Accuracy"])
    flu   = float(row["Fluency"])
    intel = float(row["Intelligibility"])
    notes_text = str(row["Notes"]).strip() if pd.notna(row["Notes"]) and str(row["Notes"]).strip() not in ("", "Later") else "No notes recorded."

    fig = plt.figure(figsize=(11, 8.5))  # Letter landscape
    fig.patch.set_facecolor("#f7f5f2")

    # ── Layout: rows
    gs = gridspec.GridSpec(
        6, 2,
        figure=fig,
        left=0.05, right=0.97,
        top=0.88, bottom=0.05,
        hspace=0.55, wspace=0.12
    )

    BG = "#f7f5f2"

    # ── Header ────────────────────────────────────────────────────────────────
    # Use Ename (English name) for PDF to avoid font issues
    try:
        ename = str(row["Ename"]).strip()
        if not ename or ename.lower() == "nan":
            ename = str(row["Name"]).strip()
    except Exception:
        ename = str(row["Name"]).strip()
    fig.text(0.05, 0.96, "Pronunciation Assessment Report",
             fontsize=15, fontweight="bold", color="#1a1a2e", va="top")
    fig.text(0.05, 0.915,
             f"Student: {ename}   |   Meeting: {row['Meeting']}   |   Midterm: {row['Midterm']}",
             fontsize=9, color="#555", va="top")
    fig.add_artist(plt.Line2D([0.05, 0.97], [0.895, 0.895],
                              transform=fig.transFigure, color="#1a1a2e", linewidth=1))

    # ── Helper: draw a heatmap row in a given axes ────────────────────────────
    def draw_heatmap_ax(ax, title, cols):
        ax.set_facecolor(BG)
        labels_list = [c.split("-", 1)[1] for c in cols]
        values      = [str(row[c]).strip() for c in cols]
        colors_list = [rating_color(v) for v in values]

        n = len(cols)
        for i, (lbl, val, bg) in enumerate(zip(labels_list, values, colors_list)):
            rect = mpatches.FancyBboxPatch(
                (i * 1.1, 0.05), 0.95, 0.75,
                boxstyle="round,pad=0.04",
                linewidth=0, facecolor=bg,
                transform=ax.transData, clip_on=False
            )
            ax.add_patch(rect)
            ax.text(i * 1.1 + 0.475, 0.58, val,
                    ha="center", va="center", color="#ffffff", **kw(9, "bold"))
            lbl_color = "#ffdd57" if text_color(bg) == "#ffffff" else "#444"
            ax.text(i * 1.1 + 0.475, 0.18, lbl,
                    ha="center", va="center", color=lbl_color, **kw(5.5))

        ax.set_xlim(-0.1, n * 1.1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_title(title, color="#1a1a2e", loc="left", pad=3, **kw(8, "bold"))

    # ── Row 0: Scores table (left) + Radar chart (right, spans rows 0-2) ─────
    ax_scores = fig.add_subplot(gs[0:2, 0])
    ax_scores.set_facecolor(BG)
    ax_scores.axis("off")
    ax_scores.set_title("Scores", color="#1a1a2e", loc="left", pad=3, **kw(8, "bold"))

    score_items  = ["Midterm"] + hw_cols + ["HW-Song-extra"]
    score_values = [str(row["Midterm"])] + \
                   [str(row[h]) for h in hw_cols] + \
                   [f"{pd.to_numeric(row['HW-Song-extra'], errors='coerce'):.1f}"]

    col_w = [0.38, 0.62]
    headers_tbl = ["Item", "Score"]
    table_data  = list(zip(score_items, score_values))

    tbl = ax_scores.table(
        cellText=table_data,
        colLabels=headers_tbl,
        colWidths=col_w,
        loc="upper left",
        cellLoc="center"
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(7.5)
    for (row_i, col_i), cell in tbl.get_celld().items():
        cell.set_edgecolor("#dddddd")
        if row_i == 0:
            cell.set_facecolor("#1a1a2e")
            cell.set_text_props(color="white", fontweight="bold")
        else:
            val = table_data[row_i - 1][col_i]
            if val == "Completed":
                cell.set_facecolor("#d4edda")
                cell.set_text_props(color="#155724")
            elif isinstance(val, str) and val not in ("Completed",) and col_i == 1:
                cell.set_facecolor("#ffffff")
            else:
                cell.set_facecolor("#ffffff")

    # ── Radar chart (right column, rows 0-2) ─────────────────────────────────
    ax_radar = fig.add_subplot(gs[0:3, 1], polar=True)
    ax_radar.set_facecolor(BG)

    if acc == 0 and flu == 0 and intel == 0:
        ax_radar.text(0, 0, "Not yet\nentered", ha="center", va="center",
                      fontsize=10, color="#aaa")
        ax_radar.axis("off")
    else:
        radar_labels = ["Accuracy", "Fluency", "Intelligibility"]
        radar_values = [acc, flu, intel]
        angles      = np.linspace(0, 2 * np.pi, 3, endpoint=False).tolist()
        values_plot = radar_values + [radar_values[0]]
        angles_plot = angles + [angles[0]]

        for rv in [20, 40, 60, 80, 100]:
            ax_radar.plot(angles_plot, [rv]*4, color="#cccccc", linewidth=0.5, linestyle="--", zorder=1)

        ax_radar.fill(angles_plot, values_plot, color="#1f77b4", alpha=0.25, zorder=2)
        ax_radar.plot(angles_plot, values_plot, color="#1f77b4", linewidth=2, zorder=3)
        ax_radar.scatter(angles, radar_values, s=40, color="#1a1a2e", zorder=4)

        for angle, lbl, val in zip(angles, radar_labels, radar_values):
            ax_radar.text(angle, val + 14, f"{lbl}\n{int(val)}",
                          ha="center", va="center", fontsize=7.5, fontweight="600", color="#1a1a2e")

        ax_radar.set_ylim(0, 115)
        ax_radar.set_yticks([])
        ax_radar.set_xticks([])
        ax_radar.spines["polar"].set_visible(False)
        ax_radar.set_title("Overall Pronunciation Profile", color="#1a1a2e", pad=10, **kw(8, "bold"))

    # ── Heatmap rows ──────────────────────────────────────────────────────────
    ax_v = fig.add_subplot(gs[2, 0])
    draw_heatmap_ax(ax_v, "Vowels", V_COLS)

    ax_c = fig.add_subplot(gs[3, 0])
    draw_heatmap_ax(ax_c, "Consonants", C_COLS)

    ax_p = fig.add_subplot(gs[4, 0])
    draw_heatmap_ax(ax_p, "Prosody", P_COLS)

    # ── Legend ────────────────────────────────────────────────────────────────
    ax_leg = fig.add_subplot(gs[3:5, 1])
    ax_leg.set_facecolor(BG)
    ax_leg.axis("off")
    ax_leg.set_title("Rating Scale", color="#1a1a2e", loc="left", pad=3, **kw(8, "bold"))
    legend_labels = {"L": "Low", "ML": "Mid-Low", "M": "Mid", "MH": "Mid-High", "H": "High"}
    for idx, (rating, desc) in enumerate(legend_labels.items()):
        bg = rating_color(rating)
        tc = text_color(bg)
        rect = mpatches.FancyBboxPatch(
            (0.05, 0.62 - idx * 0.14), 0.18, 0.11,
            boxstyle="round,pad=0.02",
            linewidth=0, facecolor=bg,
            transform=ax_leg.transAxes
        )
        ax_leg.add_patch(rect)
        ax_leg.text(0.145, 0.675 - idx * 0.14, rating,
                    ha="center", va="center", fontsize=7, fontweight="bold",
                    color=tc, transform=ax_leg.transAxes)
        ax_leg.text(0.30, 0.675 - idx * 0.14, desc,
                    ha="left", va="center", fontsize=7,
                    color="#333", transform=ax_leg.transAxes)

    # ── Notes ─────────────────────────────────────────────────────────────────
    ax_notes = fig.add_subplot(gs[5, :])
    ax_notes.set_facecolor("#fffdf5")
    ax_notes.axis("off")
    ax_notes.add_patch(mpatches.FancyBboxPatch(
        (0, 0), 1, 1, boxstyle="round,pad=0.01",
        linewidth=1.5, edgecolor="#c9a84c", facecolor="#fffdf5",
        transform=ax_notes.transAxes
    ))
    ax_notes.text(0.01, 0.5, notes_text,
                  ha="left", va="center", fontsize=8,
                  color="#333", transform=ax_notes.transAxes, wrap=True)
    ax_notes.set_title("Instructor Notes",
                        color="#1a1a2e", loc="left", pad=3, **kw(8, "bold"))

    # ── Save to bytes ─────────────────────────────────────────────────────────
    buf = io.BytesIO()
    fig.savefig(buf, format="pdf", facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — Passcode Entry
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.authenticated:

    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1, 1.6, 1])
    with col_c:
        st.markdown("""
        <div style='text-align:center; margin-bottom: 32px;'>
          <div style='font-size:3rem;'>🌱</div>
          <div style='font-family:"DM Serif Display",serif; font-size:1.9rem;
                      color:#1a1a2e; margin: 8px 0 6px 0;'>
            Pronunciation Assessment
          </div>
          <div style='font-size:0.9rem; color:#999; letter-spacing:0.05em;'>
            Enter your passcode to view your feedback
          </div>
        </div>
        """, unsafe_allow_html=True)

        passcode_input = st.text_input(
            "Passcode",
            placeholder="e.g.  sunshine42",
            label_visibility="collapsed",
            key="passcode_field"
        )

        submitted = st.button("Enter →", use_container_width=True, type="primary")

        if submitted:
            if not passcode_input.strip():
                st.warning("Please enter your passcode.")
            elif "Passcode" not in df.columns:
                st.error("⚠️ Passcode column not found in the data. Please check the CSV.")
            else:
                entered = passcode_input.strip().lower()
                match = df[df["Passcode"].astype(str).str.strip().str.lower() == entered]
                if len(match) == 0:
                    st.error("❌ Passcode not recognized. Please try again.")
                else:
                    st.session_state.authenticated = True
                    st.session_state.student_row = match.iloc[0]
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 2 — Student Dashboard
# ══════════════════════════════════════════════════════════════════════════════
else:
    row = st.session_state.student_row
    is_later = str(row.get("Notes", "")).strip() == "Later"

    # Header + buttons
    col_title, col_pdf, col_btn = st.columns([4, 1, 1])
    with col_title:
        st.markdown("## 🌱 Pronunciation Assessment Dashboard")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔒 Log out"):
            st.session_state.authenticated = False
            st.session_state.student_row = None
            st.rerun()
    with col_pdf:
        st.markdown("<br>", unsafe_allow_html=True)
        if not is_later:
            pdf_bytes = generate_pdf(row)
            st.download_button(
                label="⬇️ Download PDF",
                data=pdf_bytes,
                file_name=f"{row['Name']}_{row['Meeting']}_report.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    st.markdown("---")

    st.markdown(f"""
    <div style='margin: 20px 0 28px 0;'>
      <div class='section-label'>Selected Student</div>
      <div class='student-name'>{row['Name']}</div>
      <span class='meeting-badge'>{row['Meeting']}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── 1. Scores table ───────────────────────────────────────────────────────
    st.markdown("### 📋 Scores")

    hw_cols = ["HW01", "HW02", "HW03", "HW04", "HW05"]
    grade_data = {
        "Item":  ["Midterm"] + hw_cols + ["HW-Song-extra"],
        "Score": [row["Midterm"]] + [row[h] for h in hw_cols] + [f"{pd.to_numeric(row['HW-Song-extra'], errors='coerce'):.1f}"],
    }
    grade_df = pd.DataFrame(grade_data)

    def style_grade(v):
        if v == "Completed":
            return "background-color:#d4edda; color:#155724; font-weight:500;"
        elif isinstance(v, str) and v != "Completed":
            return "background-color:#f8d7da; color:#721c24;"
        return ""

    styled = (
        grade_df.style
        .map(style_grade, subset=["Score"])
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
        st.info("⏳ Pronunciation assessment data for this student has not been entered yet (scheduled for a later session).")
    else:
        # ── 2. Feature heatmaps ──────────────────────────────────────────────
        def draw_heatmap(title, cols, row_data, emoji):
            st.markdown(f"### {emoji} {title}")
            labels_list = [c.split("-", 1)[1] for c in cols]
            values      = [str(row_data[c]).strip() for c in cols]
            colors      = [rating_color(v) for v in values]
            txt_colors  = [text_color(c) for c in colors]

            cell_w = 1.35
            fig, ax = plt.subplots(figsize=(len(cols) * cell_w, 1.6))
            fig.patch.set_facecolor("#f7f5f2")
            ax.set_facecolor("#f7f5f2")

            for i, (lbl, val, bg, tc) in enumerate(zip(labels_list, values, colors, txt_colors)):
                rect = mpatches.FancyBboxPatch(
                    (i, 0), 0.88, 0.78,
                    boxstyle="round,pad=0.05",
                    linewidth=0, facecolor=bg,
                )
                ax.add_patch(rect)
                ax.text(i + 0.44, 0.6,  val, ha="center", va="center",
                        fontsize=13, fontweight="bold", color="#ffffff")
                lbl_color = "#ffdd57" if text_color(bg) == "#ffffff" else "#444444"
                ax.text(i + 0.44, 0.18, lbl, ha="center", va="center",
                        fontsize=7.5, color=lbl_color, fontweight="600")

            ax.set_xlim(-0.1, len(cols))
            ax.set_ylim(-0.05, 0.9)
            ax.axis("off")
            plt.tight_layout(pad=0.2)
            col_fig, _ = st.columns([len(cols), max(1, 8 - len(cols))])
            with col_fig:
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
            legend_html += "&nbsp;<span style='font-size:0.75rem; color:#888;'>L = Low &nbsp;|&nbsp; ML = Mid-Low &nbsp;|&nbsp; M = Mid &nbsp;|&nbsp; MH = Mid-High &nbsp;|&nbsp; H = High</span>"
            legend_html += "</div>"
            st.markdown(legend_html, unsafe_allow_html=True)

        draw_heatmap("Vowels", V_COLS, row, "🔆")
        draw_heatmap("Consonants", C_COLS, row, "🔆")
        draw_heatmap("Prosody", P_COLS, row, "🔆")

        st.markdown("---")

        # ── 3. Notes ──────────────────────────────────────────────────────────
        st.markdown("### 📝 Instructor Notes")
        notes_text = str(row["Notes"]).strip() if pd.notna(row["Notes"]) and str(row["Notes"]).strip() not in ("", "Later") else ""
        if notes_text:
            st.markdown(f"<div class='notes-box'>{notes_text}</div>", unsafe_allow_html=True)
        else:
            st.markdown("_No notes recorded._")

        st.markdown("---")

        # ── 4. Radar chart ─────────────────────────────────────────────────────
        st.markdown("### 🍃 Overall Pronunciation Profile")

        acc   = float(row["Accuracy"])
        flu   = float(row["Fluency"])
        intel = float(row["Intelligibility"])

        if acc == 0 and flu == 0 and intel == 0:
            st.info("⏳ Assessment scores have not been entered yet.")
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
