import streamlit as st
from calculator import (
    calc_bmi, bmi_label, calc_bmr, calc_tdee,
    adjust_tdee, calc_meal_targets,
)
from recommender import recommend_day

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Hôm nay ăn gì?", page_icon="🍚", layout="centered")

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #f5f5f5; }
[data-testid="stMain"] > div { padding-top: 1rem; }
section[data-testid="stSidebar"] { background: #fff; }
.block-container {
    max-width: 430px !important;
    padding: 0 1rem 2rem !important;
    margin: 0 auto !important;
}
.app-header {
    background: #fff;
    border-radius: 0 0 20px 20px;
    padding: 1rem 1.25rem 1.25rem;
    margin: -1rem -1rem 1.25rem -1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    text-align: center;
}
.app-header h1 { font-size: 1.25rem; font-weight: 700; color: #1a1a1a; margin: 0; }
.app-header p  { font-size: 0.8rem; color: #888; margin: 0.2rem 0 0; }
.section-card {
    background: #fff;
    border-radius: 20px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.section-title {
    font-size: 0.95rem; font-weight: 700; color: #1a1a1a;
    margin-bottom: 1rem; display: flex; align-items: center; gap: 0.4rem;
}
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {
    border-radius: 14px !important;
    border: 1.5px solid #f0f0f0 !important;
    background: #fafafa !important;
    padding: 0.65rem 1rem !important;
    font-size: 1rem !important;
    color: #1a1a1a !important;
}
[data-testid="stNumberInput"] input:focus {
    border-color: #FF6B6B !important;
    background: #fff !important;
    box-shadow: 0 0 0 3px rgba(255,107,107,0.12) !important;
}
[data-testid="stRadio"] > div { flex-direction: row !important; flex-wrap: wrap !important; gap: 0.5rem !important; }
[data-testid="stRadio"] label {
    border-radius: 50px !important; border: 1.5px solid #e8e8e8 !important;
    padding: 0.4rem 1rem !important; font-size: 0.85rem !important;
    font-weight: 500 !important; color: #555 !important;
    background: #fafafa !important; cursor: pointer !important;
}
[data-testid="stRadio"] label:has(input:checked) {
    background: #FF6B6B !important; border-color: #FF6B6B !important; color: #fff !important;
}
[data-testid="stSelectbox"] > div > div {
    border-radius: 14px !important; border: 1.5px solid #f0f0f0 !important; background: #fafafa !important;
}
[data-testid="stMultiSelect"] > div > div {
    border-radius: 14px !important; border: 1.5px solid #f0f0f0 !important; background: #fafafa !important;
}
[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #FF6B6B, #FF8E53) !important;
    color: #fff !important; border: none !important;
    border-radius: 50px !important; padding: 0.7rem 1.5rem !important;
    font-size: 1rem !important; font-weight: 600 !important; width: 100% !important;
    box-shadow: 0 4px 15px rgba(255,107,107,0.35) !important;
}
[data-testid="stButton"] > button:not([kind="primary"]) {
    border-radius: 50px !important; border: 1.5px solid #e8e8e8 !important;
    background: #fafafa !important; color: #555 !important;
    font-size: 0.85rem !important; padding: 0.4rem 1.2rem !important;
}
.bmi-box { border-radius: 16px; padding: 1rem 1.25rem; margin: 1rem 0; }
.bmi-box.normal { background: #eafaf1; border-left: 4px solid #2ecc71; }
.bmi-box.thin   { background: #fff9e6; border-left: 4px solid #f39c12; }
.bmi-box.fat    { background: #fef0e6; border-left: 4px solid #e67e22; }
.bmi-box.obese  { background: #fde8e8; border-left: 4px solid #e74c3c; }
.bmi-val   { font-size: 1.5rem; font-weight: 800; }
.bmi-label { font-size: 0.8rem; color: #666; margin-top: 0.1rem; }
.health-card {
    background: #fff; border-radius: 20px; padding: 1.25rem;
    margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.health-row { display: flex; gap: 0.75rem; margin-bottom: 0.75rem; }
.health-metric {
    flex: 1; background: #fafafa; border-radius: 16px;
    border: 1.5px solid #f0f0f0; padding: 1rem; text-align: center;
}
.health-metric .metric-val { font-size: 1.6rem; font-weight: 800; color: #FF6B6B; line-height: 1; }
.health-metric .metric-unit { font-size: 0.75rem; color: #999; margin-top: 0.15rem; }
.health-metric .metric-label { font-size: 0.78rem; color: #555; margin-top: 0.4rem; font-weight: 600; }
.health-metric .metric-tag {
    display: inline-block; margin-top: 0.35rem; font-size: 0.72rem;
    padding: 0.2rem 0.6rem; border-radius: 50px; font-weight: 600;
}
.tag-normal { background: #eafaf1; color: #27ae60; }
.tag-thin   { background: #fff9e6; color: #e67e22; }
.tag-fat    { background: #fef0e6; color: #e67e22; }
.tag-obese  { background: #fde8e8; color: #e74c3c; }
.ai-suggest {
    background: #fff8ee; border: 1.5px solid #f39c12; border-radius: 16px;
    padding: 1rem 1.1rem; margin: 0.75rem 0; display: flex; align-items: center; gap: 0.75rem;
}
.ai-suggest .suggest-main { font-size: 1.1rem; font-weight: 800; color: #1a1a1a; }
.ai-suggest .suggest-sub  { font-size: 0.78rem; color: #888; margin-top: 0.1rem; }
.ai-suggest .suggest-hint { font-size: 0.72rem; color: #f39c12; margin-top: 0.25rem; }
.meal-header {
    font-size: 1rem; font-weight: 700; color: #1a1a1a;
    margin: 1rem 0 0.5rem; display: flex; align-items: center; gap: 0.4rem;
}
.dish-card {
    background: #fff; border-radius: 16px; border: 1.5px solid #f0f0f0;
    overflow: hidden; margin-bottom: 0.75rem;
}
.dish-card img { width: 100%; height: 140px; object-fit: cover; }
.dish-body { padding: 0.85rem; }
.dish-name { font-size: 0.92rem; font-weight: 700; color: #1a1a1a; margin-bottom: 0.2rem; }
.dish-type { font-size: 0.75rem; color: #999; margin-bottom: 0.6rem; }
.dish-macros { display: flex; gap: 0.4rem; flex-wrap: wrap; }
.macro-pill { font-size: 0.72rem; padding: 0.2rem 0.6rem; border-radius: 50px; font-weight: 600; }
.macro-calo  { background: #fde8e8; color: #c0392b; }
.macro-pro   { background: #e8f4fd; color: #2980b9; }
.macro-fat   { background: #fff9e6; color: #d35400; }
.macro-fiber { background: #eafaf1; color: #27ae60; }
.score-dot   { font-size: 0.72rem; color: #aaa; margin-top: 0.5rem; }
footer, #MainMenu { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "profile_done" not in st.session_state:
    st.session_state.profile_done = False
if "profile" not in st.session_state:
    st.session_state.profile = {}

# ── BMI logic (WHO Asia-Pacific) ──────────────────────────────────────────────
BMI_RANGES = [
    (0,    18.5, "Thiếu cân",   ["Tăng cân"],                        "thin",   "🟡"),
    (18.5, 23.0, "Bình thường", ["Giảm cân", "Duy trì", "Tăng cân"], "normal", "🟢"),
    (23.0, 27.5, "Thừa cân",    ["Giảm cân", "Duy trì"],             "fat",    "🟠"),
    (27.5, 999,  "Béo phì",     ["Giảm cân"],                        "obese",  "🔴"),
]

def bmi_info(bmi):
    for lo, hi, label, goals, css, icon in BMI_RANGES:
        if lo <= bmi < hi:
            return label, goals, css, icon
    return "Béo phì", ["Giảm cân"], "obese", "🔴"

ALL_PROTEIN_SOURCES = ["Bò", "Heo", "Gà/Vịt", "Cá", "Hải sản", "Trứng", "Đạm thực vật", "Khác"]
VEGAN_SOURCES = ["Đạm thực vật"]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>🍚 Hôm nay ăn gì?</h1>
    <p>Tính toán dinh dưỡng & gợi ý thực đơn cá nhân</p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# BƯỚC 1 — HỒ SƠ SỨC KHOẺ
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.profile_done:

    st.markdown('<div class="section-card"><div class="section-title">📋 Hồ sơ sức khoẻ</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        height = st.number_input("Chiều cao (cm)", min_value=100.0, max_value=250.0, value=165.0, step=0.5)
        weight = st.number_input("Cân nặng (kg)",  min_value=30.0,  max_value=200.0, value=60.0,  step=0.5)
    with col2:
        age      = st.number_input("Tuổi", min_value=20, max_value=49, value=22, help="Hỗ trợ độ tuổi 20–49")
        activity = st.selectbox("Mức độ vận động",
                      ["Ít vận động", "Vận động nhẹ", "Vận động vừa", "Vận động nhiều"])

    gender = st.radio("Giới tính", ["Nam", "Nữ"], horizontal=True)

    bmi_temp = calc_bmi(weight, height)
    bmi_class, allowed_goals, bmi_css, bmi_icon = bmi_info(bmi_temp)

    st.markdown(f"""
<div class="bmi-box {bmi_css}">
    <div class="bmi-val">{bmi_icon} {bmi_temp:.1f}</div>
    <div class="bmi-label">BMI · {bmi_class} · Mục tiêu phù hợp: {" / ".join(allowed_goals)}</div>
</div>
""", unsafe_allow_html=True)

    goal = st.radio("Mục tiêu", allowed_goals, horizontal=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("✅ Lưu hồ sơ", use_container_width=True, type="primary"):
        st.session_state.profile = {
            "age": age, "weight": weight, "height": height,
            "gender": gender, "activity": activity, "goal": goal,
        }
        st.session_state.profile_done = True
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# BƯỚC 2 — HÔM NAY ĂN GÌ
# ══════════════════════════════════════════════════════════════════════════════
else:
    p = st.session_state.profile

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 👤 Hồ sơ")
        st.markdown(f"""
| | |
|---|---|
| Tuổi | {p['age']} |
| Giới tính | {p['gender']} |
| Cân nặng | {p['weight']} kg |
| Chiều cao | {p['height']} cm |
| Hoạt động | {p['activity']} |
| Mục tiêu | {p['goal']} |
""")
        bmi_s      = calc_bmi(p["weight"], p["height"])
        bmi_cls_s, _, _, _ = bmi_info(bmi_s)
        bmr_s      = calc_bmr(p["weight"], p["height"], p["age"], p["gender"])
        tdee_s     = calc_tdee(bmr_s, p["activity"])
        tdee_adj_s = adjust_tdee(tdee_s, p["goal"], p["gender"])
        st.divider()
        st.metric("BMI", f"{bmi_s:.1f}", bmi_cls_s)
        st.metric("TDEE mục tiêu", f"{tdee_adj_s:.0f} kcal")
        st.divider()
        if st.button("✏️ Cập nhật hồ sơ", use_container_width=True):
            st.session_state.profile_done = False
            st.rerun()

    # ── Chỉ số sức khoẻ ──────────────────────────────────────────────────────
    bmi  = calc_bmi(p["weight"], p["height"])
    bmr  = calc_bmr(p["weight"], p["height"], p["age"], p["gender"])
    tdee = calc_tdee(bmr, p["activity"])
    bmi_class, _, bmi_css, _ = bmi_info(bmi)

    tag_map = {
        "normal": ("Bình thường", "tag-normal"),
        "thin":   ("Thiếu cân",   "tag-thin"),
        "fat":    ("Thừa cân",    "tag-fat"),
        "obese":  ("Béo phì",     "tag-obese"),
    }
    tag_label, tag_css = tag_map[bmi_css]

    st.markdown(f"""
<div class="health-card">
    <div class="section-title">🧠 Chỉ số sức khoẻ của bạn</div>
    <div class="health-row">
        <div class="health-metric">
            <div class="metric-val">{bmi:.1f}</div>
            <div class="metric-unit">kg/m²</div>
            <div class="metric-label">BMI</div>
            <span class="metric-tag {tag_css}">{tag_label}</span>
        </div>
        <div class="health-metric">
            <div class="metric-val">{tdee:,.0f}</div>
            <div class="metric-unit">Calo/ngày</div>
            <div class="metric-label">TDEE</div>
            <span class="metric-tag tag-normal">Duy trì cân nặng</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

    # ── Tuỳ chọn hôm nay ─────────────────────────────────────────────────────
    st.markdown('<div class="section-card"><div class="section-title">🌅 Hôm nay ăn gì?</div>', unsafe_allow_html=True)

    diet_type = st.radio("Chế độ ăn", ["Mặn", "Chay"], horizontal=True)

    if diet_type == "Chay":
        st.info("🌿 Chế độ chay: nguồn đạm mặc định là Đạm thực vật")
        preferred_sources = VEGAN_SOURCES
    else:
        preferred_sources = st.multiselect(
            "Nguồn đạm yêu thích", ALL_PROTEIN_SOURCES, default=["Gà/Vịt", "Cá"],
            placeholder="Chọn ít nhất một nguồn đạm...",
        )
        if not preferred_sources:
            st.warning("Chưa chọn nguồn đạm — hệ thống sẽ gợi ý tất cả các loại.")

    lunch_mode  = st.radio("Bữa trưa", ["Cơm + món", "Món độc lập (bún, phở...)"], horizontal=True)
    dinner_mode = st.radio("Bữa tối",  ["Cơm + món", "Món độc lập"],              horizontal=True)
    snack_mode  = st.radio("Bữa phụ",  ["Không có", "Đồ uống", "Ăn vặt", "Đồ ngọt"], horizontal=True)

    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🍽️ Gợi ý thực đơn hôm nay", use_container_width=True, type="primary"):

        # ── Tầng 2 ────────────────────────────────────────────────────────
        tdee_adj  = adjust_tdee(tdee, p["goal"], p["gender"])
        has_snack = snack_mode != "Không có"
        targets   = calc_meal_targets(tdee_adj, p["goal"], has_snack)

        delta_map = {
            "Giảm cân": f"Giảm {tdee - tdee_adj:.0f} calo so với TDEE",
            "Tăng cân": f"Tăng {tdee_adj - tdee:.0f} calo so với TDEE",
            "Duy trì":  "Duy trì cân nặng hiện tại",
        }
        st.markdown(f"""
<div class="ai-suggest">
    <div style="font-size:1.5rem">💡</div>
    <div>
        <div class="suggest-main">{tdee_adj:,.0f} Calo/ngày</div>
        <div class="suggest-sub">{delta_map[p['goal']]}</div>
        <div class="suggest-hint">✨ Gợi ý từ AI dựa trên hồ sơ của bạn</div>
    </div>
</div>
""", unsafe_allow_html=True)

        # ── Tầng 3 ────────────────────────────────────────────────────────
        with st.spinner("Đang tìm món phù hợp..."):
            suggestions = recommend_day(
                meal_targets=targets,
                diet_type=diet_type,
                preferred_sources=preferred_sources,
                snack_label=snack_mode,
                lunch_mode=lunch_mode,
                dinner_mode=dinner_mode,
            )

        MEAL_ICONS = {"Sáng": "🌄", "Trưa": "☀️", "Tối": "🌙", "Phụ": "🍎"}

        def score_color(s):
            if s >= 0.75: return "🟢"
            if s >= 0.55: return "🟡"
            return "🔴"

        for meal_id, dishes in suggestions.items():
            target = targets[meal_id]
            icon   = MEAL_ICONS.get(meal_id, "🍽️")

            st.markdown(f"""
<div class="meal-header">
    {icon} Bữa {meal_id}
    <span style="font-size:0.78rem;font-weight:400;color:#999;margin-left:4px">
        · {target['calo']} kcal · {target['protein']}g protein
    </span>
</div>
""", unsafe_allow_html=True)

            if not dishes:
                st.warning(f"Không tìm được món phù hợp cho bữa {meal_id}.")
                continue

            for dish in dishes:
                img_html = f'<img src="{dish["image_url"]}" alt="{dish["dish_name"]}">' if dish.get("image_url") else ""
                st.markdown(f"""
<div class="dish-card">
    {img_html}
    <div class="dish-body">
        <div class="dish-name">{dish['dish_name']}</div>
        <div class="dish-type">{dish['dish_type']}</div>
        <div class="dish-macros">
            <span class="macro-pill macro-calo">🔥 {dish['calo']} kcal</span>
            <span class="macro-pill macro-pro">💪 {dish['protein']}g đạm</span>
            <span class="macro-pill macro-fat">🧈 {dish['fat']}g béo</span>
            <span class="macro-pill macro-fiber">🌾 {dish['fiber']}g xơ</span>
        </div>
        <div class="score-dot">{score_color(dish['score'])} Điểm phù hợp: {dish['score']:.2f}</div>
    </div>
</div>
""", unsafe_allow_html=True)

        with st.expander("🔧 Debug — meal_targets & filters"):
            st.json({
                "tdee_final": round(tdee_adj, 1),
                "meal_targets": targets,
                "filters": {
                    "diet_type": diet_type,
                    "preferred_sources": preferred_sources,
                    "snack_label": snack_mode,
                    "lunch_mode": lunch_mode,
                    "dinner_mode": dinner_mode,
                },
            })
