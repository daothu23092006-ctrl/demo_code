# recommender.py — Tầng 3: hard filter + scoring + pick top meals
import pandas as pd
 
DATA_PATH = "data/final_dishname.csv"

# map protein source label (UI) → token trong protein_sources_str (CSV, phân tách bằng |)
SOURCE_MAP = {
    "Bò":           "bo",
    "Heo":          "heo",
    "Gà":           "ga",
    "Vịt":          "vit",
    "Cá":           "ca",
    "Hải sản":      "hai_san",
    "Trứng":        "trung",
    "Đạm thực vật": "dam_thuc_vat",
    "Khác":         "khac",
}

# map snack_label (UI) → dish_type trong CSV
SNACK_TYPE_MAP = {
    "Đồ uống": "đồ uống",
    "Ăn vặt":  "đồ ăn vặt",
    "Đồ ngọt": "đồ ngọt",
}

# dish_type hợp lệ cho bữa chính (Trưa/Tối)
MAIN_DISH_TYPES = {"món chính", "món canh", "món phụ", "món độc lập"}

# dish_type dùng cho mode "Món độc lập" (bún, phở, lẩu...)
STANDALONE_DISH_TYPES = {"món độc lập"}


def load_db():
    df = pd.read_csv(DATA_PATH)
    #df = df[~df["is_calories_error"]].reset_index(drop=True)
    return df


def _source_match(row_sources, preferred_sources):
    """
    True nếu món có ít nhất 1 nguồn đạm user thích.
    So sánh exact token trong list phân tách |, không dùng substring
    để tránh false positive (vd: "ca" khớp "cacao"...).
    """
    if not preferred_sources:
        return True
    if pd.isna(row_sources):
        return False
    sources_list = [s.strip() for s in str(row_sources).split("|")]
    for ui_label in preferred_sources:
        key = SOURCE_MAP.get(ui_label, "")
        if key and key in sources_list:
            return True
    return False


def hard_filter(df, diet_type, meal_id, snack_label, calo_quota,
                meal_mode="Cơm + món", eaten_ids=None):
    """
    Lọc cứng theo:
    - diet_type: Mặn / Chay
    - meal_type trong CSV phải khớp bữa
    - dish_type theo mode (cơm+món vs độc lập)
    - calo không vượt quota
    - loại trừ món đã ăn gần đây
    """
    eaten_ids = eaten_ids or set()

    # diet
    diet_csv = "Món chay" if diet_type == "Chay" else "Món mặn"
    df = df[df["diet_type"] == diet_csv]

    # calo quota
    df = df[df["calories"] <= calo_quota]

    # eaten log
    if eaten_ids:
        df = df[~df["food_id"].isin(eaten_ids)]

    if meal_id == "Phụ":
        snack_dish_type = SNACK_TYPE_MAP.get(snack_label, "đồ ăn vặt")
        df = df[df["dish_type"] == snack_dish_type]
        df = df[df["meal_type"] == "bữa phụ"]

    elif meal_id == "Sáng":
        df = df[df["meal_type"].str.contains("sáng", na=False)]

    else:
        # Bữa Trưa / Tối: chỉ lấy "bữa chính", không lấy bất kỳ món nào có "sáng"
        df = df[df["meal_type"] == "bữa chính"]

        if meal_mode == "Món độc lập (bún, phở...)":
            df = df[df["dish_type"].isin(STANDALONE_DISH_TYPES)]
        else:
            # Cơm + món: tất cả MAIN_DISH_TYPES trừ món độc lập
            df = df[df["dish_type"].isin(MAIN_DISH_TYPES - STANDALONE_DISH_TYPES)]

    return df.reset_index(drop=True)


def score_dish(row, meal_target, preferred_sources):
    """
    Score cold-start:
    - 0.45 nutrition: protein_ratio & fat_ratio gần target
    - 0.25 diversity: luôn 1.0 ở cold start
    - 0.20 preference: nguồn đạm đúng
    - 0.10 fiber bonus
    - 0.05 sugar score
    """
    calo = row["calories"] or 1
    protein_ratio = row["protein_pp"] / calo
    fat_ratio     = row["fat_pp"] / calo

    target_p = meal_target["protein"] / meal_target["calo"]
    target_f = meal_target["fat"]     / meal_target["calo"]

    nutrition_score = max(0, 1 - (
        abs(protein_ratio - target_p) + abs(fat_ratio - target_f)
    ) / 2)

    preference_score = 1.0 if _source_match(row["protein_sources_str"], preferred_sources) else 0.5

    fiber_score = min((row["fiber_pp"] or 0) / calo * 100, 1)
    sugar_score = 1 - min((row["sugar_pp"] or 0) / calo * 100, 1)

    return (
        0.45 * nutrition_score
      + 0.25 * 1.0           # diversity = 1.0 cold start
      + 0.20 * preference_score
      + 0.10 * fiber_score
      + 0.05 * sugar_score
    )


def recommend_meal(meal_id, meal_target, df, diet_type, preferred_sources,
                   snack_label="Không có", meal_mode="Cơm + món",
                   eaten_ids=None, top_n=3, candidate_pool=15):
    """
    Trả về list top_n dict món ăn gợi ý cho 1 bữa.
    Lấy top candidate_pool món có score cao nhất, sau đó random sample top_n
    để mỗi lần "Gợi ý lại" ra bộ món khác nhau.
    meal_id: "Sáng" | "Trưa" | "Tối" | "Phụ"
    """
    pool = hard_filter(df, diet_type, meal_id, snack_label,
                       meal_target["calo"], meal_mode, eaten_ids)

    if pool.empty:
        return []

    pool = pool.copy()
    pool["_score"] = pool.apply(
        lambda r: score_dish(r, meal_target, preferred_sources), axis=1
    )

    # Lấy top candidate_pool món điểm cao nhất → random sample top_n trong đó
    top_candidates = pool.sort_values("_score", ascending=False).head(candidate_pool)
    n_sample = min(top_n, len(top_candidates))
    selected = top_candidates.sample(n=n_sample).sort_values("_score", ascending=False)

    results = []
    for _, row in selected.iterrows():
        results.append({
            "food_id":   int(row["food_id"]),
            "dish_name": row["dish_name"],
            "dish_type": row["dish_type"],
            "calo":      round(row["calories"]),
            "protein":   round(row["protein_pp"], 1),
            "fat":       round(row["fat_pp"], 1),
            "fiber":     round(row["fiber_pp"], 1),
            "image_url": row["image_link"],
            "score":     round(row["_score"], 3),
        })
    return results


def recommend_day(meal_targets, diet_type, preferred_sources,
                  snack_label="Không có",
                  lunch_mode="Cơm + món", dinner_mode="Cơm + món",
                  eaten_ids=None):
    """
    Gợi ý toàn ngày. Trả về dict { meal_id: [danh sách món] }.
    Load DB 1 lần duy nhất, truyền xuống recommend_meal.
    """
    df = load_db()

    meal_modes = {
        "Sáng": "Độc lập",
        "Trưa": lunch_mode,
        "Tối":  dinner_mode,
        "Phụ":  snack_label,
    }

    day_results = {}
    for meal_id, target in meal_targets.items():
        suggestions = recommend_meal(
            meal_id=meal_id,
            meal_target=target,
            df=df,
            diet_type=diet_type,
            preferred_sources=preferred_sources,
            snack_label=snack_label,
            meal_mode=meal_modes.get(meal_id, "Độc lập"),
            eaten_ids=eaten_ids,
            top_n=3,
            candidate_pool=15,
        )
        day_results[meal_id] = suggestions

    return day_results
