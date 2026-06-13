# Nạp thư viện streamlit 
import streamlit as st
# Nạp hàm gợi ý thực đơn từ recommender.py
from recommender import recommend_day

# Tiêu đề và biểu tượng cho app
st.set_page_config(page_title="Hôm nay ăn gì?", page_icon="👩‍🍳", layout="centered")

# Phần CSS tuỳ chỉnh để làm đẹp giao diện
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #f0f2f5; }
[data-testid="stMain"] > div { padding-top: 0 !important; }
section[data-testid="stSidebar"] { background: #fff; }
.block-container { max-width: 520px !important; padding: 2rem 1rem 2rem !important; margin: 0 auto !important; }

/* Radio button kiểu chip */
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

/* Nút chính */
[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #FF6B6B, #FF8E53) !important;
    color: #fff !important; border: none !important; border-radius: 50px !important;
    padding: 0.7rem 1.5rem !important; font-size: 1rem !important;
    font-weight: 600 !important; width: 100% !important;
    box-shadow: 0 4px 15px rgba(255,107,107,0.35) !important;
}
[data-testid="stButton"] > button:not([kind="primary"]) {
    border-radius: 50px !important; border: 1.5px solid #e8e8e8 !important;
    background: #fafafa !important; color: #555 !important;
    font-size: 0.85rem !important; padding: 0.4rem 1.2rem !important;
}

/* Input / Select */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div,
[data-testid="stNumberInput"] input {
    border-radius: 14px !important; border: 1.5px solid #f0f0f0 !important;
    background: #fafafa !important;
}
footer, #MainMenu { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
</style>
""", unsafe_allow_html=True)

# Hằng số 
ACTIVITY_FACTORS = {
    "Ít vận động": 1.200,
    "Vận động nhẹ": 1.375,
    "Vận động vừa": 1.550,
    "Vận động nhiều": 1.725,
}

# BMI logic (ràng buộc BMI caculated)
# Bảng định nghĩa 5 mức BMI theo chuẩn châu Á, kèm nhãn, mục tiêu phù hợp và biểu tượng cảm xúc
BMI_RANGES = [
    (0,    17.0, "Thiếu cân (vừa/nặng)", ["Tăng cân"],                        "🔴"),
    (17.0, 18.5, "Thiếu cân nhẹ",        ["Tăng cân", "Duy trì"],             "🟡"),
    (18.5, 23.0, "Bình thường",          ["Giảm cân", "Duy trì", "Tăng cân"], "🟢"),
    (23.0, 25.0, "Thừa cân",             ["Giảm cân", "Duy trì"],             "🟠"),
    (25.0, 999,  "Béo phì",              ["Giảm cân"],                        "🔴"),
]

MACRO_RATIO = {
    "Giảm cân": {"protein": 0.40, "fat": 0.30},
    "Duy trì":  {"protein": 0.30, "fat": 0.30},
    "Tăng cân": {"protein": 0.25, "fat": 0.25},
}

# Phân bổ calo theo bữa (Tầng 2, mục 2.6)
MEAL_RATIO = {
    ("Giảm cân", False): {"Sáng": 0.30, "Trưa": 0.40, "Tối": 0.30},
    ("Duy trì",  False): {"Sáng": 0.25, "Trưa": 0.35, "Tối": 0.40},
    ("Tăng cân", False): {"Sáng": 0.25, "Trưa": 0.35, "Tối": 0.40},
    ("Giảm cân", True):  {"Sáng": 0.25, "Trưa": 0.35, "Tối": 0.25, "Phụ": 0.15},
    ("Duy trì",  True):  {"Sáng": 0.20, "Trưa": 0.30, "Tối": 0.35, "Phụ": 0.15},
    ("Tăng cân", True):  {"Sáng": 0.20, "Trưa": 0.30, "Tối": 0.35, "Phụ": 0.15},
}

# Định nghĩa delta_map ở đây, trước khi dùng
DELTA_MAP = {
    "Giảm cân": "giảm cân lành mạnh",
    "Duy trì":  "duy trì cân nặng",
    "Tăng cân": "tăng cân đều đặn",
}

ALL_PROTEIN_SOURCES = ["Bò", "Heo", "Gà/Vịt", "Cá", "Hải sản", "Trứng", "Đạm thực vật", "Khác"]
VEGAN_SOURCES = ["Đạm thực vật"]

MEAL_ICONS = {"Sáng": "🌄", "Trưa": "☀️", "Tối": "🌙", "Phụ": "🍎"}


# Hàm tính toán (Tầng 1 + 2)
def calc_bmi(weight, height_cm):
    return weight / (height_cm / 100) ** 2

def get_bmi_info(bmi):
    for lo, hi, label, goals, icon in BMI_RANGES:
        if lo <= bmi < hi:
            return label, goals, icon
    return "Béo phì", ["Giảm cân"], "🔴"

def calc_bmr(weight, height_cm, age, gender):
    if gender == "Nam":
        return 10 * weight + 6.25 * height_cm - 5 * age + 5
    return 10 * weight + 6.25 * height_cm - 5 * age - 161

def calc_tdee(bmr, activity_label):
    return bmr * ACTIVITY_FACTORS[activity_label]

def adjust_tdee(tdee, goal, gender):
    """Điều chỉnh TDEE theo mục tiêu + kiểm tra mức tối thiểu (Tầng 2 mục 2.4)"""
    if goal == "Giảm cân":
        deficit = 300 if tdee < 1800 else 500
        final   = tdee - deficit
        min_k   = 1200 if gender == "Nữ" else 1500
        return max(final, min_k)
    if goal == "Tăng cân":
        surplus = 300 if tdee < 1800 else 500
        return tdee + surplus
    return tdee  # Duy trì

def calc_meal_targets(tdee_final, goal, has_snack):
    """Tính meal_targets[] theo pipeline (Tầng 2 mục 2.6) — output truyền xuống Tầng 3"""
    ratios   = MEAL_RATIO[(goal, has_snack)]
    macro_r  = MACRO_RATIO[goal]
    p_day    = tdee_final * macro_r["protein"] / 4   # gram
    f_day    = tdee_final * macro_r["fat"]     / 9   # gram
    targets  = {}
    for meal_id, r in ratios.items():
        targets[meal_id] = {
            "calo":    round(tdee_final * r),
            "protein": round(p_day * r),
            "fat":     round(f_day * r),
        }
    return targets

def delta_label(tdee, tdee_final, goal):
    """Chuỗi mô tả mức điều chỉnh calo"""
    diff = abs(round(tdee_final - tdee))
    if goal == "Giảm cân":  return f"− {diff} kcal/ngày"
    if goal == "Tăng cân":  return f"+ {diff} kcal/ngày"
    return "Giữ nguyên TDEE"


# Session state để lưu hồ sơ người dùng và tránh load lại nhiều lần
if "profile_done" not in st.session_state:
    st.session_state.profile_done = False
if "profile" not in st.session_state:
    st.session_state.profile = {}


# Header của app 
st.title("👩‍🍳🍜 Hôm nay ăn gì?")
st.caption("Gợi ý thực đơn Việt Nam theo mục tiêu dinh dưỡng")
st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# BƯỚC 1 — HỒ SƠ NGƯỜI DÙNG (Tầng 1 mục 1.1)
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.profile_done:
    st.markdown("#### 📋 Hồ sơ sức khoẻ")
    st.caption("Nhập thông tin sức khoẻ của bạn để nhận gợi ý thực đơn phù hợp.")

    col1, col2 = st.columns(2)
    with col1:
        height = st.number_input("Chiều cao (cm)", min_value=100.0, max_value=250.0,
                                  value=165.0, step=0.5)
        weight = st.number_input("Cân nặng (kg)", min_value=30.0,  max_value=200.0,
                                  value=60.0, step=0.5)
    with col2:
        age = st.number_input("Tuổi", min_value=10, max_value=100, value=22)
        activity = st.selectbox("Mức độ vận động", list(ACTIVITY_FACTORS.keys()), index=1)

    gender = st.radio("Giới tính", ["Nam", "Nữ"], horizontal=True)

    # Tính BMI tạm thời để hiển thị nhãn và mục tiêu phù hợp ngay khi nhập thông tin, giúp người dùng hiểu rõ hơn về tình trạng sức khoẻ của mình
    bmi_temp = calc_bmi(weight, height)
    bmi_class, allowed_goals, bmi_icon = get_bmi_info(bmi_temp)
    st.info(
        f"{bmi_icon} **BMI: {bmi_temp:.1f}** — {bmi_class}  ·  "
        f"Mục tiêu phù hợp: **{' / '.join(allowed_goals)}**"
    )

    goal = st.radio("Mục tiêu", allowed_goals, horizontal=True)
    st.write("")

    if st.button("Lưu hồ sơ", use_container_width=True, type="primary"):
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

    # Tính chỉ số sức khoẻ
    bmi = calc_bmi(p["weight"], p["height"])
    bmr = calc_bmr(p["weight"], p["height"], p["age"], p["gender"])
    tdee = calc_tdee(bmr, p["activity"])
    tdee_final = adjust_tdee(tdee, p["goal"], p["gender"])
    bmi_class, _, bmi_icon = get_bmi_info(bmi)

    # Sidebar: hiển thị thông tin hồ sơ người dùng và chỉ số sức khoẻ cơ bản, có nút để quay lại chỉnh sửa.
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
        st.divider()
        st.metric("BMI",          f"{bmi:.1f}", bmi_class)
        st.metric("TDEE mục tiêu", f"{tdee_final:.0f} kcal")
        st.divider()
        if st.button("✏️ Cập nhật hồ sơ", use_container_width=True):
            st.session_state.profile_done = False
            st.rerun()

    # ── Card chỉ số sức khoẻ ─────────────────────────────────────────────────
    st.markdown("#### 🧠 Chỉ số sức khoẻ")

    # badge màu theo BMI
    badge_cfg = {
        "Bình thường": ("#e6f9ef", "#27ae60"),
        "Thiếu cân nhẹ": ("#fff9e6", "#e67e22"),
        "Thiếu cân (vừa/nặng)": ("#fde8e8", "#e74c3c"),
        "Thừa cân": ("#fef0e6", "#e67e22"),
        "Béo phì": ("#fde8e8", "#e74c3c"),
    }
    badge_bg, badge_color = badge_cfg.get(bmi_class, ("#eee", "#555"))
    bmi_pct = max(0, min(100, int((bmi - 14) / (32 - 14) * 100)))
    gender_icon = "♂️" if p["gender"] == "Nam" else "♀️"
    # Dùng hàm delta_label đã định nghĩa ở trên
    dl = delta_label(tdee, tdee_final, p["goal"])

    # Row 1: 2 card hiển thị chỉ số BMI + TDEE
    col_bmi, col_tdee = st.columns(2)
    with col_bmi:
        st.markdown(f"""
<div style="background:#fafafa;border:1.5px solid #f0f0f0;border-radius:16px;padding:1rem;min-height:140px">
  <div style="font-size:0.68rem;color:#aaa;font-weight:600;letter-spacing:.05em">BMI</div>
  <div style="font-size:2.2rem;font-weight:800;color:#1a1a1a;margin:0.1rem 0">{bmi:.1f}</div>
  <span style="background:{badge_bg};color:{badge_color};padding:0.2rem 0.65rem;
    border-radius:50px;font-size:0.75rem;font-weight:700">{bmi_class}</span>
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
  <div style="font-size:1.7rem;font-weight:800;color:#1a1a1a;margin:0.1rem 0">
    {tdee:,.0f} <span style="font-size:0.8rem;font-weight:400;color:#aaa">kcal</span>
  </div>
  <div style="font-size:0.75rem;color:#3a5bd9;font-weight:600">
    Mục tiêu: {tdee_final:,.0f} kcal
  </div>
  <div style="font-size:0.7rem;color:#aaa;margin-top:0.3rem">{p['activity']}</div>
  <div style="font-size:0.7rem;color:#aaa;margin-top:0.15rem">{dl}</div>
</div>
""", unsafe_allow_html=True)

    # Row 2: 4 card hiển thị thông tin cá nhân (chiều cao, cân nặng, tuổi, giới tính)
    st.write("")
    s1, s2, s3, s4 = st.columns(4)
    for col, icon, val, lbl in [
        (s1, "📏", f"{p['height']:.0f} cm", "Chiều cao"),
        (s2, "⚖️", f"{p['weight']:.0f} kg", "Cân nặng"),
        (s3, "🎂", str(p["age"]), "Tuổi"),
        (s4, gender_icon, p["gender"], "Giới tính"),
    ]:
        with col:
            st.markdown(f"""
<div style="background:#fafafa;border:1.5px solid #f0f0f0;border-radius:14px;
  padding:0.65rem 0.4rem;text-align:center">
  <div style="font-size:1.2rem">{icon}</div>
  <div style="font-size:0.9rem;font-weight:800;color:#1a1a1a;margin-top:0.15rem">{val}</div>
  <div style="font-size:0.62rem;color:#aaa;margin-top:0.1rem">{lbl}</div>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # Tùy chọn gợi ý thực đơn trong ngày: chế độ ăn, nguồn đạm yêu thích, chế độ bữa trưa/tối, bữa phụ
    st.markdown("#### 🌅 Hôm nay ăn gì?")

    diet_type = st.radio("Chế độ ăn", ["Mặn", "Chay"], horizontal=True)

    if diet_type == "Chay":
        st.info("🌿 Chế độ chay: nguồn đạm mặc định là Đạm thực vật")
        preferred_sources = VEGAN_SOURCES
    else:
        preferred_sources = st.multiselect(
            "Nguồn đạm yêu thích hôm nay",
            ALL_PROTEIN_SOURCES,
            default=["Gà/Vịt", "Cá"],
            placeholder="Chọn ít nhất một nguồn đạm...",
        )
        if not preferred_sources:
            st.warning("Chưa chọn nguồn đạm — hệ thống sẽ gợi ý tất cả các loại.")

    col1, col2 = st.columns(2)
    with col1:
        lunch_mode = st.radio(
            "Bữa trưa",
            ["Cơm + món", "Món độc lập (bún, phở...)"],
            horizontal=True,
        )
    with col2:
        dinner_mode = st.radio(
            "Bữa tối",
            ["Cơm + món", "Món độc lập"],
            horizontal=True,
        )

    snack_mode = st.radio(
        "Bữa phụ",
        ["Không có", "Đồ uống", "Ăn vặt", "Đồ ngọt"],
        horizontal=True,
    )

    st.write("")

    # Nút gợi ý thực đơn cho ngày hôm nay
    if st.button("🍽️ Gợi ý thực đơn hôm nay", use_container_width=True, type="primary"):
        has_snack = snack_mode != "Không có"
        meal_targets = calc_meal_targets(tdee_final, p["goal"], has_snack)

        st.success(
            f"💡 Mục tiêu hôm nay: **{tdee_final:,.0f} kcal** "
            f"· {DELTA_MAP[p['goal']]}"
        )

        with st.spinner("Đang tìm món phù hợp..."):
            suggestions = recommend_day(
                meal_targets = meal_targets,
                diet_type = diet_type,
                preferred_sources = preferred_sources,
                snack_label = snack_mode,
                lunch_mode = lunch_mode,
                dinner_mode = dinner_mode,
            )

        st.divider()

        # Hiển thị kết quả từng bữa 
        def score_color(s):
            if s >= 0.75: return "#2ecc71"
            if s >= 0.55: return "#f39c12"
            return "#e74c3c"

        def render_dish(dish):
            img_tag = (
                f'<img src="{dish["image_url"]}" '
                f'style="width:100%;height:160px;object-fit:cover;display:block">'
                if dish.get("image_url") else ""
            )
            sc = score_color(dish["score"])
            st.markdown(f"""
<div style="background:#fff;border-radius:16px;overflow:hidden;
  margin-bottom:0.75rem;box-shadow:0 2px 10px rgba(0,0,0,0.07)">
  {img_tag}
  <div style="padding:0.9rem">
    <div style="font-size:1rem;font-weight:800;color:#1a1a1a;margin-bottom:0.2rem">
      {dish['dish_name'].title()}
    </div>
    <div style="font-size:0.72rem;color:#aaa;margin-bottom:0.6rem">{dish['dish_type']}</div>
    <div style="display:flex;gap:1rem;flex-wrap:wrap">
      <span style="font-size:0.82rem;color:#e74c3c;font-weight:700">🔥 {dish['calo']} kcal</span>
      <span style="font-size:0.82rem;color:#2980b9;font-weight:600">💪 {dish['protein']}g đạm</span>
      <span style="font-size:0.82rem;color:#d35400;font-weight:600">🧈 {dish['fat']}g béo</span>
      <span style="font-size:0.82rem;color:#27ae60;font-weight:600">🌾 {dish['fiber']}g xơ</span>
    </div>
    <div style="margin-top:0.5rem;font-size:0.72rem;color:#bbb">
      <span style="display:inline-block;width:8px;height:8px;
        border-radius:50%;background:{sc};margin-right:4px"></span>
      Điểm phù hợp: {dish['score']:.2f}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        for meal_id, target in meal_targets.items():
            icon = MEAL_ICONS.get(meal_id, "🍽️")
            result = suggestions.get(meal_id)

            st.markdown(
                f"**{icon} Bữa {meal_id}** &nbsp;·&nbsp; "
                f"{target['calo']} kcal &nbsp;·&nbsp; {target['protein']}g protein",
                unsafe_allow_html=True,
            )

            if not result:
                st.warning(f"Không tìm được món phù hợp cho bữa {meal_id}.")
                st.write("")
                continue

            # rice_meal trả về dict {protein, soup, veggie, rice}
            if isinstance(result, dict):
                for sub_key, label in [
                    ("protein", "Món chính"),
                    ("soup", "Món canh"),
                    ("veggie", "Món phụ / Rau"),
                    ("rice", "Cơm"),
                ]:
                    dishes = result.get(sub_key, [])
                    if dishes:
                        st.caption(label)
                        for d in dishes:
                            render_dish(d)
            else:
                # standalone hoặc snack: trả về list
                for d in result:
                    render_dish(d)

            st.write("")

        with st.expander("🔧 Debug — meal_targets & filters"):
            st.json({
                "tdee_raw": round(tdee, 1),
                "tdee_final": round(tdee_final, 1),
                "meal_targets": meal_targets,
                "filters": {
                    "diet_type": diet_type,
                    "preferred_sources": preferred_sources,
                    "snack_label": snack_mode,
                    "lunch_mode": lunch_mode,
                    "dinner_mode": dinner_mode,
                },
            })

        if st.button("🔄 Gợi ý lại (món khác)", use_container_width=True):
            st.rerun()
