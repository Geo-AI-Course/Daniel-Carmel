"""
EDA Streamlit App – Bantal vs. OSM
Simple enough for a 5-year-old  🎈
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import warnings
warnings.filterwarnings("ignore")

# ─── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="🏠 מי יודע יותר על הבתים?",
    page_icon="🏠",
    layout="wide",
)

# RTL + fun style
st.markdown("""
<style>
    html, body, [class*="css"] { direction: rtl; }
    h1, h2, h3, h4, p, li { direction: rtl; text-align: right; }
    .stMetric { background: #f8f9fa; border-radius: 12px; padding: 8px; }
    .fun-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; border-radius: 16px; padding: 20px;
        text-align: center; margin: 8px 0;
    }
    .green-box {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white; border-radius: 16px; padding: 20px;
        text-align: center; margin: 8px 0;
    }
    .orange-box {
        background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);
        color: white; border-radius: 16px; padding: 20px;
        text-align: center; margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)


# ─── Data loading ───────────────────────────────────────────────
DATA = "."

@st.cache_data(show_spinner="🔄 טוען נתונים...")
def load_all():
    bldg_b  = pd.read_csv(f"{DATA}/BANTAL_BLDG.csv",      encoding="cp1255")
    addr_b  = pd.read_csv(f"{DATA}/BANTAL_ADDR.csv",      encoding="cp1255")
    bldg_o  = pd.read_csv(f"{DATA}/OSM_BLDG.csv",         encoding="cp1255")
    addr_o  = pd.read_csv(f"{DATA}/OSM_ADDR.csv",         encoding="cp1255")
    setel   = pd.read_csv(f"{DATA}/SETEL.csv",            encoding="cp1255")
    streets = pd.read_csv(f"{DATA}/TOPO_STREET_NAME.csv", encoding="cp1255")
    setnames= pd.read_csv(f"{DATA}/TOPO_SETEL_NAME.csv",  encoding="cp1255")
    return bldg_b, addr_b, bldg_o, addr_o, setel, streets, setnames

bldg_b, addr_b, bldg_o, addr_o, setel, streets, setnames = load_all()

# ─── Lookup maps ────────────────────────────────────────────────
FTYPE_MAP = {
    11: ("🏠", "בניין רגיל"),
    12: ("🏚️", "חורבה"),
    13: ("🚧", "בנייה"),
    14: ("🌾", "מבנה חקלאי"),
    15: ("🏭", "תעשייה"),
    16: ("📦", "מחסן / צריף"),
    17: ("🪖", "ביטחוני"),
    18: ("🏫", "מבנה ציבורי"),
    31: ("⛪", "מבנה דתי"),
    32: ("🏛️", "מיוחד"),
}

OSM_MAP = {
    "yes":              ("🏠", "בניין"),
    "apartments":       ("🏢", "דירות"),
    "house":            ("🏡", "בית פרטי"),
    "detached":         ("🏡", "וילה"),
    "residential":      ("🏘️", "מגורים"),
    "school":           ("🏫", "בית ספר"),
    "semidetached_house":("🏘️","צמוד קרקע"),
    "kindergarten":     ("🧒", "גן ילדים"),
    "retail":           ("🛒", "חנות"),
    "dormitory":        ("🛏️", "מעונות"),
    "university":       ("🎓", "אוניברסיטה"),
    "commercial":       ("🏪", "מסחרי"),
    "industrial":       ("🏭", "תעשייה"),
    "roof":             ("🏠", "גג"),
    "office":           ("💼", "משרד"),
}

def ftype_label(v):
    emoji, name = FTYPE_MAP.get(v, ("❓", "אחר"))
    return f"{emoji} {name}"

def osm_label(v):
    if pd.isna(v):
        return "❓ לא ידוע"
    emoji, name = OSM_MAP.get(v, ("❓", "אחר"))
    return f"{emoji} {name}"


# ═══════════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════════
st.title("🌍 מי יודע יותר על הבתים שלנו?")
st.markdown("""
### שתי מפות מתחרות 🥊

| 🏛️ **בנטל** | 🌍 **OpenStreetMap (OSM)** |
|---|---|
| המפה **הרשמית** של מדינת ישראל | המפה **של כולם** – מתנדבים ממפים בית אחרי בית |
| מצייר אותה **מפ"י** (מרכז המיפוי) | כל אחד יכול **לעדכן** אותה |
| **סודית חלקית** ✋ | **חינמית לחלוטין** 🆓 |
""")
st.divider()


# ═══════════════════════════════════════════════════════════════
#  BIG KPI CARDS
# ═══════════════════════════════════════════════════════════════
st.markdown("## 📊 כמה דברים יש בכל מפה?")

c1, c2, c3, c4 = st.columns(4)
c1.metric("🏠 בתים בבנטל",    f"{len(bldg_b):,}",  delta=None)
c2.metric("🗺️ בתים ב-OSM",   f"{len(bldg_o):,}",  delta=f"{len(bldg_b)-len(bldg_o):+,} לבנטל")
c3.metric("📍 כתובות בבנטל", f"{len(addr_b):,}",  delta=None)
c4.metric("📮 כתובות ב-OSM",  f"{len(addr_o):,}",  delta=f"{len(addr_b)-len(addr_o):+,} לבנטל")

# Fun facts row
f1, f2, f3 = st.columns(3)
with f1:
    st.markdown(f"""
    <div class="fun-box">
        <h2>🏙️ {len(setel)}</h2>
        <p><strong>ישובים</strong> באזור הפיילוט</p>
    </div>""", unsafe_allow_html=True)
with f2:
    st.markdown(f"""
    <div class="green-box">
        <h2>🛣️ {len(streets):,}</h2>
        <p><strong>שמות רחובות</strong> במאגר</p>
    </div>""", unsafe_allow_html=True)
with f3:
    coverage = len(bldg_o) / len(bldg_b) * 100
    st.markdown(f"""
    <div class="orange-box">
        <h2>📐 {coverage:.0f}%</h2>
        <p><strong>כיסוי OSM</strong> מתוך בנטל בבניינים</p>
    </div>""", unsafe_allow_html=True)

st.divider()


# ═══════════════════════════════════════════════════════════════
#  TABS
# ═══════════════════════════════════════════════════════════════
t1, t2, t3, t4, t5, t6, t7 = st.tabs([
    "🏗️ סוגי בתים",
    "🏙️ ישובים",
    "📍 כתובות",
    "🔍 השוואה",
    "🗃️ טבלאות גולמיות",
    "🔄 דלתאות",
    "🤖 חיזוי סיכון",
])


# ──────────────────────────────────────────────────────────────
# TAB 1 – BUILDING TYPES
# ──────────────────────────────────────────────────────────────
with t1:
    st.markdown("## 🏗️ מה סוגי הבתים?")
    st.markdown("כמו שיש **עוגיות** מסוגים שונים 🍪🎂🧁 – גם בתים באים בהמון צורות!")

    col_l, col_r = st.columns(2)

    # ── Bantal ──
    with col_l:
        st.subheader("🏛️ בנטל – המפה הרשמית")
        bldg_b["label"] = bldg_b["FTYPE"].map(ftype_label)
        cnt_b = bldg_b["label"].value_counts().reset_index()
        cnt_b.columns = ["סוג בניין", "כמות"]

        fig = px.bar(
            cnt_b,
            x="כמות", y="סוג בניין",
            orientation="h",
            color="כמות",
            color_continuous_scale="Viridis",
            title=f"בנטל – {len(bldg_b):,} בניינים",
            text="כמות",
        )
        fig.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig.update_layout(showlegend=False,
                          yaxis={"categoryorder": "total ascending"},
                          xaxis_title="מספר בניינים")
        st.plotly_chart(fig, use_container_width=True)

        top_b = cnt_b.iloc[0]
        st.success(f"🏆 הכי נפוץ בבנטל: **{top_b['סוג בניין']}** — {top_b['כמות']:,} פעמים!")

    # ── OSM ──
    with col_r:
        st.subheader("🌍 OSM – המפה של כולנו")
        bldg_o["label"] = bldg_o["building"].map(osm_label)
        cnt_o = bldg_o["label"].value_counts().head(12).reset_index()
        cnt_o.columns = ["סוג בניין", "כמות"]

        fig2 = px.pie(
            cnt_o, values="כמות", names="סוג בניין",
            title=f"OSM – {len(bldg_o):,} בניינים",
            color_discrete_sequence=px.colors.qualitative.Set3,
            hole=0.35,
        )
        fig2.update_traces(textinfo="percent+label")
        st.plotly_chart(fig2, use_container_width=True)

        top_o = cnt_o.iloc[0]
        st.success(f"🏆 הכי נפוץ ב-OSM: **{top_o['סוג בניין']}** — {top_o['כמות']:,} פעמים!")

    # Treemap side-by-side
    st.markdown("---")
    st.markdown("### 🌳 עץ גדול של כל הבתים")
    tc1, tc2 = st.columns(2)
    with tc1:
        fig_tree_b = px.treemap(cnt_b, path=["סוג בניין"], values="כמות",
                                title="בנטל – עץ בניינים",
                                color="כמות", color_continuous_scale="Blues")
        st.plotly_chart(fig_tree_b, use_container_width=True)
    with tc2:
        fig_tree_o = px.treemap(cnt_o, path=["סוג בניין"], values="כמות",
                                title="OSM – עץ בניינים",
                                color="כמות", color_continuous_scale="Greens")
        st.plotly_chart(fig_tree_o, use_container_width=True)


# ──────────────────────────────────────────────────────────────
# TAB 2 – SETTLEMENTS
# ──────────────────────────────────────────────────────────────
with t2:
    st.markdown("## 🏙️ הישובים שלנו")
    st.markdown("כמו שיש **שכונות** שונות בעיר – יש לנו ישובים שונים במפה!")

    # Settlement sizes
    setel_disp = setel[["Muni_Eng", "Muni_Heb", "Sug_Muni", "AreaSQM"]].copy()
    setel_disp.columns = ["שם באנגלית", "שם בעברית", "סוג", "שטח (מ\"ר)"]
    setel_disp["שטח (קמ\"ר)"] = (setel_disp["שטח (מ\"ר)"] / 1_000_000).round(3)
    setel_disp["שטח (דונם)"] = (setel_disp["שטח (מ\"ר)"] / 1_000).round(1)
    setel_disp = setel_disp.sort_values("שטח (דונם)", ascending=False)

    s1, s2 = st.columns(2)
    with s1:
        fig_area = px.bar(
            setel_disp,
            x="שם באנגלית", y="שטח (דונם)",
            color="שטח (דונם)",
            color_continuous_scale="Blues",
            title="🗺️ כמה גדול כל ישוב? (דונם)",
            text="שטח (דונם)",
        )
        fig_area.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig_area.update_layout(xaxis_tickangle=40, showlegend=False)
        st.plotly_chart(fig_area, use_container_width=True)

        biggest = setel_disp.iloc[0]
        st.info(f"🏆 הכי גדול: **{biggest['שם באנגלית']}** – {biggest['שטח (דונם)']:,.0f} דונם!")

    with s2:
        # addresses per settlement
        addr_merged = addr_b.merge(
            setnames[["SETL_CODE", "SETL_NAME"]],
            on="SETL_CODE", how="left"
        )
        addr_per = addr_merged["SETL_NAME"].value_counts().head(10).reset_index()
        addr_per.columns = ["ישוב", "מספר כתובות"]

        fig_setl = px.bar(
            addr_per,
            x="מספר כתובות", y="ישוב",
            orientation="h",
            color="מספר כתובות",
            color_continuous_scale="Oranges",
            title="📍 כמה כתובות יש בכל ישוב? (TOP 10)",
            text="מספר כתובות",
        )
        fig_setl.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig_setl.update_layout(yaxis={"categoryorder": "total ascending"},
                               showlegend=False, xaxis_title="מספר כתובות")
        st.plotly_chart(fig_setl, use_container_width=True)

    # Settlement type breakdown
    st.markdown("---")
    st.markdown("### 🏛️ סוגי ישובים")
    sug_cnt = setel["Sug_Muni"].value_counts().reset_index()
    sug_cnt.columns = ["סוג ישוב", "כמות"]
    fig_sug = px.pie(sug_cnt, names="סוג ישוב", values="כמות",
                     title="סוגי הישובים באזור הפיילוט",
                     color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_sug.update_traces(textinfo="percent+label")
    st.plotly_chart(fig_sug, use_container_width=True)


# ──────────────────────────────────────────────────────────────
# TAB 3 – ADDRESSES
# ──────────────────────────────────────────────────────────────
with t3:
    st.markdown("## 📍 עולם הכתובות")
    st.markdown("כתובת היא כמו **כתובת גנוז** – יסייע לדואר למצוא אתכם! 📬")

    a1, a2 = st.columns(2)

    # House number distribution
    with a1:
        st.subheader("🔢 מספרי בתים – כמה גבוה?")
        hn = addr_b["HOUSE_NUM"].dropna()
        hn_clip = hn[hn <= 200]

        fig_hn = px.histogram(
            hn_clip, nbins=50,
            title=f"פיזור מספרי בתים (עד 200) – {len(hn):,} כתובות",
            color_discrete_sequence=["#FF6B6B"],
            labels={"value": "מספר בית", "count": "כמות"},
        )
        fig_hn.update_layout(xaxis_title="מספר בית", yaxis_title="כמות כתובות",
                             bargap=0.05)
        st.plotly_chart(fig_hn, use_container_width=True)

        st.info(f"""
        📊 מספר הבית **הממוצע**: {hn.mean():.0f}
        📈 הכי **גבוה**: {hn.max():.0f}
        📉 הכי **נמוך**: {hn.min():.0f}
        """)

    # Entry letters
    with a2:
        st.subheader("🚪 אותיות כניסה – איזו כניסה הכי נפוצה?")
        entry = addr_b["ENTRY_LETR"].dropna()
        entry_cnt = entry.value_counts().head(10).reset_index()
        entry_cnt.columns = ["אות כניסה", "כמות"]

        fig_entry = px.bar(
            entry_cnt,
            x="אות כניסה", y="כמות",
            color="כמות",
            color_continuous_scale="Greens",
            title=f"אותיות כניסה – {len(entry):,} כתובות עם כניסה",
            text="כמות",
        )
        fig_entry.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig_entry.update_layout(showlegend=False)
        st.plotly_chart(fig_entry, use_container_width=True)

        top_e = entry_cnt.iloc[0]
        st.info(f"🏆 כניסה **{top_e['אות כניסה']}** הכי נפוצה – {top_e['כמות']:,} פעמים!")

    # streets stats
    st.markdown("---")
    st.subheader("🛣️ כמה רחובות יש?")
    streets_per_setl = streets.groupby("SETL_CODE").size().reset_index(name="מספר רחובות")
    streets_merged = streets_per_setl.merge(
        setnames[["SETL_CODE", "SETL_NAME"]], on="SETL_CODE", how="left"
    )
    streets_merged = streets_merged.dropna(subset=["SETL_NAME"])
    streets_top = streets_merged.nlargest(15, "מספר רחובות")

    fig_str = px.bar(
        streets_top,
        x="מספר רחובות", y="SETL_NAME",
        orientation="h",
        color="מספר רחובות",
        color_continuous_scale="Purples",
        title="🛣️ ישובים עם הכי הרבה רחובות (TOP 15)",
        text="מספר רחובות",
    )
    fig_str.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig_str.update_layout(yaxis={"categoryorder": "total ascending"},
                          showlegend=False, xaxis_title="מספר רחובות",
                          yaxis_title="ישוב")
    st.plotly_chart(fig_str, use_container_width=True)


# ──────────────────────────────────────────────────────────────
# TAB 4 – COMPARISON
# ──────────────────────────────────────────────────────────────
with t4:
    st.markdown("## 🔍 בנטל מול OSM – מי מנצח?")
    st.markdown("נדמיין שבנטל ו-OSM שני ילדים שמנסים לאסוף הכי הרבה **כרטיסי פוקמון** 🃏")

    c1, c2, c3 = st.columns([1.2, 1.2, 1])

    # Buildings comparison
    with c1:
        fig_b = go.Figure(go.Bar(
            x=["🏛️ בנטל", "🌍 OSM"],
            y=[len(bldg_b), len(bldg_o)],
            marker_color=["#6C5CE7", "#00B894"],
            text=[f"{len(bldg_b):,}", f"{len(bldg_o):,}"],
            textposition="outside",
            textfont_size=16,
        ))
        fig_b.update_layout(
            title="🏠 כמה בתים יודע כל אחד?",
            yaxis_title="מספר בניינים",
            yaxis_range=[0, max(len(bldg_b), len(bldg_o)) * 1.2],
        )
        st.plotly_chart(fig_b, use_container_width=True)

    # Addresses comparison
    with c2:
        fig_a = go.Figure(go.Bar(
            x=["🏛️ בנטל", "🌍 OSM"],
            y=[len(addr_b), len(addr_o)],
            marker_color=["#FDCB6E", "#0984E3"],
            text=[f"{len(addr_b):,}", f"{len(addr_o):,}"],
            textposition="outside",
            textfont_size=16,
        ))
        fig_a.update_layout(
            title="📍 כמה כתובות יודע כל אחד?",
            yaxis_title="מספר כתובות",
            yaxis_range=[0, max(len(addr_b), len(addr_o)) * 1.2],
        )
        st.plotly_chart(fig_a, use_container_width=True)

    # Verdict
    with c3:
        st.markdown("### 🏆 הכרעת השופטים")
        bldg_diff = len(bldg_b) - len(bldg_o)
        addr_diff = len(addr_b) - len(addr_o)
        coverage  = len(bldg_o) / len(bldg_b) * 100

        if bldg_diff > 0:
            st.success(f"🏛️ בנטל מכיר **{bldg_diff:,}** בתים **יותר** מ-OSM")
        else:
            st.success(f"🌍 OSM מכיר **{abs(bldg_diff):,}** בתים **יותר** מבנטל")

        if addr_diff > 0:
            st.info(f"📮 בנטל מכיר **{addr_diff:,}** כתובות **יותר** מ-OSM")
        else:
            st.info(f"📮 OSM מכיר **{abs(addr_diff):,}** כתובות **יותר** מבנטל")

        st.metric("📐 כיסוי OSM מבנטל (בניינים)", f"{coverage:.1f}%")
        if coverage > 60:
            st.balloons()
            st.success("🎉 WOW! OSM מכסה יותר מ-60% מהבתים של בנטל!")

    # Gauge chart for coverage
    st.markdown("---")
    st.markdown("### 🎯 מד הכיסוי של OSM")
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=coverage,
        number={"suffix": "%"},
        delta={"reference": 100, "valueformat": ".1f"},
        title={"text": "כמה אחוז מהבניינים של בנטל קיימים גם ב-OSM?"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#00B894"},
            "steps": [
                {"range": [0, 40],  "color": "#FF7675"},
                {"range": [40, 70], "color": "#FDCB6E"},
                {"range": [70, 100],"color": "#55EFC4"},
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": 100,
            },
        },
    ))
    fig_gauge.update_layout(height=300)
    st.plotly_chart(fig_gauge, use_container_width=True)

    # Fun summary table
    st.markdown("---")
    st.markdown("### 📋 טבלת סיכום")
    summary = pd.DataFrame({
        "נושא": ["🏠 בניינים", "📍 כתובות", "🛣️ רחובות", "🏙️ ישובים"],
        "🏛️ בנטל": [f"{len(bldg_b):,}", f"{len(addr_b):,}", f"{len(streets):,}", f"{len(setel)}"],
        "🌍 OSM":   [f"{len(bldg_o):,}", f"{len(addr_o):,}", "—", "—"],
        "הפרש":    [
            f"{bldg_diff:+,}",
            f"{addr_diff:+,}",
            "—", "—",
        ],
    })
    st.dataframe(summary, use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────────────────────
# TAB 5 – RAW TABLES
# ──────────────────────────────────────────────────────────────
with t5:
    st.markdown("## 🗃️ הנתונים הגולמיים")
    st.markdown("כאן אפשר לראות את הטבלאות כמו שהן – כמו לפתוח את הגנוז! 📂")

    dataset = st.selectbox("בחר טבלה", [
        "🏛️ בנטל – בניינים",
        "📍 בנטל – כתובות",
        "🌍 OSM – בניינים",
        "📮 OSM – כתובות",
        "🏙️ ישובים (SETEL)",
        "🛣️ שמות רחובות (דוגמה)",
    ])

    if dataset == "🏛️ בנטל – בניינים":
        df_show = bldg_b.drop(columns=["WKT"], errors="ignore")
        df_show["סוג בניין"] = bldg_b["FTYPE"].map(ftype_label)
        st.dataframe(df_show, use_container_width=True, height=400)
    elif dataset == "📍 בנטל – כתובות":
        df_show = addr_b.drop(columns=["WKT"], errors="ignore")
        st.dataframe(df_show, use_container_width=True, height=400)
    elif dataset == "🌍 OSM – בניינים":
        df_show = bldg_o.drop(columns=["WKT"], errors="ignore")
        df_show["סוג בניין"] = bldg_o["building"].map(osm_label)
        st.dataframe(df_show, use_container_width=True, height=400)
    elif dataset == "📮 OSM – כתובות":
        df_show = addr_o.drop(columns=["WKT"], errors="ignore")
        st.dataframe(df_show, use_container_width=True, height=400)
    elif dataset == "🏙️ ישובים (SETEL)":
        df_show = setel.drop(columns=["WKT"], errors="ignore")
        st.dataframe(df_show, use_container_width=True, height=400)
    elif dataset == "🛣️ שמות רחובות (דוגמה)":
        st.dataframe(streets.head(200), use_container_width=True, height=400)
        st.caption(f"מציג 200 מתוך {len(streets):,} רחובות")

    # Download button
    csv_map = {
        "🏛️ בנטל – בניינים":    bldg_b.drop(columns=["WKT"], errors="ignore"),
        "📍 בנטל – כתובות":      addr_b.drop(columns=["WKT"], errors="ignore"),
        "🌍 OSM – בניינים":      bldg_o.drop(columns=["WKT"], errors="ignore"),
        "📮 OSM – כתובות":       addr_o.drop(columns=["WKT"], errors="ignore"),
        "🏙️ ישובים (SETEL)":     setel.drop(columns=["WKT"], errors="ignore"),
        "🛣️ שמות רחובות (דוגמה)":streets.head(200),
    }
    st.download_button(
        "⬇️ הורד כ-CSV",
        data=csv_map[dataset].to_csv(index=False, encoding="utf-8-sig"),
        file_name=f"{dataset.split(' – ')[-1].strip()}.csv",
        mime="text/csv",
    )


# ──────────────────────────────────────────────────────────────
# TAB 6 – DELTA RESULTS
# ──────────────────────────────────────────────────────────────
DELTA_SUMMARY_PATH  = "output/delta_summary.csv"
DELTA_BLDG_PATH     = "output/delta_buildings.csv"
DELTA_ADDR_PATH     = "output/delta_addresses.csv"

with t6:
    st.markdown("## 🔄 תוצאות הדלתאות")

    if not __import__("os").path.exists(DELTA_SUMMARY_PATH):
        st.warning("⚠️ קבצי דלתאות לא נמצאו. הרץ קודם: `python delta_engine.py`")
    else:
        @st.cache_data(show_spinner="טוען תוצאות דלתאות...")
        def load_delta_data():
            ds = pd.read_csv(DELTA_SUMMARY_PATH,  encoding="utf-8-sig")
            db = pd.read_csv(DELTA_BLDG_PATH,     encoding="utf-8-sig") if __import__("os").path.exists(DELTA_BLDG_PATH) else pd.DataFrame()
            da = pd.read_csv(DELTA_ADDR_PATH,     encoding="utf-8-sig") if __import__("os").path.exists(DELTA_ADDR_PATH) else pd.DataFrame()
            return ds, db, da

        ds, db, da = load_delta_data()

        # KPI row
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("🆕 מבנים חדשים ב-OSM",       f"{int(ds['n_new_bldg'].sum()):,}")
        d2.metric("🏚️ מבנים חסרים ב-OSM",       f"{int(ds['n_missing_bldg'].sum()):,}")
        d3.metric("📌 כתובות חסרות בבנטל",       f"{int(ds['n_missing_bantal_addr'].sum()):,}")
        d4.metric("⚡ קונפליקטים מרחביים",         f"{int(ds['n_spatial_mismatch'].sum()):,}")

        st.divider()

        # Delta score per settlement
        st.markdown("### 🎯 ציון דלתא לפי ישוב")
        fig_score = px.bar(
            ds.sort_values("delta_score", ascending=True),
            x="delta_score", y="Muni_Eng",
            orientation="h",
            color="delta_score",
            color_continuous_scale="Reds",
            text="delta_score",
            title="ציון דלתא (גבוה = יותר פערים)",
        )
        fig_score.update_traces(texttemplate="%{text:.3f}", textposition="outside")
        fig_score.update_layout(showlegend=False, xaxis_title="ציון דלתא", yaxis_title="ישוב")
        st.plotly_chart(fig_score, use_container_width=True)

        # Building delta breakdown
        st.markdown("### 🏗️ פירוט דלתאות מבנים לפי ישוב")
        bldg_cols = ["Muni_Eng", "total_bantal_bldg", "total_osm_bldg",
                     "n_new_bldg", "n_missing_bldg", "osm_coverage_pct"]
        st.dataframe(
            ds[bldg_cols].rename(columns={
                "Muni_Eng": "ישוב", "total_bantal_bldg": "בנטל",
                "total_osm_bldg": "OSM", "n_new_bldg": "חדש ב-OSM",
                "n_missing_bldg": "חסר ב-OSM", "osm_coverage_pct": "כיסוי %",
            }),
            use_container_width=True, hide_index=True,
        )

        # Address delta breakdown pie
        st.markdown("### 📍 התפלגות דלתאות כתובות")
        if not da.empty:
            addr_counts = da["delta_type"].value_counts().reset_index()
            addr_counts.columns = ["סוג דלתא", "כמות"]
            delta_labels = {
                "FULL_MATCH":        "✅ התאמה מלאה",
                "SPATIAL_MISMATCH":  "⚠️ קונפליקט מרחבי",
                "MISSING_IN_BANTAL": "➕ חסר בבנטל",
                "MISSING_IN_OSM":    "➖ חסר ב-OSM",
            }
            addr_counts["סוג דלתא"] = addr_counts["סוג דלתא"].map(delta_labels).fillna(addr_counts["סוג דלתא"])

            col_pie, col_tbl = st.columns([1, 1])
            with col_pie:
                fig_addr_pie = px.pie(
                    addr_counts, values="כמות", names="סוג דלתא",
                    title="סוגי דלתאות כתובות",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    hole=0.35,
                )
                fig_addr_pie.update_traces(textinfo="percent+label")
                st.plotly_chart(fig_addr_pie, use_container_width=True)
            with col_tbl:
                st.dataframe(addr_counts, use_container_width=True, hide_index=True)

        # Drilldown by settlement
        st.markdown("### 🔎 פירוט לפי ישוב")
        settlements = ["הכל"] + sorted(ds["Muni_Eng"].dropna().tolist())
        sel_setl = st.selectbox("בחר ישוב לפירוט", settlements, key="delta_setl_sel")

        if sel_setl != "הכל":
            setl_code_sel = ds[ds["Muni_Eng"] == sel_setl]["setl_code"].iloc[0]
            if not db.empty:
                db_filt = db[db["setl_code"] == setl_code_sel]
                st.markdown(f"**מבנים — {sel_setl}** ({len(db_filt)} דלתאות)")
                st.dataframe(db_filt.drop(columns=["geometry_wkt"], errors="ignore"),
                             use_container_width=True, height=300)
            if not da.empty:
                da_filt = da[pd.to_numeric(da["setl_code"], errors="coerce") == setl_code_sel]
                st.markdown(f"**כתובות — {sel_setl}** ({len(da_filt)} דלתאות)")
                st.dataframe(da_filt, use_container_width=True, height=300)
        else:
            if not db.empty:
                st.dataframe(db.drop(columns=["geometry_wkt"], errors="ignore"),
                             use_container_width=True, height=300)

        # Download buttons
        st.markdown("---")
        dl1, dl2, dl3 = st.columns(3)
        with dl1:
            st.download_button("⬇️ סיכום דלתאות",
                               ds.to_csv(index=False, encoding="utf-8-sig"),
                               "delta_summary.csv", mime="text/csv")
        with dl2:
            if not db.empty:
                st.download_button("⬇️ דלתאות מבנים",
                                   db.drop(columns=["geometry_wkt"], errors="ignore")
                                     .to_csv(index=False, encoding="utf-8-sig"),
                                   "delta_buildings.csv", mime="text/csv")
        with dl3:
            if not da.empty:
                st.download_button("⬇️ דלתאות כתובות",
                                   da.to_csv(index=False, encoding="utf-8-sig"),
                                   "delta_addresses.csv", mime="text/csv")


# ──────────────────────────────────────────────────────────────
# TAB 7 – ML RISK PREDICTION
# ──────────────────────────────────────────────────────────────
ML_PRED_PATH = "output/ml_predictions.csv"
ML_COEF_PATH = "output/ml_feature_importance.csv"

SETTLE_TYPE_MAP = {
    1: "עיר / מועצה מקומית",
    2: "מועצה אזורית",
    3: "כפר / יישוב קטן",
    4: "קיבוץ / מושב",
}

RELIGION_MAP = {
    1: "🟡 יהודי",
    2: "🟢 מעורב",
    3: "🔵 ערבי / בדואי",
}

with t7:
    st.markdown("## 🤖 חיזוי רמת סיכון לדלתאות")
    st.markdown(
        "המודל אומן על 11 ישובי הפיילוט ומחזה רמת סיכון לדלתאות לכל ~2,000 ישובי ישראל "
        "על בסיס אוכלוסייה, סוג ישוב ודת."
    )

    if not __import__("os").path.exists(ML_PRED_PATH):
        st.warning("⚠️ קובץ חיזויים לא נמצא. הרץ קודם: `python delta_engine.py` ואז `python ml_risk.py`")
    else:
        @st.cache_data(show_spinner="טוען חיזויים...")
        def load_ml_data():
            pred = pd.read_csv(ML_PRED_PATH, encoding="utf-8-sig")
            coef = pd.read_csv(ML_COEF_PATH, encoding="utf-8-sig") if __import__("os").path.exists(ML_COEF_PATH) else pd.DataFrame()
            return pred, coef

        pred, coef = load_ml_data()

        pred["religion_label"]   = pred["religion_type"].map(RELIGION_MAP).fillna("❓ לא ידוע")
        pred["population_2024"]  = pd.to_numeric(pred["population_2024"], errors="coerce")

        # KPIs
        m1, m2, m3 = st.columns(3)
        m1.metric("🏙️ ישובים בחיזוי",   f"{len(pred):,}")
        m2.metric("⚠️ ישובי סיכון גבוה (>70)", f"{(pred['risk_score_100'] > 70).sum():,}")
        m3.metric("📊 ישובי פיילוט", f"{pred['is_pilot'].sum()}")

        st.divider()

        # Top-N bar chart
        st.markdown("### 🏆 ישובים בסיכון הגבוה ביותר")
        n_top = st.slider("כמה ישובים להציג", 10, 50, 30, key="ml_top_n")
        top_df = pred.head(n_top).copy()
        top_df["label"] = top_df["setl_name"].fillna("?") + " " + top_df["religion_label"].fillna("")

        fig_top = px.bar(
            top_df[::-1],
            x="risk_score_100", y="label",
            orientation="h",
            color="religion_label",
            color_discrete_map={
                "🟡 יהודי": "#FFD93D",
                "🟢 מעורב": "#6BCB77",
                "🔵 ערבי / בדואי": "#4D96FF",
                "❓ לא ידוע": "#CCCCCC",
            },
            text="risk_score_100",
            title=f"TOP {n_top} ישובים — ציון סיכון (0–100)",
        )
        fig_top.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig_top.update_layout(
            xaxis_title="ציון סיכון", yaxis_title="",
            legend_title="סוג דת", height=max(400, n_top * 20),
        )
        st.plotly_chart(fig_top, use_container_width=True)

        # Scatter: population vs risk
        st.markdown("### 📊 אוכלוסייה מול ציון סיכון")
        fig_scatter = px.scatter(
            pred.dropna(subset=["population_2024"]),
            x="population_2024",
            y="risk_score_100",
            color="religion_label",
            size="risk_score_100",
            size_max=20,
            hover_name="setl_name",
            hover_data={"population_2024": ":,", "risk_score_100": ":.1f"},
            log_x=True,
            color_discrete_map={
                "🟡 יהודי": "#FFD93D",
                "🟢 מעורב": "#6BCB77",
                "🔵 ערבי / בדואי": "#4D96FF",
                "❓ לא ידוע": "#CCCCCC",
            },
            symbol="is_pilot",
            symbol_map={True: "star", False: "circle"},
            title="גודל אוכלוסייה (log) מול ציון סיכון — ⭐ = ישוב פיילוט",
        )
        fig_scatter.update_layout(xaxis_title="אוכלוסייה (log)", yaxis_title="ציון סיכון")
        st.plotly_chart(fig_scatter, use_container_width=True)

        # Feature importance
        if not coef.empty:
            st.markdown("### 🔬 חשיבות הפיצ'רים במודל")
            coef_sorted = coef.sort_values("coefficient", key=abs, ascending=True)
            fig_coef = px.bar(
                coef_sorted,
                x="coefficient", y="feature",
                orientation="h",
                color="coefficient",
                color_continuous_scale="RdBu",
                color_continuous_midpoint=0,
                title="מקדמי הרגרסיה (חיובי = מגדיל סיכון)",
            )
            fig_coef.update_layout(showlegend=False, xaxis_title="מקדם", yaxis_title="פיצ'ר")
            st.plotly_chart(fig_coef, use_container_width=True)

        # Pilot comparison table
        st.markdown("### 🏙️ ישובי פיילוט — ממשי מול חזוי")
        pilot_compare = pred[pred["is_pilot"]].copy()
        pilot_compare = pilot_compare.sort_values("actual_delta_score", ascending=False)
        st.dataframe(
            pilot_compare[["setl_name", "population_2024", "religion_label",
                           "actual_delta_score", "risk_score_100", "risk_rank"]]
            .rename(columns={
                "setl_name": "ישוב", "population_2024": "אוכלוסייה",
                "religion_label": "דת", "actual_delta_score": "ציון ממשי",
                "risk_score_100": "ציון חזוי", "risk_rank": "דירוג כלל-ארצי",
            }),
            use_container_width=True, hide_index=True,
        )

        # Download
        st.markdown("---")
        st.download_button(
            "⬇️ הורד טבלת חיזויים מלאה",
            pred.to_csv(index=False, encoding="utf-8-sig"),
            "ml_predictions.csv", mime="text/csv",
        )


# ─── Footer ────────────────────────────────────────────────────
st.divider()
st.caption(
    "📊 הנתונים: בנטל / מפ\"י (רשמי) + OpenStreetMap (מתנדבים)  |  "
    "🤖 נבנה ע\"י Claude Code  |  "
    "🗓️ פיילוט 2 – אזורים: כפר מרדכי + צפון תל-אביב"
)
