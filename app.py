import streamlit as st
from calculator import (
    calc_bmi, bmi_label, calc_bmr, calc_tdee,
    adjust_tdee, calc_meal_targets,
)
from recommender import recommend_day

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Hôm nay ăn gì?", page_icon="🍚", layout="centered")

# ── Session state init ────────────────────────────────────────────────────────
if "profile_done" not in st.session_state:
    st.session_state.profile_done = False
if "profile" not in st.session_state:
    st.session_state.profile = {}

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🍚 Hôm nay ăn gì?")
st.caption("Tính toán dinh dưỡng và gợi ý thực đơn phù hợp mục tiêu cá nhân")
st.divider()

# ── Helper: nhãn BMI theo WHO Asia-Pacific ────────────────────────────────────
BMI_RANGES = [
    (0,    18.5, "Thiếu cân",       ["Tăng cân"]),
    (18.5, 23.0, "Bình thường",     ["Giảm cân", "Duy trì", "Tăng cân"]),
    (23.0, 27.5, "Thừa cân",        ["Giảm cân", "Duy trì"]),
    (27.5, 999,  "Béo phì",         ["Giảm cân"]),
]

BMI_COLOR = {
    "Thiếu cân":  "🟡",
    "Bình thường":"🟢",
    "Thừa cân":   "🟠",
    "Béo phì":    "🔴",
}

def bmi_info(bmi):
    for lo, hi, label, goals in BMI_RANGES:
        if lo <= bmi < hi:
            return label, goals
    return "Béo phì", ["Giảm cân"]

# Tất cả 8 nhãn protein (UI label → CSV token)
ALL_PROTEIN_SOURCES = ["Bò", "Heo", "Gà/Vịt", "Cá", "Hải sản", "Trứng", "Đạm thực vật", "Khác"]
VEGAN_SOURCES       = ["Đạm thực vật"]

# ══════════════════════════════════════════════════════════════════════════════
# BƯỚC 1 — THÔNG TIN CỐ ĐỊNH
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.profile_done:
    st.subheader("📋 Thông tin cá nhân")
    st.caption("Chỉ cần nhập một lần.")

    col1, col2 = st.columns(2)
    with col1:
        age    = st.number_input("Tuổi", min_value=20, max_value=49, value=22,
                                 help="Hệ thống hỗ trợ độ tuổi từ 20 đến 49")
        weight = st.number_input("Cân nặng (kg)", min_value=30.0, max_value=200.0, value=60.0, step=0.5)
        gender = st.radio("Giới tính", ["Nam", "Nữ"], horizontal=True)
    with col2:
        height   = st.number_input("Chiều cao (cm)", min_value=100.0, max_value=250.0, value=165.0, step=0.5)
        activity = st.selectbox(
            "Mức hoạt động",
            ["Ít vận động", "Vận động nhẹ", "Vận động vừa", "Vận động nhiều"],
            help="Ít vận động: ngồi nhiều · Nhẹ: đi bộ 1–3 ngày/tuần · Vừa: tập 3–5 ngày · Nhiều: tập nặng hàng ngày"
        )

    # BMI live preview + ràng buộc mục tiêu
    bmi_temp = calc_bmi(weight, height)
    bmi_class, allowed_goals = bmi_info(bmi_temp)
    color = BMI_COLOR.get(bmi_class, "⚪")

    st.info(
        f"{color} **BMI: {bmi_temp:.1f}** — {bmi_class}  ·  "
        f"Mục tiêu được phép: **{' · '.join(allowed_goals)}**"
    )

    goal = st.radio("Mục tiêu", allowed_goals, horizontal=True)

    st.divider()
    if st.button("✅ Lưu thông tin", use_container_width=True, type="primary"):
        st.session_state.profile = {
            "age": age, "weight": weight, "height": height,
            "gender": gender, "activity": activity, "goal": goal,
        }
        st.session_state.profile_done = True
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# BƯỚC 2 — HÔM NAY ĂN GÌ + GỢI Ý
# ══════════════════════════════════════════════════════════════════════════════
else:
    p = st.session_state.profile

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 👤 Hồ sơ của bạn")
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
        # Chỉ số sức khỏe sidebar
        bmi_s = calc_bmi(p["weight"], p["height"])
        bmi_class_s, _ = bmi_info(bmi_s)
        bmr_s  = calc_bmr(p["weight"], p["height"], p["age"], p["gender"])
        tdee_s = calc_tdee(bmr_s, p["activity"])
        tdee_adj_s = adjust_tdee(tdee_s, p["goal"], p["gender"])

        st.divider()
        st.markdown("**📊 Chỉ số sức khỏe**")
        st.metric("BMI", f"{bmi_s:.1f}", bmi_class_s)
        st.metric("TDEE mục tiêu", f"{tdee_adj_s:.0f} kcal")
        st.divider()

        if st.button("✏️ Cập nhật hồ sơ", use_container_width=True):
            st.session_state.profile_done = False
            st.rerun()

    # ── Hôm nay ăn gì ────────────────────────────────────────────────────────
    st.subheader("🌅 Hôm nay ăn gì?")
    st.write("")

    col1, col2 = st.columns(2)
    with col1:
        diet_type = st.radio("Chế độ ăn", ["Mặn", "Chay"], horizontal=True)

        # Chặn nguồn đạm nếu chọn Chay
        if diet_type == "Chay":
            st.info("🌿 Chế độ chay: nguồn đạm mặc định là **Đạm thực vật**")
            preferred_sources = VEGAN_SOURCES
        else:
            preferred_sources = st.multiselect(
                "Nguồn đạm yêu thích",
                ALL_PROTEIN_SOURCES,
                default=["Gà/Vịt", "Cá"],
                placeholder="Chọn ít nhất một nguồn đạm...",
            )
            if not preferred_sources:
                st.warning("Chưa chọn nguồn đạm — hệ thống sẽ gợi ý tất cả các loại.")

    with col2:
        lunch_mode  = st.radio("Bữa trưa", ["Cơm + món", "Món độc lập (bún, phở...)"], horizontal=True)
        dinner_mode = st.radio("Bữa tối",  ["Cơm + món", "Món độc lập"],              horizontal=True)
        snack_mode  = st.radio("Bữa phụ",  ["Không có", "Đồ uống", "Ăn vặt", "Đồ ngọt"], horizontal=True)

    st.write("")
    if st.button("🍽️ Gợi ý thực đơn", use_container_width=True, type="primary"):

        # ── Tầng 2: tính toán ─────────────────────────────────────────────
        bmi      = calc_bmi(p["weight"], p["height"])
        bmr      = calc_bmr(p["weight"], p["height"], p["age"], p["gender"])
        tdee     = calc_tdee(bmr, p["activity"])
        tdee_adj = adjust_tdee(tdee, p["goal"], p["gender"])
        has_snack = snack_mode != "Không có"
        targets  = calc_meal_targets(tdee_adj, p["goal"], has_snack)

        # ── Chỉ số sức khỏe ───────────────────────────────────────────────
        st.divider()
        st.subheader("📊 Chỉ số sức khỏe")

        bmi_class, _ = bmi_info(bmi)
        color = BMI_COLOR.get(bmi_class, "⚪")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("BMI",      f"{bmi:.1f}",         bmi_class)
        m2.metric("BMR",      f"{bmr:.0f} kcal")
        m3.metric("TDEE",     f"{tdee:.0f} kcal")
        m4.metric("Mục tiêu", f"{tdee_adj:.0f} kcal")

        delta_map = {
            "Giảm cân": f"Thâm hụt {tdee - tdee_adj:.0f} kcal so với TDEE",
            "Tăng cân": f"Dư {tdee_adj - tdee:.0f} kcal so với TDEE",
            "Duy trì":  "Giữ nguyên TDEE",
        }
        st.caption(f"{color} **{bmi_class}** · {delta_map[p['goal']]}")

        # ── Tầng 3: gợi ý ─────────────────────────────────────────────────
        st.divider()
        st.subheader("🥗 Gợi ý thực đơn hôm nay")

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
            icon = MEAL_ICONS.get(meal_id, "🍽️")
            st.markdown(
                f"**{icon} Bữa {meal_id}** — mục tiêu **{target['calo']} kcal** · **{target['protein']}g** protein",
                unsafe_allow_html=True,
            )

            if not dishes:
                st.warning(f"Không tìm được món phù hợp cho bữa {meal_id} với bộ lọc hiện tại.")
                st.write("")
                continue

            cols = st.columns(len(dishes))
            for col, dish in zip(cols, dishes):
                with col:
                    with st.container(border=True):
                        if dish.get("image_url"):
                            st.image(dish["image_url"], use_container_width=True)
                        st.markdown(f"**{dish['dish_name']}**")
                        st.caption(dish["dish_type"])
                        c1, c2 = st.columns(2)
                        c1.markdown(f"🔥 **{dish['calo']}** kcal")
                        c2.markdown(f"💪 **{dish['protein']}g**")
                        c1.markdown(f"🧈 {dish['fat']}g fat")
                        c2.markdown(f"🌾 {dish['fiber']}g fiber")
                        st.caption(f"{score_color(dish['score'])} Điểm phù hợp: {dish['score']:.2f}")

            st.write("")

        # ── Debug expander ─────────────────────────────────────────────────
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
