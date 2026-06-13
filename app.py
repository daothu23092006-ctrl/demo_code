import streamlit as st
from calculator import (
    calc_bmi, bmi_label, calc_bmr, calc_tdee,
    adjust_tdee, calc_meal_targets,
)
from recommender import recommend_day

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Gợi ý thực đơn", page_icon="🍚", layout="centered")

# ── Session state init ────────────────────────────────────────────────────────
if "profile_done" not in st.session_state:
    st.session_state.profile_done = False
if "profile" not in st.session_state:
    st.session_state.profile = {}

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🍚 Hôm nay ăn gì?")
st.caption("Tính toán dinh dưỡng và gợi ý thực đơn phù hợp mục tiêu cá nhân")
st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# BƯỚC 1 — THÔNG TIN CỐ ĐỊNH
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.profile_done:
    st.subheader("📋 Thông tin cá nhân")
    st.caption("Chỉ cần nhập một lần.")

    col1, col2 = st.columns(2)
    with col1:
        age    = st.number_input("Tuổi", min_value=20, max_value=49, value=22)
        weight = st.number_input("Cân nặng (kg)", min_value=30.0, max_value=200.0, value=60.0, step=0.5)
        gender = st.radio("Giới tính", ["Nam", "Nữ"], horizontal=True)
    with col2:
        height   = st.number_input("Chiều cao (cm)", min_value=100.0, max_value=250.0, value=165.0, step=0.5)
        activity = st.selectbox("Mức hoạt động", ["Ít vận động", "Vận động nhẹ", "Vận động vừa", "Vận động nhiều"])

    bmi_temp = calc_bmi(weight, height)
    bmi_class, allowed_goals = bmi_label(bmi_temp)
    st.info(f"BMI hiện tại: **{bmi_temp:.1f}** — {bmi_class}")
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
# BƯỚC 2 — THÔNG TIN HÀNG NGÀY + GỢI Ý
# ══════════════════════════════════════════════════════════════════════════════
else:
    p = st.session_state.profile

    # Sidebar — xem / sửa profile
    with st.sidebar:
        st.markdown("### 👤 Hồ sơ của bạn")
        st.markdown(f"- **Tuổi:** {p['age']}")
        st.markdown(f"- **Giới tính:** {p['gender']}")
        st.markdown(f"- **Cân nặng:** {p['weight']} kg")
        st.markdown(f"- **Chiều cao:** {p['height']} cm")
        st.markdown(f"- **Hoạt động:** {p['activity']}")
        st.markdown(f"- **Mục tiêu:** {p['goal']}")
        st.divider()
        if st.button("✏️ Cập nhật hồ sơ"):
            st.session_state.profile_done = False
            st.rerun()

    st.subheader("🌅 Tùy chỉnh hôm nay")

    col1, col2 = st.columns(2)
    with col1:
        diet_type = st.radio("Chế độ ăn", ["Mặn", "Chay"], horizontal=True)
        preferred_sources = st.multiselect(
            "Nguồn đạm yêu thích",
            ["Gà", "Bò", "Cá", "Tôm", "Heo", "Đậu hũ", "Trứng"],
            default=["Gà", "Cá"],
        )
    with col2:
        lunch_mode  = st.radio("Bữa trưa", ["Cơm + món", "Món độc lập (bún, phở...)"], horizontal=True)
        dinner_mode = st.radio("Bữa tối",  ["Cơm + món", "Món độc lập"],              horizontal=True)
        snack_mode  = st.radio("Bữa phụ",  ["Không có", "Đồ uống", "Ăn vặt", "Đồ ngọt"], horizontal=True)

    st.divider()

    if st.button("🍽️ Gợi ý thực đơn", use_container_width=True, type="primary"):

        # ── Tầng 2: tính toán ─────────────────────────────────────────────
        bmi      = calc_bmi(p["weight"], p["height"])
        bmr      = calc_bmr(p["weight"], p["height"], p["age"], p["gender"])
        tdee     = calc_tdee(bmr, p["activity"])
        tdee_adj = adjust_tdee(tdee, p["goal"], p["gender"])
        has_snack = snack_mode != "Không có"
        targets  = calc_meal_targets(tdee_adj, p["goal"], has_snack)

        # ── Chỉ số dinh dưỡng ─────────────────────────────────────────────
        st.subheader("📊 Chỉ số dinh dưỡng")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("BMI",      f"{bmi:.1f}")
        m2.metric("BMR",      f"{bmr:.0f} kcal")
        m3.metric("TDEE",     f"{tdee:.0f} kcal")
        m4.metric("Mục tiêu", f"{tdee_adj:.0f} kcal")

        bmi_class, _ = bmi_label(bmi)
        delta_map = {
            "Giảm cân": f"−{tdee - tdee_adj:.0f} kcal so với TDEE",
            "Tăng cân": f"+{tdee_adj - tdee:.0f} kcal so với TDEE",
            "Duy trì":  "Giữ nguyên TDEE",
        }
        st.caption(f"BMI: **{bmi_class}** · {delta_map[p['goal']]}")
        st.divider()

        # ── Tầng 3: gợi ý ─────────────────────────────────────────────────
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

        meal_icons = {"Sáng": "🌄", "Trưa": "☀️", "Tối": "🌙", "Phụ": "🍎"}

        for meal_id, dishes in suggestions.items():
            target = targets[meal_id]
            st.markdown(f"#### {meal_icons.get(meal_id, '🍽️')} Bữa {meal_id} — mục tiêu {target['calo']} kcal · {target['protein']}g protein")

            if not dishes:
                st.warning(f"Không tìm được món phù hợp cho bữa {meal_id} với bộ lọc hiện tại.")
                continue

            cols = st.columns(len(dishes))
            for col, dish in zip(cols, dishes):
                with col:
                    with st.container(border=True):
                        if dish.get("image_url"):
                            st.image(dish["image_url"], use_container_width=True)
                        st.markdown(f"**{dish['dish_name']}**")
                        st.caption(f"{dish['dish_type']}")
                        st.markdown(f"🔥 {dish['calo']} kcal")
                        st.markdown(f"💪 Protein: {dish['protein']}g")
                        st.markdown(f"🧈 Fat: {dish['fat']}g")
                        st.markdown(f"🌾 Fiber: {dish['fiber']}g")

            st.divider()

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
