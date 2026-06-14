# calculator.py — Tầng 1 & 2: BMI, BMR, TDEE, macro, meal targets
ACTIVITY_FACTORS = {
    "Ít vận động":    1.200,
    "Vận động nhẹ":   1.375,
    "Vận động vừa":   1.550,
    "Vận động nhiều": 1.725,
}
MACRO_RATIOS = {
    "Giảm cân": (0.40, 0.30),
    "Duy trì":  (0.30, 0.30),
    "Tăng cân": (0.25, 0.25),
}
MEAL_RATIOS = {
    False: {  # không có bữa phụ
        "Giảm cân": {"Sáng": 0.30, "Trưa": 0.40, "Tối": 0.30},
        "Duy trì":  {"Sáng": 0.25, "Trưa": 0.35, "Tối": 0.40},
        "Tăng cân": {"Sáng": 0.25, "Trưa": 0.35, "Tối": 0.40},
    },
    True: {   # có bữa phụ
        "Giảm cân": {"Sáng": 0.25, "Trưa": 0.35, "Tối": 0.25, "Phụ": 0.15},
        "Duy trì":  {"Sáng": 0.20, "Trưa": 0.30, "Tối": 0.35, "Phụ": 0.15},
        "Tăng cân": {"Sáng": 0.20, "Trưa": 0.30, "Tối": 0.35, "Phụ": 0.15},
    },
}
def calc_bmi(weight_kg, height_cm):
    h = height_cm / 100
    return weight_kg / (h * h)
def bmi_label(bmi):
    """
    Phân loại BMI theo chuẩn châu Á và trả về danh sách mục tiêu tương ứng.
    """
    if bmi < 17.0:
        bmi_class = "Thiếu cân (Vừa/Nặng)"
        allowed_goals = ["Tăng cân"]

    elif 17.0 <= bmi < 18.5:
        bmi_class = "Thiếu cân nhẹ"
        allowed_goals = ["Tăng cân", "Duy trì"]

    elif 18.5 <= bmi < 23.0:
        bmi_class = "Bình thường"
        allowed_goals = ["Giảm cân", "Duy trì", "Tăng cân"]

    elif 23.0 <= bmi < 25.0:
        bmi_class = "Thừa cân"
        allowed_goals = ["Giảm cân", "Duy trì"]

    elif bmi >= 25.0:
        bmi_class = "Béo phì"
        allowed_goals = ["Giảm cân"]

    return bmi_class, allowed_goals
def calc_bmr(weight_kg, height_cm, age, gender):
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if gender == "Nam" else base - 161
def calc_tdee(bmr, activity):
    return bmr * ACTIVITY_FACTORS[activity]
def adjust_tdee(tdee, goal, gender):
    deficit = 300 if tdee < 1800 else 500
    if goal == "Giảm cân":
        min_val = 1200 if gender == "Nữ" else 1500
        return max(tdee - deficit, min_val)
    elif goal == "Tăng cân":
        return tdee + deficit
    return tdee
def calc_meal_targets(tdee_final, goal, has_snack):
    p_ratio, f_ratio = MACRO_RATIOS[goal]
    protein_day = (tdee_final * p_ratio) / 4
    fat_day     = (tdee_final * f_ratio) / 9
    ratios = MEAL_RATIOS[has_snack][goal]
    targets = {}
    for meal, r in ratios.items():
        targets[meal] = {
            "calo":    round(tdee_final  * r),
            "protein": round(protein_day * r, 1),
            "fat":     round(fat_day     * r, 1),
        }
    return targets
