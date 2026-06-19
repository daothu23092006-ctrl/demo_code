# Nạp thư viện streamlit 
import streamlit as st
import pickle
import os
import numpy as np

# Nạp các hàm cấu trúc dữ liệu và logic lõi từ Vifoodrec
from models import UserProfile, DailyPreference, Dish
from loaders import load_food_db, normalize_diet_type
import core_logic as cl
from engine import RecommendationEngine

# Giữ nguyên các hàm bổ trợ giao diện cũ để không lỗi render
BMI_RANGES = [
    (0,    17.0, "Thiếu cân (vừa/nặng)", ["Tăng cân"],                     "🔴"),
    (17.0, 18.5, "Thiếu cân nhẹ",        ["Tăng cân", "Duy trì"],             "🟡"),
    (18.5, 23.0, "Bình thường",          ["Giảm cân", "Duy trì", "Tăng cân"], "🟢"),
    (23.0, 25.0, "Thừa cân",             ["Giảm cân", "Duy trì"],             "🟠"),
    (25.0, 999,  "Béo phì",              ["Giảm cân"],                        "🔴"),
]

def bmi_info(bmi):
    for lo, hi, label, goals, icon in BMI_RANGES:
        if lo <= bmi < hi:
            return label, goals, icon
    return "Béo phì", ["Giảm cân"], "🔴"

# Ánh xạ tên giao diện sang chuẩn database phục vụ truy vấn
MAP_GENDER = {"Nam": "male", "Nữ": "female"}
MAP_ACTIVITY = {
    "Ít vận động": "sedentary",
    "Vận động nhẹ": "light",
    "Vận động vừa": "moderate",
    "Vận động nhiều": "active"
}
MAP_GOAL = {
    "Giảm cân": "lose_weight",
    "Duy trì": "maintain_weight",
    "Tăng cân": "gain_weight"
}
MAP_PROTEIN = {
    "Bò": "bo", "Heo": "heo", "Gà": "ga", "Vịt": "vit",
    "Cá": "ca", "Hải sản": "hai_san", "Trứng": "trung", "Khác": "khac"
}
MAP_MODE = {
    "Cơm + món": 1,                      # rice_meal
    "Món độc lập (bún, phở...)": 0,       # standalone
    "Món độc lập": 0
}
MAP_SNACK = {
    "Không có": None,
    "Đồ uống": "đồ uống",
    "Ăn vặt": "đồ ăn vặt",
    "Đồ ngọt": "đồ ngọt"
}

# Khởi tạo hoặc load Cache cho Engine giải thuật (Chỉ load 1 lần để tối ưu tốc độ request)
@st.cache_resource
def get_recommendation_engine():
    # Đọc danh sách món ăn từ file dishname_final.csv của bạn
    food_db = load_food_db("dishname_final.csv")
    
    # Đọc file artifacts mẫu để chạy các nhánh fallback rule-based của Cold Start
    if os.path.exists("artifacts_train.pkl"):
        with open("artifacts_train.pkl", "rb") as f:
            artifacts = pickle.load(f)
    else:
        # Hỗ trợ tự động tạo Artifact rỗng nếu chưa chạy pipeline để tránh crash app
        from artifacts import Artifacts
        artifacts = Artifacts(
            food_db_by_id={d.food_id: d for d in food_db},
            all_feature_values=cl.get_all_feature_values(food_db),
            user_profile_vectors={},
            similar_users_index={},
            popular_dishes_by_group={}
        )
    return RecommendationEngine(food_db, artifacts)

# Các hàm tính toán chỉ số sức khỏe chuyển sang dùng hàm chuẩn hóa của Vifoodrec
def calc_bmi(w, h):
    return w / ((h / 100.0) ** 2)

def calc_bmr(w, h, a, g):
    # Tạo profile ảo để tái sử dụng module core_logic tính toán chính xác tuyệt đối
    gender_en = MAP_GENDER.get(g, "male")
    u = UserProfile(
        user_id="TEMP", persona_id="TEMP", gender=gender_en,
        age_group="20-29" if a < 30 else "30-49", age=a, height_cm=h, weight_kg=w,
        bmi=calc_bmi(w, h), bmi_group="normal", activity_level="sedentary", goal="maintain_weight",
        bmr=0.0, tdee=0.0, tdee_final=0.0, tdee_clamped=False
    )
    return u.bmr

def calc_tdee(bmr, activity):
    # Logic tính toán tự động nằm hoàn toàn trong quá trình khởi tạo UserProfile của core_logic
    return bmr # Hàm bọc giữ nguyên tương thích giao diện

def adjust_tdee(tdee, goal, gender):
    # Tính toán TDEE cuối cùng sau khi cộng/trừ calo theo mục tiêu tăng/giảm cân
    return tdee # Trả về biến gốc, logic thật sẽ được xử lý tự động bởi object UserProfile bên dưới

def calc_meal_targets(tdee_adj, goal, has_snack):
    # Đóng vai trò làm hàm giữ cấu trúc để giao diện đọc chỉ số kcal/protein hiển thị tiêu đề bữa ăn
    return None 

# --- BẮT ĐẦU UI STREAMLIT (GIỮ NGUYÊN HOÀN TOÀN PHẦN RENDER GIAO DIỆN VÀ CSS) ---

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
/* Label to đậm cho number input và selectbox */
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label {
    font-size: 1rem !important;
    font-weight: 700 !important;
    color: #1a1a1a !important;
}
/* Label to đậm cho các section */
.field-label {
    font-size: 1rem;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 0.4rem;
    margin-top: 0.75rem;
    display: block;
}
footer, #MainMenu { visibility: hidden; }
[data-testid="stToolbar"] { display: visible; 
</style>
""", unsafe_allow_html=True)

if "profile_done" not in st.session_state:
    st.session_state.profile_done = False
if "profile" not in st.session_state:
    st.session_state.profile = {}
if "show_suggestions" not in st.session_state:
    st.session_state.show_suggestions = False
if "menu_done" not in st.session_state:
    st.session_state.menu_done = False
if "user_choices" not in st.session_state:
    st.session_state.user_choices = {}

ALL_PROTEIN_SOURCES = ["Bò", "Heo", "Gà", "Vịt", "Cá", "Hải sản", "Trứng", "Khác"]
VEGAN_SOURCES = ["Đạm thực vật"]

st.title("👩‍🍳🍜 Hôm nay ăn gì?")
st.caption("Gợi ý thực đơn Việt Nam theo mục tiêu dinh dưỡng")
st.divider()

if not st.session_state.profile_done:
    st.markdown("#### 📋 Hồ sơ sức khoẻ")
    st.caption("Nhập thông tin sức khoẻ của bạn để nhận gợi ý thực đơn phù hợp.")
    
    col1, col2 = st.columns(2)
    with col1:
        height = st.number_input("Chiều cao (cm)", min_value=100.0, max_value=250.0, value=165.0, step=0.5)
        weight = st.number_input("Cân nặng (kg)",  min_value=30.0,  max_value=200.0, value=60.0,  step=0.5)
    with col2:
        age = st.number_input("Tuổi", min_value=20, max_value=49, value=22)
        activity = st.selectbox("Mức độ vận động",
                      ["Ít vận động", "Vận động nhẹ", "Vận động vừa", "Vận động nhiều"])
    
    st.markdown('<span class="field-label">⚧ Giới tính</span>', unsafe_allow_html=True)
    gender = st.radio("", ["Nam", "Nữ"], horizontal=True, key="gender_radio", label_visibility="collapsed")

    bmi_temp = weight / ((height / 100.0) ** 2)
    bmi_class, allowed_goals, bmi_icon = bmi_info(bmi_temp)
    st.info(f"{bmi_icon} **BMI: {bmi_temp:.1f}** — {bmi_class}\n\nMục tiêu phù hợp cho bạn: **{' / '.join(allowed_goals)}**")

    st.markdown('<span class="field-label">🎯 Mục tiêu của bạn</span>', unsafe_allow_html=True)
    goal = st.radio("", allowed_goals, horizontal=True, key="goal_radio", label_visibility="collapsed")
    st.write("")

    if st.button("Lưu hồ sơ", use_container_width=True, type="primary"):
        st.session_state.profile = {
            "age": age, "weight": weight, "height": height,
            "gender": gender, "activity": activity, "goal": goal,
        }
        st.session_state.profile_done = True
        st.rerun()

else:
    p = st.session_state.profile

    # Tạo UserProfile thật chuẩn cấu trúc Vifoodrec để tính sinh lý tự động
    user_obj = UserProfile(
        user_id="U_COLD",
        persona_id="cold_start_persona",
        gender=MAP_GENDER[p["gender"]],
        age_group="20-29" if p["age"] < 30 else "30-49",
        age=p["age"],
        height_cm=p["height"],
        weight_kg=p["weight"],
        bmi=p["weight"] / ((p["height"] / 100.0) ** 2),
        bmi_group="normal", # Sẽ tự động chuẩn hóa lại trong class
        activity_level=MAP_ACTIVITY[p["activity"]],
        goal=MAP_GOAL[p["goal"]],
        bmr=0.0, tdee=0.0, tdee_final=0.0, tdee_clamped=False
    )

    bmi = user_obj.bmi
    tdee = user_obj.tdee
    tdee_adj_preview = user_obj.tdee_final
    bmi_class, _, bmi_icon = bmi_info(bmi)

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
        st.metric("TDEE mục tiêu", f"{tdee_adj_preview:.0f} kcal")
        st.divider()

    # -------------------------------------------------------------------------
    # TRƯỜNG HỢP 2A: ĐÃ NHẤN NÚT GỢI Ý -> GỌI ENGINE RECOMENDER ĐỂ XỬ LÝ
    # -------------------------------------------------------------------------
    if st.session_state.menu_done:
        choices = st.session_state.user_choices

        with st.expander("📊 Xem lại Chỉ số sức khoẻ & Bộ lọc đã chọn", expanded=False):
            st.markdown(f"**BMI:** {bmi:.1f} ({bmi_class}) &nbsp;·&nbsp; **Mục tiêu calo:** {tdee_adj_preview:,.0f} kcal")
            st.markdown(f"**Chế độ ăn:** {choices.get('diet_type')} &nbsp;·&nbsp; **Nguồn đạm:** {', '.join(choices.get('preferred_sources', []))}")
            st.markdown(f"**Bữa trưa:** {choices.get('lunch_mode')} &nbsp;·&nbsp; **Bữa tối:** {choices.get('dinner_mode')} &nbsp;·&nbsp; **Bữa phụ:** {choices.get('snack_mode')}")

        st.divider()
        st.success(f"💡 Mục tiêu hôm nay: **{tdee_adj_preview:,.0f} kcal**")

        with st.spinner("Đang tìm món phù hợp..."):
            # Khởi tạo Engine giải thuật
            engine = get_recommendation_engine()

            # Chuyển đổi bộ lọc người dùng sang Object DailyPreference chuẩn
            pref_sources_en = [MAP_PROTEIN[s] for s in choices.get('preferred_sources', []) if s in MAP_PROTEIN]
            if choices.get('diet_type') == "Chay":
                pref_sources_en = ["dam_thuc_vat"]

            daily_pref_obj = DailyPreference(
                user_id="U_COLD",
                date=1, # Ngày mặc định khi test demo
                diet_type=normalize_diet_type(choices.get('diet_type')),
                protein_sources=pref_sources_en,
                lunch_mode=MAP_MODE[choices.get('lunch_mode')],
                dinner_mode=MAP_MODE[choices.get('dinner_mode')],
                has_snack=choices.get('snack_mode') != "Không có",
                snack_label=MAP_SNACK.get(choices.get('snack_mode'))
            )

            # Tính toán chỉ tiêu dinh dưỡng từng bữa ăn dựa trên core_logic thật của hệ thống
            targets = {}
            for m_id in ["breakfast", "lunch", "dinner", "snack"]:
                targets[m_id] = cl.compute_meal_target(user_obj, daily_pref_obj, m_id)

            # Gọi Engine gợi ý thực đơn (Mặc định cho Cold Start bằng cách truyền danh sách rỗng vào history log)
            # Hệ thống sẽ tự động điều hướng sang nhánh Rule-Based & Popularity
            suggestions = {}
            for m_id in ["breakfast", "lunch", "dinner", "snack"]:
                if m_id == "snack" and not daily_pref_obj.has_snack:
                    continue
                
                # Gọi hàm gợi ý của RecommendationEngine
                rec_results = engine.recommend_meal(
                    user=user_obj,
                    daily_pref=daily_pref_obj,
                    meal_id=m_id,
                    meal_target=targets[m_id],
                    eaten_log=[], # Rỗng hoàn toàn đại diện cho Cold Start
                    day=1,
                    top_k=5
                )

                if rec_results:
                    # Lấy ngẫu nhiên hoặc lấy Top 1 để hiển thị mâm cơm tương thích nút "Gợi ý lại"
                    chosen_res = rec_results[0]
                    meal_obj = chosen_res.meal
                    
                    # Chuyển đổi dữ liệu bữa ăn (Meal) thành danh sách các món ăn khớp với cấu trúc UI
                    dish_list = []
                    for d in meal_obj.dishes:
                        if d.dish_type == "rice": # Bỏ qua hiển thị dòng text cơm trắng nếu là cơm nạp calo nền
                            continue
                        dish_list.append({
                            "dish_name": d.dish_name.title(),
                            "dish_type": d.dish_type.upper(),
                            "calo": int(d.calories),
                            "protein": round(d.protein_pp, 1),
                            "fat": round(d.fat_pp, 1),
                            "fiber": round(d.fiber_pp, 1),
                            "score": chosen_res.score,
                            "image_url": getattr(d, 'image_link', None) # Đọc link ảnh từ database thật
                        })
                    suggestions[m_id] = dish_list
                else:
                    suggestions[m_id] = []

        # Đồng bộ tên hiển thị giữa ID bữa ăn trong Database và Giao diện UI
        UI_MEAL_MAP = {"breakfast": "Sáng", "lunch": "Trưa", "dinner": "Tối", "snack": "Phụ"}
        MEAL_ICONS = {"Sáng": "🌄", "Trưa": "☀️", "Tối": "🌙", "Phụ": "🍎"}

        def score_color(s):
            if s >= 0.75: return "#2ecc71"
            if s >= 0.55: return "#f39c12"
            return "#e74c3c"

        for db_meal_id, dishes in suggestions.items():
            meal_id = UI_MEAL_MAP[db_meal_id]
            target = targets[db_meal_id]
            icon = MEAL_ICONS.get(meal_id, "🍽️")

            st.markdown(f"#### {icon} Bữa {meal_id} &nbsp;<span style='font-size:0.85rem;font-weight:400;color:#aaa'>· {int(target.calo_quota)} kcal · {int(target.protein_g_target)}g protein</span>", unsafe_allow_html=True)

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
    <div style="display:flex;gap:1.2rem;align-items:center;flex-wrap:wrap">
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

        st.write("") 
        if st.button("🔄 Gợi ý lại (món khác)", use_container_width=True):
            st.rerun()

    # -------------------------------------------------------------------------
    # TRƯỜNG HỢP 2B: CHƯA NHẤN NÚT -> HIỂN THỊ ĐẦY ĐỦ THÔNG TIN VÀ BỘ LỌC ĐỂ CHỌN
    # -------------------------------------------------------------------------
    else:
        badge_cfg = {
            "Bình thường":          ("#e6f9ef", "#27ae60"),
            "Thiếu cân nhẹ":        ("#fff9e6", "#e67e22"),
            "Thiếu cân (vừa/nặng)": ("#fde8e8", "#e74c3c"),
            "Thừa cân":             ("#fef0e6", "#e67e22"),
            "Béo phì":              ("#fde8e8", "#e74c3c"),
        }
        badge_bg, badge_color = badge_cfg.get(bmi_class, ("#eee", "#555"))
        bmi_pct = max(0, min(100, int((bmi - 14) / (32 - 14) * 100)))
        gender_icon = "♂️" if p["gender"] == "Nam" else "♀️"

        delta_label = {
            "Giảm cân": f"− {tdee - tdee_adj_preview:.0f} Calo so với TDEE",
            "Tăng cân": f"+ {tdee_adj_preview - tdee:.0f} Calo so với TDEE",
            "Duy trì":  "= Duy trì cân nặng",
        .get(p["goal"], "")

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
    <span style="font-size:1rem;font-weight:800;color:#FF6B6B">{tdee_adj_preview:,.0f} Calo</span>
  </div>
  <div style="font-size:0.72rem;color:#3a5bd9;margin-top:0.2rem">{delta_label}</div>
</div>
""", unsafe_allow_html=True)

        st.write("")
        s1, s2, s3, s4 = st.columns(4)
        for col, icon, val, lbl in [
            (s1, "📏", f"{p['height']:.0f}", "Chiều cao"),
            (s2, "⚖️", f"{p['weight']:.0f}", "Cân nặng"),
            (s3, "🎂", str(p['age']),        "Tuổi"),
            (s4, gender_icon, p['gender'],   "Giới tính"),
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

        if diet_type == "Chay":
            st.info("🌿 Chế độ chay: nguồn đạm mặc định là Đạm thực vật")
            preferred_sources = VEGAN_SOURCES
        else:
            st.markdown('<span class="field-label">💪 Nguồn đạm yêu thích</span>', unsafe_allow_html=True)
            preferred_sources = st.multiselect(
                "", ALL_PROTEIN_SOURCES, default=["Gà", "Cá"],
                placeholder="Bạn hãy chọn ít nhất một nguồn đạm...",
                key="protein_multi",
                label_visibility="collapsed"
            )
            if not preferred_sources:
                st.warning("Bạn chưa chọn nguồn đạm - hệ thống sẽ gợi ý tất cả các loại.")

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
                "preferred_sources": preferred_sources if diet_type == "Mặn" else VEGAN_SOURCES,
                "lunch_mode": lunch_mode,
                "dinner_mode": dinner_mode,
                "snack_mode": snack_mode
            }
            st.session_state.show_suggestions = True
            st.session_state.menu_done = True
            st.rerun()
