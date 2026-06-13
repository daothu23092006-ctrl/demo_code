# recommender.py — Tầng 3: hard filter + scoring + pick top meals
# Dựa sát theo pipeline gốc (PIPELINE_.docx)

import pandas as pd
import random

DATA_PATH = "data/final_dishname.csv"

# ── Map nguồn đạm UI → token trong protein_sources_str ──────────────────────
# FIX #1: "Gà/Vịt" tách thành list ["ga", "vit"] vì data không có token "ga_vit"
SOURCE_MAP = {
    "Bò":           ["bo"],
    "Heo":          ["heo"],
    "Gà/Vịt":       ["ga", "vit"],   # ← đã sửa: data dùng "ga" và "vit" riêng
    "Cá":           ["ca"],
    "Hải sản":      ["hai_san"],
    "Trứng":        ["trung"],
    "Đạm thực vật": ["dam_thuc_vat"],
    "Khác":         ["khac"],
}

# ── Map snack_label UI → dish_type trong CSV ─────────────────────────────────
SNACK_TYPE_MAP = {
    "Đồ uống": "đồ uống",
    "Ăn vặt":  "đồ ăn vặt",
    "Đồ ngọt": "đồ ngọt",
}

# ── dish_type hợp lệ cho từng pool (Tầng 3 Bước 2) ──────────────────────────
PROTEIN_DISH_TYPES  = {"món chính"}
SOUP_DISH_TYPES     = {"món canh"}
VEGGIE_DISH_TYPES   = {"món phụ"}
STANDALONE_TYPES    = {"món độc lập"}


# ── Load & làm sạch data ─────────────────────────────────────────────────────
def load_db():
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")

    # FIX #2: is_calories_error là string "True"/"False" trong CSV, không phải bool
    df = df[df["is_calories_error"].astype(str).str.lower() == "false"]

    # Ép kiểu numeric cho các cột dinh dưỡng
    for col in ["calories_per_person", "protein_per_person",
                "fat_per_person", "fiber_per_person", "sugar_per_person"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["calories_per_person"]).reset_index(drop=True)
    return df


# ── Kiểm tra nguồn đạm khớp sở thích ────────────────────────────────────────
def _source_match(row_sources, preferred_sources):
    """
    True nếu món có ít nhất 1 token khớp với preferred_sources.
    So sánh exact token (split theo |) để tránh false positive.
    """
    if not preferred_sources:
        return True
    if pd.isna(row_sources) or str(row_sources).strip() == "":
        return False
    tokens = {s.strip() for s in str(row_sources).split("|")}
    for ui_label in preferred_sources:
        for token in SOURCE_MAP.get(ui_label, [ui_label.lower()]):
            if token in tokens:
                return True
    return False


# ── Hard filter (Tầng 3 Bước 1) ─────────────────────────────────────────────
def hard_filter(df, diet_type, calo_quota, meal_id,
                meal_mode="Cơm + món", snack_label=None, eaten_ids=None):
    """
    Lọc cứng theo pipeline:
    - diet_type (chay/mặn)
    - calo không vượt quota
    - meal_type khớp bữa
    - dish_type theo mode (standalone / rice_meal / snack)
    - loại trừ món đã ăn gần đây
    """
    eaten_ids = eaten_ids or set()

    # Lọc chay/mặn
    diet_csv = "Món chay" if diet_type == "Chay" else "Món mặn"
    df = df[df["diet_type"] == diet_csv].copy()

    # Loại trừ món đã ăn
    if eaten_ids:
        df = df[~df["food_id"].isin(eaten_ids)]

    if meal_id == "Phụ":
        # Bữa phụ: lọc đúng snack_type + filter calo [budget×0.8, budget×1.1]
        snack_dish_type = SNACK_TYPE_MAP.get(snack_label, "đồ ăn vặt")
        df = df[df["dish_type"] == snack_dish_type]
        df = df[df["meal_type"] == "bữa phụ"]
        # FIX #3: filter calo range theo pipeline [budget×0.8, budget×1.1]
        df = df[
            (df["calories_per_person"] >= calo_quota * 0.8) &
            (df["calories_per_person"] <= calo_quota * 1.1)
        ]

    elif meal_id == "Sáng":
        # Bữa sáng: luôn standalone, chỉ lấy meal_type chứa "sáng"
        df = df[df["meal_type"].str.contains("sáng", na=False)]
        # Không filter dish_type vì data sáng đều là "món độc lập"

    else:
        # Bữa Trưa/Tối: chỉ lấy "bữa chính", không lấy "bữa sáng"
        df = df[df["meal_type"] == "bữa chính"]
        # Filter calo quota
        df = df[df["calories_per_person"] <= calo_quota]

        if meal_mode in ("Món độc lập (bún, phở...)", "Món độc lập"):
            df = df[df["dish_type"].isin(STANDALONE_TYPES)]
        # Nếu rice_meal thì KHÔNG filter dish_type ở đây —
        # để build_rice_meal tự tách protein / soup / veggie pool

    return df.reset_index(drop=True)


# ── Scoring cho bữa chính / sáng (Tầng 3 Bước 6) ───────────────────────────
def score_dish(row, calo_quota, protein_target, fat_target, preferred_sources):
    """
    Cold-start scoring theo pipeline:
    0.45 nutrition + 0.25 diversity(=1.0) + 0.20 preference + 0.10 fiber + 0.05 sugar
    """
    calo = row["calories_per_person"] or 1

    protein_ratio    = row["protein_per_person"] / calo
    fat_ratio        = row["fat_per_person"]     / calo
    target_p_ratio   = protein_target / max(calo_quota, 1)
    target_f_ratio   = fat_target     / max(calo_quota, 1)

    nutrition_score = max(0, 1 - (
        abs(protein_ratio - target_p_ratio) +
        abs(fat_ratio     - target_f_ratio)
    ) / 2)

    preference_score = 1.0 if _source_match(
        row["protein_sources_str"], preferred_sources
    ) else 0.5

    fiber_score = min((row["fiber_per_person"] or 0) / calo * 100, 1)
    sugar_score = 1 - min((row["sugar_per_person"] or 0) / calo * 100, 1)

    return (
        0.45 * nutrition_score
      + 0.25 * 1.0            # diversity = 1.0 (cold start)
      + 0.20 * preference_score
      + 0.10 * fiber_score
      + 0.05 * sugar_score
    )


# ── Scoring riêng cho snack (Tầng 3 Bước 4) ─────────────────────────────────
def score_snack(row, calo_quota):
    """
    Pipeline: 0.6 × khớp_calo_budget + 0.4 × random
    """
    calo_match = 1 - abs(row["calories_per_person"] - calo_quota) / max(calo_quota, 1)
    calo_match = max(0, calo_match)
    return 0.6 * calo_match + 0.4 * random.random()


# ── Pick top N từ pool đã lọc ────────────────────────────────────────────────
def _pick_top(pool, score_col, n=1):
    if pool.empty:
        return []
    pool = pool.copy()
    top = pool.nlargest(n, score_col)
    results = []
    for _, row in top.iterrows():
        calo    = row["calories_per_person"] or 0
        protein = row["protein_per_person"]  or 0
        fat     = row["fat_per_person"]      or 0
        fiber   = row["fiber_per_person"]    or 0
        carb    = max((calo - protein * 4 - fat * 9) / 4, 0)
        results.append({
            "food_id":   int(row["food_id"]),
            "dish_name": row["dish_name"],
            "dish_type": row["dish_type"],
            "calo":      round(calo),
            "protein":   round(protein, 1),
            "fat":       round(fat, 1),
            "fiber":     round(fiber, 1),
            "carb":      round(carb, 1),
            "image_url": row.get("image_link", ""),
            "score":     round(row[score_col], 3),
        })
    return results


# ── Build rice meal (Tầng 3 Bước 5) ─────────────────────────────────────────
def build_rice_meal(df_main, preferred_sources, calo_quota, protein_target, fat_target):
    """
    Ghép bữa cơm: protein + canh + rau (món phụ) + cơm trắng
    theo tỉ lệ pipeline: protein 55%, soup 30%, veggie 15%
    """
    # Tách 3 pool từ df_main (đã filter bữa chính + diet)
    protein_pool = df_main[df_main["dish_type"].isin(PROTEIN_DISH_TYPES)].copy()
    soup_pool    = df_main[df_main["dish_type"].isin(SOUP_DISH_TYPES)].copy()
    veggie_pool  = df_main[df_main["dish_type"].isin(VEGGIE_DISH_TYPES)].copy()

    prot_quota   = calo_quota * 0.55
    soup_quota   = calo_quota * 0.30
    veggie_quota = calo_quota * 0.15

    # Score và pick protein
    if protein_pool.empty:
        return None
    protein_pool["_score"] = protein_pool.apply(
        lambda r: score_dish(r, prot_quota, protein_target, fat_target, preferred_sources), axis=1
    )
    protein_dish = _pick_top(protein_pool, "_score", n=1)
    if not protein_dish:
        return None

    # Pick soup gần quota nhất
    soup_dish = []
    if not soup_pool.empty:
        soup_pool = soup_pool[soup_pool["calories_per_person"] <= soup_quota * 1.2].copy()
        if not soup_pool.empty:
            soup_pool["_diff"] = (soup_pool["calories_per_person"] - soup_quota).abs()
            soup_pool["_score"] = -soup_pool["_diff"]
            soup_dish = _pick_top(soup_pool, "_score", n=1)

    # FIX #4: Pick veggie (món phụ) — pipeline yêu cầu, code cũ bỏ qua
    veggie_dish = []
    if not veggie_pool.empty:
        veggie_pool = veggie_pool[
            veggie_pool["calories_per_person"] <= veggie_quota * 1.2
        ].copy()
        if not veggie_pool.empty:
            # Ưu tiên fiber cao theo pipeline
            veggie_pool["_score"] = veggie_pool.apply(
                lambda r: (r["fiber_per_person"] or 0) / max(r["calories_per_person"], 1),
                axis=1
            )
            veggie_dish = _pick_top(veggie_pool, "_score", n=1)

    # Cơm trắng (~130 kcal/100g, phần cơm = rice_quota / 1.3 * 100g)
    rice_quota = calo_quota * 0.55 - (protein_dish[0]["calo"] if protein_dish else 0)
    rice_portion_g = max(rice_quota / 1.3, 0)
    rice = [{
        "food_id":   -1,
        "dish_name": f"Cơm trắng (~{round(rice_portion_g)}g)",
        "dish_type": "món nền",
        "calo":      round(rice_portion_g * 1.3),
        "protein":   round(rice_portion_g * 0.027, 1),
        "fat":       round(rice_portion_g * 0.003, 1),
        "fiber":     0.3,
        "carb":      round(rice_portion_g * 0.28, 1),
        "image_url": "",
        "score":     1.0,
    }]

    return {
        "protein": protein_dish,
        "soup":    soup_dish,
        "veggie":  veggie_dish,
        "rice":    rice,
    }


# ── Recommend toàn ngày ──────────────────────────────────────────────────────
def recommend_day(meal_targets, diet_type, preferred_sources,
                  snack_label="Không có",
                  lunch_mode="Cơm + món", dinner_mode="Cơm + món",
                  eaten_ids=None):
    """
    Trả về dict { meal_id: result } cho toàn ngày.
    meal_id: "Sáng" | "Trưa" | "Tối" | "Phụ"
    """
    df = load_db()
    results = {}

    for meal_id, target in meal_targets.items():
        calo_q  = target["calo"]
        prot_t  = target["protein"]
        fat_t   = target["fat"]

        # Quyết định mode (Tầng 3 Bước 3)
        if meal_id == "Sáng":
            mode = "standalone"
        elif meal_id == "Phụ":
            mode = "snack"
        elif meal_id == "Trưa":
            mode = "standalone" if "độc lập" in lunch_mode.lower() else "rice_meal"
        else:  # Tối
            mode = "standalone" if "độc lập" in dinner_mode.lower() else "rice_meal"

        meal_mode_str = (
            "Món độc lập" if mode == "standalone"
            else ("Cơm + món" if mode == "rice_meal" else snack_label)
        )

        if mode == "snack":
            pool = hard_filter(df, diet_type, calo_q, meal_id,
                               snack_label=snack_label, eaten_ids=eaten_ids)
            if pool.empty:
                results[meal_id] = []
                continue
            pool["_score"] = pool.apply(lambda r: score_snack(r, calo_q), axis=1)
            results[meal_id] = _pick_top(pool, "_score", n=1)

        elif mode == "standalone":
            pool = hard_filter(df, diet_type, calo_q, meal_id,
                               meal_mode=meal_mode_str, eaten_ids=eaten_ids)
            if pool.empty:
                results[meal_id] = []
                continue
            # Ưu tiên preferred_sources trước, fallback toàn pool
            pref_pool = pool[pool["protein_sources_str"].apply(
                lambda s: _source_match(s, preferred_sources)
            )]
            scored_pool = pref_pool if len(pref_pool) >= 3 else pool
            scored_pool = scored_pool.copy()
            scored_pool["_score"] = scored_pool.apply(
                lambda r: score_dish(r, calo_q, prot_t, fat_t, preferred_sources), axis=1
            )
            results[meal_id] = _pick_top(scored_pool, "_score", n=3)

        else:  # rice_meal
            # Hard filter chỉ lọc diet + meal_type, không lọc dish_type
            pool = hard_filter(df, diet_type, calo_q, meal_id,
                               meal_mode="Cơm + món", eaten_ids=eaten_ids)
            meal_result = build_rice_meal(pool, preferred_sources, calo_q, prot_t, fat_t)
            results[meal_id] = meal_result if meal_result else []

    return results
