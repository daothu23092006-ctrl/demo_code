import streamlit as st
from calculator import (
    calc_bmi, bmi_label, calc_bmr, calc_tdee,
    adjust_tdee, calc_meal_targets,
)
from recommender import recommend_day

st.set_page_config(page_title="Hôm nay ăn gì?", page_icon="🍚", layout="centered")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #f0f2f5; }
[data-testid="stMain"] > div { padding-top: 0 !important; }
section[data-testid="stSidebar"] { background: #fff; }
.block-container { max-width: 480px !important; padding: 2rem 1rem 2rem !important; margin: 0 auto !important; }
[data-testid="stRadio"] > div { flex-direction: row !important; flex-wrap: wrap !important; gap: 0.5rem !important; }
[data-testid="stRadio"] label { border-radius: 50px !important; border: 1.5px solid #e8e8e8 !important; padding: 0.4rem 1rem !important; font-size: 0.85rem !important; font-weight: 500 !important; color: #555 !important; background: #fafafa !important; cursor: pointer !important; }
[data-testid="stRadio"] label:has(input:checked) { background: #FF6B6B !important; border-color: #FF6B6B !important; color: #fff !important; }
[data-testid="stButton"] > button[kind="primary"] { background: linear-gradient(135deg, #FF6B6B, #FF8E53) !important; color: #fff !important; border: none !important; border-radius: 50px !important; padding: 0.7rem 1.5rem !important; font-size: 1rem !important; font-weight: 600 !important; width: 100% !important; box-shadow: 0 4px 15px rgba(255,107,107,0.35) !important; }
[data-testid="stButton"] > button:not([kind="primary"]) { border-radius: 50px !important; border: 1.5px solid #e8e8e8 !important; background: #fafafa !important; color: #555 !important; font-size: 0.85rem !important; padding: 0.4rem 1.2rem !important; }
[data-testid="stSelectbox"] > div > div { border-radius: 14px !important; border: 1.5px solid #f0f0f0 !important; background: #fafafa !important; }
[data-testid="stMultiSelect"] > div > div { border-radius: 14px !important; border: 1.5px solid #f0f0f0 !important; background: #fafafa !important; }
[data-testid="stNumberInput"] input { border-radius: 14px !important; border: 1.5px solid #f0f0f0 !important; background: #fafafa !important; }
footer, #MainMenu { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "profile_done" not in st.session_state:
    st.session_state.profile_done = False
if "profile" not in st.session_state:
    st.session_state.profile = {}

# ── BMI logic (WHO Asia-Pacific, 5 mức) ──────────────────────────────────────
BMI_RANGES = [
    (0,    17.0, "Thiếu cân (vừa/nặng)", ["Tăng cân"],                        "🔴"),
    (17.0, 18.5, "Thiếu cân nhẹ",        ["Tăng cân", "Duy trì"],             "🟡"),
    (18.5, 23.0, "Bình thường",           ["Giảm cân", "Duy trì", "Tăng cân"], "🟢"),
    (23.0, 25.0, "Thừa cân",             ["Giảm cân", "Duy trì"],             "🟠"),
    (25.0, 999,  "Béo phì",              ["Giảm cân"],                        "🔴"),
]

def bmi_info(bmi):
    for lo, hi, label, goals, icon in BMI_RANGES:
        if lo <= bmi < hi:
            return label, goals, icon
    return "Béo phì", ["Giảm cân"], "🔴"

ALL_PROTEIN_SOURCES = ["Bò", "Heo", "Gà/Vịt", "Cá", "Hải sản", "Trứng", "Đạm thực vật", "Khác"]
VEGAN_SOURCES = ["Đạm thực vật"]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:1rem 0 0.5rem">
    <div style="font-size:1.5rem;font-weight:800;color:#1a1a1a">🍚 Hôm nay ăn gì?</div>
    <div style="font-size:0.82rem;color:#999;margin-top:0.2rem">Gợi ý thực đơn Việt Nam theo mục tiêu dinh dưỡng</div>
</div>
""", unsafe_allow_html=True)
st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# BƯỚC 1 — HỒ SƠ
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.profile_done:
    st.markdown("#### 📋 Hồ sơ sức khoẻ")
    st.caption("Chỉ cần nhập một lần.")

    col1, col2 = st.columns(2)
    with col1:
        height = st.number_input("Chiều cao (cm)", min_value=100.0, max_value=250.0, value=165.0, step=0.5)
        weight = st.number_input("Cân nặng (kg)",  min_value=30.0,  max_value=200.0, value=60.0,  step=0.5)
    with col2:
        age      = st.number_input("Tuổi", min_value=10, max_value=100, value=22)
        activity = st.selectbox("Mức độ vận động",
                      ["Ít vận động", "Vận động nhẹ", "Vận động vừa", "Vận động nhiều"])

    gender = st.radio("Giới tính", ["Nam", "Nữ"], horizontal=True)

    bmi_temp = calc_bmi(weight, height)
    bmi_class, allowed_goals, bmi_icon = bmi_info(bmi_temp)
    st.info(f"{bmi_icon} **BMI: {bmi_temp:.1f}** — {bmi_class}  ·  Mục tiêu phù hợp: **{' / '.join(allowed_goals)}**")

    goal = st.radio("Mục tiêu", allowed_goals, horizontal=True)
    st.write("")

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
        bmi_s = calc_bmi(p["weight"], p["height"])
        bmi_cls_s, _, _ = bmi_info(bmi_s)
        bmr_s = calc_bmr(p["weight"], p["height"], p["age"], p["gender"])
        tdee_s = calc_tdee(bmr_s, p["activity"])
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
    tdee_adj_preview = adjust_tdee(tdee, p["goal"], p["gender"])
    bmi_class, _, bmi_icon = bmi_info(bmi)

    delta_map = {
        "Giảm cân": f"−{tdee - tdee_adj_preview:.0f} kcal so với TDEE",
        "Tăng cân": f"+{tdee_adj_preview - tdee:.0f} kcal so với TDEE",
        "Duy trì":  "Giữ nguyên TDEE",
    }

    # badge màu theo BMI
    badge_cfg = {
        "Bình thường":           ("#e6f9ef", "#27ae60"),
        "Thiếu cân nhẹ":         ("#fff9e6", "#e67e22"),
        "Thiếu cân (vừa/nặng)":  ("#fde8e8", "#e74c3c"),
        "Thừa cân":              ("#fef0e6", "#e67e22"),
        "Béo phì":               ("#fde8e8", "#e74c3c"),
    }
    badge_bg, badge_color = badge_cfg.get(bmi_class, ("#eee", "#555"))
    bmi_pct = max(0, min(100, int((bmi - 14) / (32 - 14) * 100)))
    gender_icon = "♂️" if p["gender"] == "Nam" else "♀️"
    delta_label = {
        "Giảm cân": f"−{tdee - tdee_adj_preview:.0f} kcal so với TDEE",
        "Tăng cân": f"+{tdee_adj_preview - tdee:.0f} kcal so với TDEE",
        "Duy trì":  "= Giữ nguyên TDEE",
    }[p["goal"]]

    st.markdown("#### 🧠 Chỉ số sức khoẻ")

    # Row 1: BMI + TDEE — dùng st.columns, HTML đơn giản trong mỗi ô
    col_bmi, col_tdee = st.columns(2)
    with col_bmi:
        st.markdown(f"""
<div style="background:#fafafa;border:1.5px solid #f0f0f0;border-radius:16px;padding:1rem;min-height:140px">
  <div style="font-size:0.68rem;color:#aaa;font-weight:600;letter-spacing:.05em">BMI</div>
  <div style="font-size:2.2rem;font-weight:800;color:#1a1a1a;margin:0.1rem 0">{bmi:.1f}</div>
  <span style="background:{badge_bg};color:{badge_color};padding:0.2rem 0.65rem;border-radius:50px;font-size:0.75rem;font-weight:700">{bmi_class}</span>
  <div style="margin-top:0.65rem;background:#eee;border-radius:50px;height:6px">
    <div style="width:{bmi_pct}%;height:100%;background:{badge_color};border-radius:50px"></div>
  </div>
  <div style="font-size:0.68rem;color:#bbb;margin-top:0.3rem">Chuẩn: 18.5 – 22.9</div>
</div>
""", unsafe_allow_html=True)

    with col_tdee:
        st.markdown(f"""
<div style="background:#f5f8ff;border:1.5px solid #dce8ff;border-radius:16px;padding:1rem;min-height:140px">
  <div style="font-size:0.68rem;color:#aaa;font-weight:600;letter-spacing:.05em">🔥 TDEE</div>
  <div style="font-size:1.7rem;font-weight:800;color:#1a1a1a;margin:0.1rem 0">{tdee:,.0f} <span style="font-size:0.8rem;font-weight:400;color:#aaa">kcal</span></div>
  <div style="font-size:0.75rem;color:#3a5bd9;font-weight:600">Mục tiêu: {tdee_adj_preview:,.0f} kcal</div>
  <div style="font-size:0.7rem;color:#aaa;margin-top:0.3rem">{p['activity']}</div>
  <div style="font-size:0.7rem;color:#aaa;margin-top:0.15rem">{delta_label}</div>
</div>
""", unsafe_allow_html=True)

    # Row 2: 4 stats — dùng st.columns(4)
    st.write("")
    s1, s2, s3, s4 = st.columns(4)
    for col, icon, val, lbl in [
        (s1, "📏", f"{p['height']:.0f}", "Chiều cao"),
        (s2, "⚖️", f"{p['weight']:.0f}", "Cân nặng"),
        (s3, "🎂", str(p['age']),         "Tuổi"),
        (s4, gender_icon, p['gender'],    "Giới tính"),
    ]:
        with col:
            st.markdown(f"""
<div style="background:#fafafa;border:1.5px solid #f0f0f0;border-radius:14px;padding:0.65rem 0.4rem;text-align:center">
  <div style="font-size:1.2rem">{icon}</div>
  <div style="font-size:1rem;font-weight:800;color:#1a1a1a;margin-top:0.15rem">{val}</div>
  <div style="font-size:0.62rem;color:#aaa;margin-top:0.1rem">{lbl}</div>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # ── Tuỳ chọn hôm nay ─────────────────────────────────────────────────────
    st.markdown("#### 🌅 Hôm nay ăn gì?")

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

    col1, col2 = st.columns(2)
    with col1:
        lunch_mode = st.radio("Bữa trưa", ["Cơm + món", "Món độc lập (bún, phở...)"], horizontal=True)
    with col2:
        dinner_mode = st.radio("Bữa tối", ["Cơm + món", "Món độc lập"], horizontal=True)
    snack_mode = st.radio("Bữa phụ", ["Không có", "Đồ uống", "Ăn vặt", "Đồ ngọt"], horizontal=True)

    st.write("")
    if st.button("🍽️ Gợi ý thực đơn hôm nay", use_container_width=True, type="primary"):

        tdee_adj  = adjust_tdee(tdee, p["goal"], p["gender"])
        has_snack = snack_mode != "Không có"
        targets   = calc_meal_targets(tdee_adj, p["goal"], has_snack)

        st.success(f"💡 Mục tiêu hôm nay: **{tdee_adj:,.0f} kcal** · {delta_map[p['goal']]}")

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
            if s >= 0.75: return "#2ecc71"
            if s >= 0.55: return "#f39c12"
            return "#e74c3c"

        st.divider()
        for meal_id, dishes in suggestions.items():
            target = targets[meal_id]
            icon   = MEAL_ICONS.get(meal_id, "🍽️")

            st.markdown(f"**{icon} Bữa {meal_id}** &nbsp;·&nbsp; {target['calo']} kcal &nbsp;·&nbsp; {target['protein']}g protein", unsafe_allow_html=True)

            if not dishes:
                st.warning(f"Không tìm được món phù hợp cho bữa {meal_id}.")
                st.write("")
                continue

            for dish in dishes:
                img_tag = f'<img src="{dish["image_url"]}" style="width:100%;height:180px;object-fit:cover;display:block">' if dish.get("image_url") else ""
                sc = score_color(dish["score"])
                st.markdown(f"""
<div style="background:#fff;border-radius:20px;overflow:hidden;margin-bottom:1rem;box-shadow:0 2px 12px rgba(0,0,0,0.07)">
  {img_tag}
  <div style="padding:1rem">
    <div style="font-size:1.05rem;font-weight:800;color:#1a1a1a;margin-bottom:0.2rem">{dish['dish_name']}</div>
    <div style="font-size:0.75rem;color:#aaa;margin-bottom:0.75rem">{dish['dish_type']}</div>
    <div style="display:flex;gap:1.2rem;align-items:center">
      <span style="font-size:0.82rem;color:#e74c3c;font-weight:700">🔥 {dish['calo']} Calo</span>
      <span style="font-size:0.82rem;color:#2980b9;font-weight:600">💪 {dish['protein']}g đạm</span>
      <span style="font-size:0.82rem;color:#d35400;font-weight:600">🧈 {dish['fat']}g béo</span>
      <span style="font-size:0.82rem;color:#27ae60;font-weight:600">🌾 {dish['fiber']}g xơ</span>
    </div>
    <div style="margin-top:0.6rem;font-size:0.72rem;color:#bbb">
      <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{sc};margin-right:4px"></span>
      Điểm phù hợp: {dish['score']:.2f}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

            st.write("")

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
