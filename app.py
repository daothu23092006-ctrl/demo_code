# Nạp thư viện streamlit
import csv
import os

import streamlit as st

# Nạp pipeline THẬT (đồng bộ với artifacts.py / engine.py / core_logic.py)
from models import UserProfile, DailyPreference
from loaders import load_food_db
from artifacts import load_artifacts
from engine import RecommendationEngine
import core_logic as cl

st.set_page_config(page_title="Hôm nay ăn gì?", page_icon="👩‍🍳", layout="centered")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #f0f2f5; }
[data-testid="stHeader"] {
    display: none !important;
    height: 0px !important;
}
[data-testid="stMain"] > div { padding-top: 2rem !important; }
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
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label {
    font-size: 1rem !important;
    font-weight: 700 !important;
    color: #1a1a1a !important;
}
.field-label {
    font-size: 1rem;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 0.4rem;
    margin-top: 0.75rem;
    display: block;
}
footer, #MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HẰNG SỐ ĐƯỜNG DẪN DỮ LIỆU + LOAD PIPELINE (1 LẦN, CACHE)
# ══════════════════════════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FOOD_DB_PATH = os.path.join(BASE_DIR, "dishname_final.csv")
ARTIFACTS_PATH = os.path.join(BASE_DIR, "artifacts_train.pkl")


@st.cache_resource
def load_pipeline():
    food_db = load_food_db(FOOD_DB_PATH)
    artifacts = load_artifacts(ARTIFACTS_PATH)
    engine = RecommendationEngine(food_db, artifacts)

    # Dish (models.py) không có field ảnh -> đọc riêng từ CSV để hiển thị
    image_map = {}
    with open(FOOD_DB_PATH, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            fid_raw = row.get("food_id") or row.get("\ufefffood_id")
            img = row.get("image_link")
            if fid_raw and img:
                image_map[int(fid_raw)] = img
    return food_db, artifacts, engine, image_map


food_db, artifacts, engine, IMAGE_MAP = load_pipeline()

# ══════════════════════════════════════════════════════════════════════════════
# BMI / BMR / TDEE — viết lại tại đây vì calculator.py không còn tồn tại trong
# pipeline mới. Nhóm bmi_group dùng đúng slug mà artifacts_train.pkl đã train
# (underweight_severe / underweight_mild / normal / overweight / obese).
# ══════════════════════════════════════════════════════════════════════════════
BMI_RANGES = [
    (0,    17.0, "underweight_severe", "Thiếu cân (vừa/nặng)", ["gain_weight"],                                   "🔴"),
    (17.0, 18.5, "underweight_mild",   "Thiếu cân nhẹ",        ["gain_weight", "maintain_weight"],                "🟡"),
    (18.5, 23.0, "normal",             "Bình thường",          ["lose_weight", "maintain_weight", "gain_weight"], "🟢"),
    (23.0, 25.0, "overweight",         "Thừa cân",             ["lose_weight", "maintain_weight"],                "🟠"),
    (25.0, 999,  "obese",              "Béo phì",              ["lose_weight"],                                   "🔴"),
]

GOAL_VN_TO_KEY = {"Giảm cân": "lose_weight", "Duy trì": "maintain_weight", "Tăng cân": "gain_weight"}
GOAL_KEY_TO_VN = {v: k for k, v in GOAL_VN_TO_KEY.items()}

ACTIVITY_MULT = {
    "Ít vận động": 1.20,
    "Vận động nhẹ": 1.375,
    "Vận động vừa": 1.55,
    "Vận động nhiều": 1.725,
}

# Điều chỉnh TDEE theo mục tiêu (deficit/surplus đơn giản, không có calculator.py
# gốc để tham chiếu — đây là giả định, có thể chỉnh lại theo công thức cũ của bạn)
GOAL_ADJUST = {"lose_weight": 0.80, "maintain_weight": 1.00, "gain_weight": 1.15}
TDEE_MIN, TDEE_MAX = 1200.0, 3800.0

ALL_PROTEIN_SOURCES_VN = ["Bò", "Heo", "Gà", "Vịt", "Cá", "Hải sản", "Trứng", "Khác"]
PROTEIN_VN_TO_SLUG = {
    "Bò": "bo", "Heo": "heo", "Gà": "ga", "Vịt": "vit", "Cá": "ca",
    "Hải sản": "hai_san", "Trứng": "trung", "Khác": "khac",
}
VEGAN_SLUGS = ["dam_thuc_vat"]

SNACK_VN_TO_DISHTYPE = {"Đồ uống": "đồ uống", "Ăn vặt": "đồ ăn vặt", "Đồ ngọt": "đồ ngọt"}

MEAL_LABEL_VN = {"breakfast": "Sáng", "lunch": "Trưa", "dinner": "Tối", "snack": "Phụ"}
MEAL_ICONS = {"breakfast": "🌄", "lunch": "☀️", "dinner": "🌙", "snack": "🍎"}


def calc_bmi(weight_kg: float, height_cm: float) -> float:
    h_m = height_cm / 100
    return weight_kg / (h_m * h_m)


def bmi_info(bmi: float):
    for lo, hi, group_key, label, goals, icon in BMI_RANGES:
        if lo <= bmi < hi:
            return group_key, label, goals, icon
    return "obese", "Béo phì", ["lose_weight"], "🔴"


def calc_bmr(weight_kg: float, height_cm: float, age: int, gender_vn: str) -> float:
    # Mifflin-St Jeor
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if gender_vn == "Nam" else base - 161


def calc_tdee(bmr: float, activity_vn: str) -> float:
    return bmr * ACTIVITY_MULT.get(activity_vn, 1.2)


def adjust_tdee(tdee: float, goal_key: str):
    raw = tdee * GOAL_ADJUST[goal_key]
    clamped_val = max(TDEE_MIN, min(raw, TDEE_MAX))
    return clamped_val, (clamped_val != raw)


def age_group_of(age: int) -> str:
    return "20-29" if age < 30 else "30-49"


def score_color(s: float) -> str:
    if s >= 0.75:
        return "#2ecc71"
    if s >= 0.55:
        return "#f39c12"
    return "#e74c3c"


# ══════════════════════════════════════════════════════════════════════════════
# STATE
# ══════════════════════════════════════════════════════════════════════════════
if "profile_done" not in st.session_state:
    st.session_state.profile_done = False
if "profile" not in st.session_state:
    st.session_state.profile = {}
if "menu_done" not in st.session_state:
    st.session_state.menu_done = False
if "user_choices" not in st.session_state:
    st.session_state.user_choices = {}

st.title("👩‍🍳🍜 Hôm nay ăn gì?")
st.caption("Gợi ý thực đơn Việt Nam theo mục tiêu dinh dưỡng")
st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# BƯỚC 1 - HỒ SƠ NGƯỜI DÙNG
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.profile_done:
    st.markdown("#### 📋 Hồ sơ sức khoẻ")
    st.caption("Nhập thông tin sức khoẻ của bạn để nhận gợi ý thực đơn phù hợp.")

    _prev = st.session_state.profile  # giữ giá trị cũ nếu đang sửa hồ sơ

    col1, col2 = st.columns(2)
    with col1:
        height = st.number_input("Chiều cao (cm)", min_value=100.0, max_value=250.0, value=_prev.get("height", 165.0), step=0.5)
        weight = st.number_input("Cân nặng (kg)", min_value=30.0, max_value=200.0, value=_prev.get("weight", 60.0), step=0.5)
    with col2:
        age = st.number_input("Tuổi", min_value=20, max_value=49, value=_prev.get("age", 22))
        activity = st.selectbox("Mức độ vận động", list(ACTIVITY_MULT.keys()),
                                 index=list(ACTIVITY_MULT.keys()).index(_prev["activity"]) if _prev.get("activity") in ACTIVITY_MULT else 0)

    st.markdown('<span class="field-label">⚧ Giới tính</span>', unsafe_allow_html=True)
    gender = st.radio("", ["Nam", "Nữ"], horizontal=True, key="gender_radio", label_visibility="collapsed",
                       index=["Nam", "Nữ"].index(_prev["gender"]) if _prev.get("gender") in ("Nam", "Nữ") else 0)

    bmi_temp = calc_bmi(weight, height)
    _, bmi_label_vn, allowed_goal_keys, bmi_icon = bmi_info(bmi_temp)
    allowed_goals_vn = [GOAL_KEY_TO_VN[k] for k in allowed_goal_keys]
    st.info(f"{bmi_icon} **BMI: {bmi_temp:.1f}** — {bmi_label_vn}\n\nMục tiêu phù hợp cho bạn: **{' / '.join(allowed_goals_vn)}**")

    st.markdown('<span class="field-label">🎯 Mục tiêu của bạn</span>', unsafe_allow_html=True)
    goal = st.radio("", allowed_goals_vn, horizontal=True, key="goal_radio", label_visibility="collapsed",
                     index=allowed_goals_vn.index(_prev["goal"]) if _prev.get("goal") in allowed_goals_vn else 0)
    st.write("")

    if st.button("Lưu hồ sơ", use_container_width=True, type="primary"):
        st.session_state.profile = {
            "age": age, "weight": weight, "height": height,
            "gender": gender, "activity": activity, "goal": goal,
        }
        st.session_state.profile_done = True
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# BƯỚC 2 - LỰA CHỌN BỘ LỌC VÀ HIỂN THỊ THỰC ĐƠN
# ══════════════════════════════════════════════════════════════════════════════
else:
    p = st.session_state.profile
    goal_key = GOAL_VN_TO_KEY[p["goal"]]

    bmi = calc_bmi(p["weight"], p["height"])
    bmi_group, bmi_class, _, bmi_icon = bmi_info(bmi)
    bmr = calc_bmr(p["weight"], p["height"], p["age"], p["gender"])
    tdee = calc_tdee(bmr, p["activity"])
    tdee_final, tdee_clamped = adjust_tdee(tdee, goal_key)

    # UserProfile thật, dùng để gọi engine
    user = UserProfile(
        user_id="guest", persona_id="guest",
        gender=p["gender"], age_group=age_group_of(p["age"]), age=p["age"],
        height_cm=p["height"], weight_kg=p["weight"],
        bmi=bmi, bmi_group=bmi_group,
        activity_level=p["activity"], goal=goal_key,
        bmr=bmr, tdee=tdee, tdee_final=tdee_final, tdee_clamped=tdee_clamped,
    )

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
        st.metric("BMI", f"{bmi:.1f}", bmi_class)
        st.metric("TDEE mục tiêu", f"{tdee_final:.0f} kcal")
        if tdee_clamped:
            st.caption(f"⚠️ TDEE đã được giới hạn trong khoảng {TDEE_MIN:.0f}–{TDEE_MAX:.0f} kcal vì lý do an toàn.")
        st.divider()
        if st.button("✏️ Sửa hồ sơ", use_container_width=True):
            st.session_state.profile_done = False
            st.session_state.menu_done = False
            st.session_state.user_choices = {}
            st.rerun()

    # -------------------------------------------------------------------------
    # 2A: ĐÃ NHẤN GỢI Ý -> ĐỌC user_choices, GỌI ENGINE, HIỂN THỊ
    # -------------------------------------------------------------------------
    if st.session_state.menu_done:
        choices = st.session_state.user_choices

        # Bảo vệ khỏi session_state cũ (schema cũ trước khi đổi sang pipeline mới)
        # hoặc dict trống do lỗi khác — tránh KeyError, quay lại bước chọn bộ lọc.
        _required_keys = {
            "diet_type_key", "protein_slugs", "lunch_mode_int",
            "dinner_mode_int", "has_snack", "snack_label",
        }
        if not _required_keys.issubset(choices.keys()):
            st.session_state.menu_done = False
            st.session_state.user_choices = {}
            st.rerun()

        with st.expander("📊 Xem lại Chỉ số sức khoẻ & Bộ lọc đã chọn", expanded=False):
            st.markdown(f"**BMI:** {bmi:.1f} ({bmi_class}) &nbsp;·&nbsp; **Mục tiêu calo:** {tdee_final:,.0f} kcal")
            st.markdown(f"**Chế độ ăn:** {choices.get('diet_type')} &nbsp;·&nbsp; **Nguồn đạm:** {', '.join(choices.get('preferred_sources_vn', []))}")
            st.markdown(f"**Bữa trưa:** {choices.get('lunch_mode')} &nbsp;·&nbsp; **Bữa tối:** {choices.get('dinner_mode')} &nbsp;·&nbsp; **Bữa phụ:** {choices.get('snack_mode')}")

        st.divider()
        st.success(f"💡 Mục tiêu hôm nay: **{tdee_final:,.0f} kcal**")

        # DailyPreference thật (đồng bộ với models.py / core_logic.py)
        daily_pref = DailyPreference(
            user_id="guest", date=1,
            diet_type=choices["diet_type_key"],
            protein_sources=choices["protein_slugs"],
            lunch_mode=choices["lunch_mode_int"],
            dinner_mode=choices["dinner_mode_int"],
            has_snack=choices["has_snack"],
            snack_label=choices["snack_label"],
        )

        meal_ids = ["breakfast", "lunch", "dinner"] + (["snack"] if daily_pref.has_snack else [])

        with st.spinner("Đang tìm món phù hợp..."):
            suggestions = {}
            for meal_id in meal_ids:
                meal_target = cl.compute_meal_target(user, daily_pref, meal_id)
                results = engine.recommend_meal(
                    user=user, daily_pref=daily_pref, meal_target=meal_target,
                    meal_id=meal_id, eaten_log=[], day=1, top_k=3,
                )
                suggestions[meal_id] = (meal_target, results)

        for meal_id, (meal_target, results) in suggestions.items():
            icon = MEAL_ICONS.get(meal_id, "🍽️")
            label_vn = MEAL_LABEL_VN.get(meal_id, meal_id)

            st.markdown(
                f"#### {icon} Bữa {label_vn} "
                f"<span style='font-size:0.85rem;font-weight:400;color:#aaa'>"
                f"· {meal_target.calo_quota:.0f} kcal · {meal_target.protein_target:.0f}g protein</span>",
                unsafe_allow_html=True,
            )

            if not results:
                st.warning(f"Không tìm được món phù hợp cho bữa {label_vn}.")
                st.write("")
                continue

            for res in results:
                meal = res.meal
                sc = score_color(res.score)

                # Ảnh: chỉ món chính/độc lập có food_id thật mới có ảnh (Cơm không có)
                hero_dish = meal.dishes[0]
                hero_img = IMAGE_MAP.get(getattr(hero_dish, "food_id", None))
                img_tag = f'<img src="{hero_img}" style="width:100%;height:180px;object-fit:cover;display:block">' if hero_img else ""

                dish_lines = "".join(
                    f"<div style='font-size:0.85rem;color:#555;margin-bottom:0.15rem'>"
                    f"• {d.dish_name}"
                    f"{f' ({d.portion_g:.0f}g)' if hasattr(d, 'portion_g') else ''}"
                    f"</div>"
                    for d in meal.dishes
                )

                st.markdown(f"""
<div style="background:#fff;border-radius:20px;overflow:hidden;margin-bottom:1rem;box-shadow:0 2px 12px rgba(0,0,0,0.07)">
  {img_tag}
  <div style="padding:1rem">
    {dish_lines}
    <div style="display:flex;gap:1.2rem;align-items:center;flex-wrap:wrap;margin-top:0.5rem">
      <span style="font-size:0.82rem;color:#e74c3c;font-weight:700">🔥 {meal.total_kcal:.0f} Calo</span>
      <span style="font-size:0.82rem;color:#2980b9;font-weight:600">💪 {meal.total_protein_g:.1f}g đạm</span>
      <span style="font-size:0.82rem;color:#d35400;font-weight:600">🧈 {meal.total_fat_g:.1f}g béo</span>
      <span style="font-size:0.82rem;color:#27ae60;font-weight:600">🌾 {meal.total_fiber_g:.1f}g xơ</span>
    </div>
    <div style="margin-top:0.6rem;font-size:0.72rem;color:#bbb">
      <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{sc};margin-right:4px"></span>
      Điểm phù hợp: {res.score:.2f}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

            st.write("")

        st.write("")
        if st.button("🔄 Gợi ý lại (món khác)", use_container_width=True):
            st.rerun()

        if st.button("⬅️ Đổi bộ lọc", use_container_width=True):
            st.session_state.menu_done = False
            st.rerun()

    # -------------------------------------------------------------------------
    # 2B: CHƯA NHẤN -> HIỂN THỊ CHỈ SỐ + BỘ LỌC ĐỂ CHỌN
    # -------------------------------------------------------------------------
    else:
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

        delta_label = {
            "lose_weight": f"− {tdee - tdee_final:.0f} Calo so với TDEE",
            "gain_weight": f"+ {tdee_final - tdee:.0f} Calo so với TDEE",
            "maintain_weight": "= Duy trì cân nặng",
        }.get(goal_key, "")

        st.markdown("#### 🧠 Chỉ số sức khoẻ")
        st.markdown(f"""
<div style="background:#fff;border:1.5px solid #e8e8e8;border-left:4px solid {badge_color};border-radius:16px;padding:1.1rem 1.25rem;margin-bottom:0.75rem">
  <div style="font-size:0.7rem;color:#aaa;font-weight:700;letter-spacing:.08em;text-transform:uppercase">BMI · Chỉ số khối cơ thể</div>
  <div style="font-size:0.72rem;color:#bbb;margin-bottom:0.5rem">Đánh giá tình trạng cơ thể dựa trên chiều cao và cân nặng</div>
  <div style="font-size:2.4rem;font-weight:800;color:#1a1a1a;line-height:1">{bmi:.1f}</div>
  <div style="margin:0.5rem 0">
    <span style="background:{badge_bg};color:{badge_color};padding:0.25rem 0.8rem;border-radius:50px;font-size:0.78rem;font-weight:700">{bmi_class}</span>
  </div>
  <div style="background:#eee;border-radius:50px;height:7px;margin-top:0.6rem">
    <div style="width:{bmi_pct}%;height:100%;background:{badge_color};border-radius:50px"></div>
  </div>
  <div style="font-size:0.68rem;color:#bbb;margin-top:0.3rem">Phạm vi chuẩn (châu Á): 18.5 – 22.9</div>
</div>
""", unsafe_allow_html=True)

        st.markdown(f"""
<div style="background:#fff;border:1.5px solid #e8e8e8;border-left:4px solid #3a5bd9;border-radius:16px;padding:1.1rem 1.25rem;margin-bottom:0.75rem">
  <div style="font-size:0.7rem;color:#aaa;font-weight:700;letter-spacing:.08em;text-transform:uppercase">🔥 TDEE · Tổng năng lượng tiêu hao</div>
  <div style="font-size:0.72rem;color:#bbb;margin-bottom:0.5rem">Lượng calo cơ thể đốt cháy mỗi ngày theo mức vận động của bạn</div>
  <div style="font-size:2.4rem;font-weight:800;color:#1a1a1a;line-height:1">{tdee:,.0f} <span style="font-size:0.9rem;font-weight:400;color:#aaa">Calo/ngày</span></div>
  <div style="margin:0.5rem 0">
    <span style="background:#eef2ff;color:#3a5bd9;padding:0.25rem 0.8rem;border-radius:50px;font-size:0.78rem;font-weight:600">Mức vận động: {p['activity']}</span>
  </div>
  <div style="border-top:1px solid #f0f0f0;margin-top:0.75rem;padding-top:0.75rem;display:flex;justify-content:space-between;align-items:center">
    <span style="font-size:0.8rem;color:#555">Mục tiêu của bạn ({p['goal']})</span>
    <span style="font-size:1rem;font-weight:800;color:#FF6B6B">{tdee_final:,.0f} Calo</span>
  </div>
  <div style="font-size:0.72rem;color:#3a5bd9;margin-top:0.2rem">{delta_label}</div>
</div>
""", unsafe_allow_html=True)

        st.write("")
        s1, s2, s3, s4 = st.columns(4)
        for col, icon, val, lbl in [
            (s1, "📏", f"{p['height']:.0f}", "Chiều cao"),
            (s2, "⚖️", f"{p['weight']:.0f}", "Cân nặng"),
            (s3, "🎂", str(p['age']), "Tuổi"),
            (s4, gender_icon, p['gender'], "Giới tính"),
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
        st.markdown("#### 🌅 Hôm nay bạn muốn ăn gì?")

        st.markdown('<span class="field-label">🥗 Chế độ ăn</span>', unsafe_allow_html=True)
        diet_type = st.radio("", ["Mặn", "Chay"], horizontal=True, key="diet_radio", label_visibility="collapsed")
        diet_type_key = "man" if diet_type == "Mặn" else "chay"

        if diet_type == "Chay":
            st.info("🌿 Chế độ chay: nguồn đạm mặc định là Đạm thực vật")
            preferred_sources_vn = ["Đạm thực vật"]
            protein_slugs = VEGAN_SLUGS
        else:
            st.markdown('<span class="field-label">💪 Nguồn đạm yêu thích</span>', unsafe_allow_html=True)
            preferred_sources_vn = st.multiselect(
                "", ALL_PROTEIN_SOURCES_VN, default=["Gà", "Cá"],
                placeholder="Bạn hãy chọn ít nhất một nguồn đạm...",
                key="protein_multi",
                label_visibility="collapsed",
            )
            if not preferred_sources_vn:
                st.warning("Bạn chưa chọn nguồn đạm - hệ thống sẽ gợi ý tất cả các loại.")
                protein_slugs = list(PROTEIN_VN_TO_SLUG.values())
            else:
                protein_slugs = [PROTEIN_VN_TO_SLUG[s] for s in preferred_sources_vn]

        st.markdown('<span class="field-label">🌄 Bữa sáng</span>', unsafe_allow_html=True)
        st.caption("Món độc lập (bún, phở, cháo...)")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<span class="field-label">☀️ Bữa trưa</span>', unsafe_allow_html=True)
            lunch_mode = st.radio("", ["Cơm + món", "Món độc lập (bún, phở...)"], horizontal=True, key="lunch_radio", label_visibility="collapsed")
        with col2:
            st.markdown('<span class="field-label">🌙 Bữa tối</span>', unsafe_allow_html=True)
            dinner_mode = st.radio("", ["Cơm + món", "Món độc lập"], horizontal=True, key="dinner_radio", label_visibility="collapsed")

        st.markdown('<span class="field-label">🍎 Bữa phụ</span>', unsafe_allow_html=True)
        snack_mode = st.radio("", ["Không có", "Đồ uống", "Ăn vặt", "Đồ ngọt"], horizontal=True, key="snack_radio", label_visibility="collapsed")

        st.write("")

        if st.button("🍽️ Gợi ý thực đơn hôm nay", use_container_width=True, type="primary"):
            st.session_state.user_choices = {
                "diet_type": diet_type,
                "diet_type_key": diet_type_key,
                "preferred_sources_vn": preferred_sources_vn,
                "protein_slugs": protein_slugs,
                "lunch_mode": lunch_mode,
                "lunch_mode_int": 0 if lunch_mode == "Cơm + món" else 1,
                "dinner_mode": dinner_mode,
                "dinner_mode_int": 0 if dinner_mode == "Cơm + món" else 1,
                "snack_mode": snack_mode,
                "has_snack": snack_mode != "Không có",
                "snack_label": SNACK_VN_TO_DISHTYPE.get(snack_mode),
            }
            st.session_state.menu_done = True
            st.rerun()
