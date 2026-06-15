# Nạp thư viện streamlit 
import streamlit as st
# Nạp các hàm tính toàn chỉ số sức khỏe từ calculator.py
from calculator import (
    calc_bmi, bmi_label, calc_bmr, calc_tdee,
    adjust_tdee, calc_meal_targets,
)
# Nạp hàm gợi ý thực đơn từ recommender.py
from recommender import recommend_day

st.set_page_config(page_title="Hôm nay ăn gì?", page_icon="👩‍🍳", layout="centered") 

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #f0f2f5; }
/*[data-testid="stHeader"] {
    display: none !important;
    height: 0px !important;
}*/
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
[data-testid="stToolbar"] { display: none; }
</style>
""", unsafe_allow_html=True)

# Khởi tạo các biến lưu trữ trạng thái hệ thống
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Light"
#
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

#
with st.sidebar:
    st.markdown("### 🌓 Chế độ nền")
    
    # Checkbox ngầm đổi trạng thái True (Dark) / False (Light)
    is_dark = st.toggle("Kích hoạt chế độ Tối", value=(st.session_state.theme_mode == "Dark"), label_visibility="collapsed")
    
    # Cập nhật trạng thái và rerun để render đúng màu CSS ngầm
    new_theme = "Dark" if is_dark else "Light"
    if new_theme != st.session_state.theme_mode:
        st.session_state.theme_mode = new_theme
        st.rerun()

    # Hiển thị nút trượt đồ họa trực quan tương ứng với trạng thái
    if st.session_state.theme_mode == "Dark":
        st.markdown("""
            <div style="display: flex; align-items: center; gap: 10px; background: #2a2a35; padding: 10px 15px; border-radius: 50px; justify-content: center; border: 1px solid #444;">
                <span style="font-size: 1.2rem; opacity: 0.3;">☀️</span>
                <div style="width: 40px; height: 20px; background: #FF6B6B; border-radius: 20px; position: relative;">
                    <div style="width: 16px; height: 16px; background: white; border-radius: 50%; position: absolute; top: 2px; right: 2px;"></div>
                </div>
                <span style="font-size: 1.1rem; color: #fff; font-weight: 600;">🌙 Chế độ Tối</span>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="display: flex; align-items: center; gap: 10px; background: #f0f2f5; padding: 10px 15px; border-radius: 50px; justify-content: center; border: 1px solid #e8e8e8;">
                <span style="font-size: 1.1rem; color: #1a1a1a; font-weight: 600;">☀️ Chế độ Sáng</span>
                <div style="width: 40px; height: 20px; background: #ccc; border-radius: 20px; position: relative;">
                    <div style="width: 16px; height: 16px; background: white; border-radius: 50%; position: absolute; top: 2px; left: 2px;"></div>
                </div>
                <span style="font-size: 1.2rem; opacity: 0.3;">🌙</span>
            </div>
        """, unsafe_allow_html=True)
        
    st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# GIỮ CẤU TRÚC PHONG CÁCH VÀ CHÈN THEME THAY ĐỔI THEO TRẠNG THÁI
# ══════════════════════════════════════════════════════════════════════════════
# Các thuộc tính chung cho cả 2 giao diện
common_style = """
[data-testid="stHeader"] { display: none !important; height: 0px !important; }
[data-testid="stMain"] > div { padding-top: 2rem !important; }
.block-container { max-width: 480px !important; padding: 2rem 1rem 2rem !important; margin: 0 auto !important; }
[data-testid="stRadio"] > div { flex-direction: row !important; flex-wrap: wrap !important; gap: 0.5rem !important; }
[data-testid="stRadio"] label { border-radius: 50px !important; padding: 0.4rem 1rem !important; font-size: 0.85rem !important; font-weight: 500 !important; cursor: pointer !important; }
[data-testid="stButton"] > button[kind="primary"] { background: linear-gradient(135deg, #FF6B6B, #FF8E53) !important; color: #fff !important; border: none !important; border-radius: 50px !important; padding: 0.7rem 1.5rem !important; font-size: 1rem !important; font-weight: 600 !important; width: 100% !important; box-shadow: 0 4px 15px rgba(255,107,107,0.35) !important; }
[data-testid="stSelectbox"] > div > div, [data-testid="stMultiSelect"] > div > div, [data-testid="stNumberInput"] input { border-radius: 14px !important; }
[data-testid="stNumberInput"] label, [data-testid="stSelectbox"] label { font-size: 1rem !important; font-weight: 700 !important; }
.field-label { font-size: 1rem; font-weight: 700; margin-bottom: 0.4rem; margin-top: 0.75rem; display: block; }
footer, #MainMenu { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
"""

if st.session_state.theme_mode == "Dark":
    # Các thông số ghi đè sang màu Đêm tối (Nền tối, chữ trắng rực)
    st.markdown(f"""
    <style>
    {common_style}
    [data-testid="stAppViewContainer"] {{ background: #141419; }}
    section[data-testid="stSidebar"] {{ background: #1e1e24 !important; border-right: 1px solid #2d2d35; }}
    [data-testid="stMarkdownContainer"] p, h1, h2, h3, h4, h5, h6, span, label, li {{ color: #ffffff !important; }}
    
    [data-testid="stRadio"] label {{ border: 1.5px solid #3f3f4f !important; color: #cccccc !important; background: #2a2a35 !important; }}
    [data-testid="stRadio"] label:has(input:checked) {{ background: #FF6B6B !important; border-color: #FF6B6B !important; color: #fff !important; }}
    [data-testid="stButton"] > button:not([kind="primary"]) {{ border-radius: 50px !important; border: 1.5px solid #3f3f4f !important; background: #2a2a35 !important; color: #ffffff !important; font-size: 0.85rem !important; padding: 0.4rem 1.2rem !important; }}
    
    [data-testid="stSelectbox"] > div > div, [data-testid="stMultiSelect"] > div > div, [data-testid="stNumberInput"] input {{ border: 1.5px solid #3f3f4f !important; background: #2a2a35 !important; color: #ffffff !important; }}
    .field-label {{ color: #ffffff !important; }}
    [data-testid="stMetricValue"] {{ color: #ffffff !important; }}
    </style>
    """, unsafe_allow_html=True)
else:
    # Giữ nguyên bản gốc giao diện màu sáng của bạn
    st.markdown(f"""
    <style>
    {common_style}
    [data-testid="stAppViewContainer"] {{ background: #f0f2f5; }}
    section[data-testid="stSidebar"] {{ background: #fff; }}
    [data-testid="stRadio"] label {{ border: 1.5px solid #e8e8e8 !important; padding: 0.4rem 1rem !important; font-size: 0.85rem !important; font-weight: 500 !important; color: #555 !important; background: #fafafa !important; }}
    [data-testid="stRadio"] label:has(input:checked) {{ background: #FF6B6B !important; border-color: #FF6B6B !important; color: #fff !important; }}
    [data-testid="stButton"] > button:not([kind="primary"]) {{ border-radius: 50px !important; border: 1.5px solid #e8e8e8 !important; background: #fafafa !important; color: #555 !important; font-size: 0.85rem !important; padding: 0.4rem 1.2rem !important; }}
    [data-testid="stSelectbox"] > div > div, [data-testid="stMultiSelect"] > div > div, [data-testid="stNumberInput"] input {{ border: 1.5px solid #f0f0f0 !important; background: #fafafa !important; }}
    [data-testid="stNumberInput"] label, [data-testid="stSelectbox"] label {{ color: #1a1a1a !important; }}
    .field-label {{ color: #1a1a1a; }}
    </style>
    """, unsafe_allow_html=True)
#
BMI_RANGES = [
    (0,    17.0, "Thiếu cân (vừa/nặng)", ["Tăng cân"],                        "🔴"),
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

ALL_PROTEIN_SOURCES = ["Bò", "Heo", "Gà", "Vịt", "Cá", "Hải sản", "Trứng", "Đạm thực vật", "Khác"]
VEGAN_SOURCES = ["Đạm thực vật"]

st.title("👩‍🍳🍜 Hôm nay ăn gì?")
st.caption("Gợi ý thực đơn Việt Nam theo mục tiêu dinh dưỡng")
st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# BƯỚC 1 - HỒ SƠ NGƯỜI DÙNG
# ══════════════════════════════════════════════════════════════════════════════
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

    bmi_temp = calc_bmi(weight, height)
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

# ══════════════════════════════════════════════════════════════════════════════
# BƯỚC 2 - LỰA CHỌN BỘ LỌC VÀ HIỂN THỊ THỰC ĐƠN
# ══════════════════════════════════════════════════════════════════════════════
else:
    p = st.session_state.profile

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
            st.session_state.menu_done = False
            st.session_state.show_suggestions = False
            st.session_state.user_choices = {}
            st.rerun()

    bmi  = calc_bmi(p["weight"], p["height"])
    bmr  = calc_bmr(p["weight"], p["height"], p["age"], p["gender"])
    tdee = calc_tdee(bmr, p["activity"])
    tdee_adj_preview = adjust_tdee(tdee, p["goal"], p["gender"])
    bmi_class, _, bmi_icon = bmi_info(bmi)

    # -------------------------------------------------------------------------
    # TRƯỜNG HỢP 2A: ĐÃ NHẤN NÚT GỢI Ý -> ĐỌC DỮ LIỆU TỪ "user_choices" ĐỂ HIỂN THỊ
    # -------------------------------------------------------------------------
    if st.session_state.menu_done:
        choices = st.session_state.user_choices

        # Gom gọn dữ liệu cơ thể và bộ lọc cũ lại thành một khối đóng/mở (Expander)
        with st.expander("📊 Xem lại Chỉ số sức khoẻ & Bộ lọc đã chọn", expanded=False):
            st.markdown(f"**BMI:** {bmi:.1f} ({bmi_class}) &nbsp;·&nbsp; **Mục tiêu calo:** {tdee_adj_preview:,.0f} kcal")
            st.markdown(f"**Chế độ ăn:** {choices.get('diet_type')} &nbsp;·&nbsp; **Nguồn đạm:** {', '.join(choices.get('preferred_sources', []))}")
            st.markdown(f"**Bữa trưa:** {choices.get('lunch_mode')} &nbsp;·&nbsp; **Bữa tối:** {choices.get('dinner_mode')} &nbsp;·&nbsp; **Bữa phụ:** {choices.get('snack_mode')}")
            
            st.divider()
            
            # --- SỬA ĐỔI 1: CHIA ĐÔI CỘT ĐỂ ĐẶT HAI NÚT SONG SONG NHAU ---
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("🔄 Thay đổi bộ lọc ăn uống", use_container_width=True):
                    st.session_state.menu_done = False
                    st.rerun()
            with btn_col2:
                if st.button("✏️ Cập nhật lại hồ sơ", use_container_width=True):
                    st.session_state.profile_done = False
                    st.session_state.menu_done = False
                    st.session_state.show_suggestions = False
                    st.session_state.user_choices = {}
                    st.rerun()

        st.divider()

        # Render trang kết quả gợi ý món ăn mới từ dữ liệu an toàn trong choices
        tdee_adj  = adjust_tdee(tdee, p["goal"], p["gender"])
        has_snack = choices.get('snack_mode') != "Không có"
        targets   = calc_meal_targets(tdee_adj, p["goal"], has_snack)

        st.success(f"💡 Mục tiêu hôm nay: **{tdee_adj:,.0f} kcal**")

        with st.spinner("Đang tìm món phù hợp..."):
            suggestions = recommend_day(
                meal_targets=targets,
                diet_type=choices.get('diet_type'),
                preferred_sources=choices.get('preferred_sources'),
                snack_label=choices.get('snack_mode'),
                lunch_mode=choices.get('lunch_mode'),
                dinner_mode=choices.get('dinner_mode'),
            )

        MEAL_ICONS = {"Sáng": "🌄", "Trưa": "☀️", "Tối": "🌙", "Phụ": "🍎"}

        def score_color(s):
            if s >= 0.75: return "#2ecc71"
            if s >= 0.55: return "#f39c12"
            return "#e74c3c"

        for meal_id, dishes in suggestions.items():
            target = targets[meal_id]
            icon = MEAL_ICONS.get(meal_id, "🍽️")

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

       # with st.expander("🔧 Debug — meal_targets & filters"):
       #     st.json({
       #         "tdee_final": round(tdee_adj, 1),
       #         "meal_targets": targets,
       #         "filters": choices,
           #    })


        st.write("") 
        # Khi nhấn nút này, hệ thống sẽ rerun và gọi lại hàm gợi ý ngẫu nhiên món khác dựa trên bộ lọc đã chọn trong choices
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
        }.get(p["goal"], "")

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

        # --- SỬA ĐỔI 2: THÊM NÚT SỬA HỒ SƠ NGAY TẠI MÀN HÌNH BỘ LỌC ---
        st.write("")
        if st.button("✏️ Cập nhật lại hồ sơ", use_container_width=True):
            st.session_state.profile_done = False
            st.session_state.menu_done = False
            st.session_state.show_suggestions = False
            st.session_state.user_choices = {}
            st.rerun()

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
        
        # Ngay khi bấm nút, "đóng băng" toàn bộ lựa chọn người dùng đưa vào state an toàn trước khi ẩn widget
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
