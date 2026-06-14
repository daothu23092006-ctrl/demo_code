# recommender.py — Tầng 3: hard filter + scoring + pick top meals
import pandas as pd
import random

DATA_PATH = "data/final_dishname.csv"

# SOURCE_MAP: value là list để _source_match có thể loop
SOURCE_MAP = {
    "Bò":           ["bo"],
    "Heo":          ["heo"],
    "Gà":           ["ga"],          # tách riêng khớp với UI
    "Vịt":          ["vit"],         # tách riêng khớp với UI
    "Cá":           ["ca"],
    "Hải sản":      ["hai_san"],
    "Trứng":        ["trung"],
    "Đạm thực vật": ["dam_thuc_vat"],
    "Khác":         ["khac"],
}

SNACK_TYPE_MAP = {
    "Đồ uống": "đồ uống",
    "Ăn vặt":  "đồ ăn vặt",
    "Đồ ngọt": "đồ ngọt",
}

MAIN_DISH_TYPES     = {"món chính", "món canh", "món phụ", "món độc lập"}
STANDALONE_TYPES    = {"món độc lập"}
PROTEIN_DISH_TYPES  = {"món chính"}
SOUP_DISH_TYPES     = {"món canh"}
VEGGIE_DISH_TYPES   = {"món phụ"}


def load_db():
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    # is_calories_error đọc từ CSV là bool hoặc string tuỳ môi trường — xử lý cả 2
    err_col = df["is_calories_error"]
    if err_col.dtype == object:
        df = df[err_col.str.lower() == "false"]
    else:
        df = df[~err_col]
    for col in ["calories_per_person", "protein_per_person",
                "fat_per_person", "fiber_per_person", "sugar_per_person"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["calories_per_person"]).reset_index(drop=True)


def _source_match(row_sources, preferred_sources):
    """True nếu món có ít nhất 1 token khớp nguồn đạm user chọn."""
    if not preferred_sources:
        return True
    if pd.isna(row_sources) or str(row_sources).strip() == "":
        return False
    tokens = {s.strip() for s in str(row_sources).split("|")}
    for ui_label in preferred_sources:
        for token in SOURCE_MAP.get(ui_label, []):
            if token in tokens:
                return True
    return False


def hard_filter(df, diet_type, meal_id, snack_label, calo_quota,
                meal_mode="Cơm + món", eaten_ids=None):
    eaten_ids = eaten_ids or set()
    diet_csv  = "Món chay" if diet_type == "Chay" else "Món mặn"
    df = df[df["diet_type"] == diet_csv].copy()

    if eaten_ids:
        df = df[~df["food_id"].isin(eaten_ids)]

    if meal_id == "Phụ":
        snack_dish_type = SNACK_TYPE_MAP.get(snack_label, "đồ ăn vặt")
        df = df[df["dish_type"] == snack_dish_type]
        df = df[df["meal_type"] == "bữa phụ"]
        # Filter calo range [budget×0.8, budget×1.1] theo pipeline
        df = df[
            (df["calories_per_person"] >= calo_quota * 0.8) &
            (df["calories_per_person"] <= calo_quota * 1.1)
        ]
    elif meal_id == "Sáng":
        df = df[df["meal_type"].str.contains("sáng", na=False)]
    else:
        df = df[df["meal_type"] == "bữa chính"]
        df = df[df["calories_per_person"] <= calo_quota]
        if meal_mode in ("Món độc lập (bún, phở...)", "Món độc lập"):
            df = df[df["dish_type"].isin(STANDALONE_TYPES)]
        else:
            df = df[df["dish_type"].isin(MAIN_DISH_TYPES - STANDALONE_TYPES)]

    return df.reset_index(drop=True)


def score_dish(row, meal_target, preferred_sources):
    """Cold-start scoring theo pipeline (Tầng 3 Bước 6)."""
    calo = row["calories_per_person"] or 1
    protein_ratio = row["protein_per_person"] / calo
    fat_ratio     = row["fat_per_person"]     / calo
    target_p = meal_target["protein"] / max(meal_target["calo"], 1)
    target_f = meal_target["fat"]     / max(meal_target["calo"], 1)

    nutrition_score  = max(0, 1 - (abs(protein_ratio - target_p) + abs(fat_ratio - target_f)) / 2)
    preference_score = 1.0 if _source_match(row["protein_sources_str"], preferred_sources) else 0.5
    fiber_score      = min((row["fiber_per_person"] or 0) / calo * 100, 1)
    sugar_score      = 1 - min((row["sugar_per_person"] or 0) / calo * 100, 1)

    return (
        0.45 * nutrition_score
      + 0.25 * 1.0            # diversity = 1.0 cold start
      + 0.20 * preference_score
      + 0.10 * fiber_score
      + 0.05 * sugar_score
    )


def score_snack(row, calo_quota):
    """Snack scoring: 0.6×khớp_calo + 0.4×random theo pipeline."""
    calo_match = max(0, 1 - abs(row["calories_per_person"] - calo_quota) / max(calo_quota, 1))
    return 0.6 * calo_match + 0.4 * random.random()


def _to_dict(row, score):
    calo    = row["calories_per_person"] or 0
    protein = row["protein_per_person"]  or 0
    fat     = row["fat_per_person"]      or 0
    fiber   = row["fiber_per_person"]    or 0
    carb    = max((calo - protein * 4 - fat * 9) / 4, 0)
    return {
        "food_id":   int(row["food_id"]),
        "dish_name": row["dish_name"],
        "dish_type": row["dish_type"],
        "calo":      round(calo),
        "protein":   round(protein, 1),
        "fat":       round(fat, 1),
        "fiber":     round(fiber, 1),
        "carb":      round(carb, 1),
        "image_url": row.get("image_link", ""),
        "score":     round(score, 3),
    }


def _pick_top(pool, score_col, n=1):
    if pool.empty:
        return []
    return [_to_dict(row, row[score_col])
            for _, row in pool.nlargest(n, score_col).iterrows()]


def build_rice_meal(df_main, preferred_sources, calo_quota, meal_target):
    """Ghép bữa cơm: protein + canh + rau + cơm (Tầng 3 Bước 5)."""
    protein_pool = df_main[df_main["dish_type"].isin(PROTEIN_DISH_TYPES)].copy()
    soup_pool    = df_main[df_main["dish_type"].isin(SOUP_DISH_TYPES)].copy()
    veggie_pool  = df_main[df_main["dish_type"].isin(VEGGIE_DISH_TYPES)].copy()

    prot_quota   = calo_quota * 0.55
    soup_quota   = calo_quota * 0.30
    veggie_quota = calo_quota * 0.15

    if protein_pool.empty:
        return None

    protein_pool["_score"] = protein_pool.apply(
        lambda r: score_dish(r, meal_target, preferred_sources), axis=1
    )
    protein_dish = _pick_top(protein_pool, "_score", n=1)
    if not protein_dish:
        return None

    soup_dish = []
    if not soup_pool.empty:
        sub = soup_pool[soup_pool["calories_per_person"] <= soup_quota * 1.2].copy()
        if not sub.empty:
            sub["_score"] = -(sub["calories_per_person"] - soup_quota).abs()
            soup_dish = _pick_top(sub, "_score", n=1)

    veggie_dish = []
    if not veggie_pool.empty:
        sub = veggie_pool[veggie_pool["calories_per_person"] <= veggie_quota * 1.2].copy()
        if not sub.empty:
            sub["_score"] = sub.apply(
                lambda r: (r["fiber_per_person"] or 0) / max(r["calories_per_person"], 1), axis=1
            )
            veggie_dish = _pick_top(sub, "_score", n=1)

    rice_portion_g = max((prot_quota - protein_dish[0]["calo"]) / 1.3, 50)
    rice = [{
        "food_id": -1, "dish_name": f"Cơm trắng (~{round(rice_portion_g)}g)",
        "dish_type": "món nền", "calo": round(rice_portion_g * 1.3),
        "protein": round(rice_portion_g * 0.027, 1),
        "fat": round(rice_portion_g * 0.003, 1),
        "fiber": 0.3, "carb": round(rice_portion_g * 0.28, 1),
        "image_url": "", "score": 1.0,
    }]

    return {"protein": protein_dish, "soup": soup_dish,
            "veggie": veggie_dish, "rice": rice}


def recommend_meal(meal_id, meal_target, df, diet_type, preferred_sources,
                   snack_label="Không có", meal_mode="Cơm + món",
                   eaten_ids=None, top_n=3):
    """Gợi ý 1 bữa — trả về list (standalone/snack) hoặc dict (rice_meal)."""
    calo_quota = meal_target["calo"]

    # Quyết định mode (Tầng 3 Bước 3)
    if meal_id == "Phụ":
        mode = "snack"
    elif meal_id == "Sáng":
        mode = "standalone"
    elif meal_mode in ("Món độc lập (bún, phở...)", "Món độc lập"):
        mode = "standalone"
    else:
        mode = "rice_meal"

    if mode == "snack":
        pool = hard_filter(df, diet_type, meal_id, snack_label,
                           calo_quota, eaten_ids=eaten_ids)
        if pool.empty:
            return []
        pool = pool.copy()
        pool["_score"] = pool.apply(lambda r: score_snack(r, calo_quota), axis=1)
        return _pick_top(pool, "_score", n=1)

    elif mode == "standalone":
        pool = hard_filter(df, diet_type, meal_id, snack_label,
                           calo_quota, meal_mode=meal_mode, eaten_ids=eaten_ids)
        if pool.empty:
            return []
        pool = pool.copy()
        pool["_score"] = pool.apply(
            lambda r: score_dish(r, meal_target, preferred_sources), axis=1
        )
        return _pick_top(pool, "_score", n=top_n)

    else:  # rice_meal
        pool = hard_filter(df, diet_type, meal_id, snack_label,
                           calo_quota, meal_mode="Cơm + món", eaten_ids=eaten_ids)
        result = build_rice_meal(pool, preferred_sources, calo_quota, meal_target)
        return result if result else []


def recommend_day(meal_targets, diet_type, preferred_sources,
                  snack_label="Không có",
                  lunch_mode="Cơm + món", dinner_mode="Cơm + món",
                  eaten_ids=None):
    """Gợi ý toàn ngày. Trả về dict { meal_id: list | dict }."""
    df = load_db()

    meal_modes = {
        "Sáng": "Độc lập",
        "Trưa": lunch_mode,
        "Tối":  dinner_mode,
        "Phụ":  snack_label,
    }

    return {
        meal_id: recommend_meal(
            meal_id=meal_id,
            meal_target=target,
            df=df,
            diet_type=diet_type,
            preferred_sources=preferred_sources,
            snack_label=snack_label,
            meal_mode=meal_modes.get(meal_id, "Độc lập"),
            eaten_ids=eaten_ids,
            top_n=3,
        )
        for meal_id, target in meal_targets.items()
    }
