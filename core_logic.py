"""
core_logic.py — Hàm lõi DÙNG CHUNG giữa:
  (1) pipeline production (engine.py gọi để recommend cho user thật)
  (2) simulate eaten_log (sinh dữ liệu giả lập 30 ngày)
"""
import numpy as np
import math
from typing import List, Dict, Tuple
from collections import defaultdict

from models import Dish, Rice, UserProfile, DailyPreference, MealTarget, Meal, EatenEntry

# ── Hằng số toàn cục ─────────────────────────────────────────────────
NO_REPEAT_DAYS = 5
WARMUP_MIN = 5
WARMUP_FULL = 15
K_MIN_CLUSTER = 5
TEMPERATURE = 1

PROTEIN_MAX_RATIO_OF_QUOTA = 0.4
MIN_PROTEIN_DISH_KCAL = 185    # = min(calories món chính) toàn dataset
STANDALONE_MAX_RATIO_OF_QUOTA = 1.12
SOUP_TARGET_RATIO = 0.22
VEGGIE_TARGET_RATIO = 0.12  
MEAL_KCAL_TOLERANCE = 1.12

RICE_MIN_PORTION_G = 80
RICE_MAX_PORTION_G = 250
RICE_FLOOR_KCAL = RICE_MIN_PORTION_G * Rice.RICE_KCAL_PER_100G / 100  # 104 kcal
WRONG_MACRO_THRESHOLD = 0.15        

FEATURE_KEYS = ["protein_source", "calo_band", "diet_type", "meal_category"]

# Tỷ lệ macro theo goal
MACRO_RATIO = {
    "lose_weight":     {"protein": 0.35, "fat": 0.25},
    "maintain_weight": {"protein": 0.30, "fat": 0.30},
    "gain_weight":     {"protein": 0.30, "fat": 0.25},
}
 
# Phân bổ calo theo bữa (ratio)
MEAL_RATIOS_BY_GOAL = {
    "lose_weight": {
        "breakfast": 0.25, "lunch": 0.35, "dinner": 0.25, "snack": 0.15
    },
    "maintain_weight": {
        "breakfast": 0.20, "lunch": 0.30, "dinner": 0.35, "snack": 0.15
    },
    "gain_weight": {
        "breakfast": 0.20, "lunch": 0.30, "dinner": 0.35, "snack": 0.15
    }
}
 
MEAL_RATIOS_BY_GOAL_no_snack = {
    "lose_weight": {
        "breakfast": 0.30, "lunch": 0.40, "dinner": 0.30
    },
    "maintain_weight": {
        "breakfast": 0.25, "lunch": 0.35, "dinner": 0.40
    },
    "gain_weight": {
        "breakfast": 0.25, "lunch": 0.35, "dinner": 0.40
    }
}

# ── Branch theo lượng lịch sử ────────────────────────────────────────
def get_branch(eaten_log: List[EatenEntry]) -> str:
    n = len(eaten_log)
    if n < WARMUP_MIN:
        return "cold_start"
    elif n < WARMUP_FULL:
        return "warmup"
    return "full"


# ── Quyết định mode bữa (Bước 3 Tầng 3) ──────────────────────────────
def decide_mode(daily_pref: DailyPreference, meal_id: str) -> str:
    if meal_id == "snack":
        return "snack"
    if meal_id == "breakfast":
        return "standalone"
    mode_flag = daily_pref.get_mode(meal_id)
    return "rice_meal" if mode_flag == 0 else "standalone"


# ── Hard filter (Bước 1 Tầng 3 / Phần 2 eaten_log — ĐỒNG BỘ) ─────────
def get_candidate_pool(user: UserProfile, day: int, meal_id: str,
                        meal_target: MealTarget, daily_pref: DailyPreference,
                        food_db: List[Dish], eaten_log: List[EatenEntry],
                        slot_type: str, relax: bool = False) -> List[Dish]:
    '''
    Lấy danh sách món ăn phù hợp với bữa ăn (candidate pool).
    user: UserProfile
    day: ngày hiện tại (1-30)
    meal_id: "breakfast"|"lunch"|"dinner"|"snack"
    meal_target: MealTarget
    daily_pref: DailyPreference
    food_db: danh sách Dish
    eaten_log: danh sách EatenEntry đã simulate trước đó
    slot_type: "correct"|"wrong_protein"|"wrong_macro"|"snack"
    relax: nếu True, bỏ qua điều kiện no-repeat 
    '''
    recent_ids = {e.protein_dish_id for e in eaten_log
                  if day - NO_REPEAT_DAYS <= e.date < day}

    max_ratio = PROTEIN_MAX_RATIO_OF_QUOTA if meal_target.mode == "rice_meal" else 1.12
    max_kcal_allowed = max(meal_target.calo_quota * max_ratio, MIN_PROTEIN_DISH_KCAL)

    pool = [d for d in food_db
            if d.diet_type == daily_pref.diet_type
            and d.meal_type_compatible(meal_id)
            and d.calories <= max_kcal_allowed
            and (relax or d.food_id not in recent_ids)]

    if meal_id == "snack":
        snack_label = daily_pref.snack_label or ""
        return [d for d in pool if d.dish_type == snack_label]

    if meal_target.mode == "rice_meal":
        pool = [d for d in pool if d.dish_type == "món chính"]
    elif meal_target.mode == "standalone":
        pool = [d for d in pool if d.dish_type == "món độc lập"]

    if slot_type == "correct":
        return pool
    elif slot_type == "wrong_protein":
        pref_sources = set(daily_pref.get_protein_sources())
        wrong = [d for d in pool if not (set(d.protein_sources) & pref_sources)]
        return wrong if wrong else pool
    elif slot_type == "wrong_macro":
        protein_ratio_target = meal_target.protein_target / meal_target.calo_quota
        wrong = [d for d in pool
                 if abs(d.protein_pp * 4 / max(d.calories, 1) - protein_ratio_target) > 0.15]
        return wrong if wrong else pool

    return pool


def protein_pct_calo(dish: Dish) -> float:
    """%calo-từ-đạm = protein_g * 4 kcal/g / tổng kcal — ĐÚNG ĐƠN VỊ."""
    if dish.calories <= 0:
        return 0.0
    return dish.protein_pp * 4 / dish.calories


def fat_pct_calo(dish_or_meal) -> float:
    """%calo-từ-fat = fat_g * 9 kcal/g / tổng kcal."""
    kcal = dish_or_meal.calories if hasattr(dish_or_meal, "calories") else dish_or_meal.total_kcal
    fat_g = dish_or_meal.fat_pp if hasattr(dish_or_meal, "fat_pp") else dish_or_meal.total_fat_g
    if kcal <= 0:
        return 0.0
    return fat_g * 9 / kcal


# ── build_rice_meal (viết lại hoàn toàn — greedy theo ngân sách) ─────
def build_rice_meal(protein_dish: Dish, soup_pool: List[Dish],
                    veggie_pool: List[Dish], meal_target: MealTarget) -> Meal:
    """
    Xây dựng bữa rice_meal:
    - Bắt buộc: Món chính, Cơm
    - Nếu calo không đủ sẽ giảm dần kích thước món phụ trước
    """
    same_diet_soup   = [d for d in soup_pool   if d.diet_type == protein_dish.diet_type]
    same_diet_veggie = [d for d in veggie_pool if d.diet_type == protein_dish.diet_type]

    chosen = [protein_dish]
    running_kcal = protein_dish.calories

    # 1. Thêm Canh 
    soup_added = False
    if same_diet_soup:
        target = meal_target.calo_quota * SOUP_TARGET_RATIO
        candidate = min(same_diet_soup, key=lambda d: abs(d.calories - target))
        
        if running_kcal + candidate.calories + RICE_FLOOR_KCAL <= meal_target.calo_quota * MEAL_KCAL_TOLERANCE:
            chosen.append(candidate)
            running_kcal += candidate.calories
            soup_added = True

    # 2. Thêm Rau phụ 
    veggie_added = False
    if same_diet_veggie:
        target = meal_target.calo_quota * VEGGIE_TARGET_RATIO
        affordable = [d for d in same_diet_veggie
                      if running_kcal + d.calories + RICE_FLOOR_KCAL 
                         <= meal_target.calo_quota * MEAL_KCAL_TOLERANCE]
        
        if affordable:
            veggie = max(affordable, key=lambda d: d.fiber_pp / max(d.calories, 1))
            chosen.append(veggie)
            running_kcal += veggie.calories
            veggie_added = True
        else:
            # Nếu không đủ chỗ, thử lấy món rau nhỏ nhất có thể
            smallest_veggie = min(same_diet_veggie, key=lambda d: d.calories)
            if running_kcal + smallest_veggie.calories + RICE_FLOOR_KCAL <= meal_target.calo_quota * 1.15:
                chosen.append(smallest_veggie)
                running_kcal += smallest_veggie.calories
                veggie_added = True

    # 3. Thêm Cơm (luôn có)
    remaining_kcal = max(meal_target.calo_quota - running_kcal, RICE_FLOOR_KCAL)
    rice_g = remaining_kcal / Rice.RICE_KCAL_PER_100G * 100
    rice_g = max(RICE_MIN_PORTION_G, min(rice_g, RICE_MAX_PORTION_G))
    
    rice = Rice(portion_g=rice_g)
    chosen.append(rice)

    # Tính tổng
    return Meal(
        dishes=chosen,
        total_kcal=round(sum(getattr(d, 'calories', 0) for d in chosen), 2),
        total_protein_g=round(sum(getattr(d, 'protein_pp', 0) for d in chosen), 2),
        total_fat_g=round(sum(getattr(d, 'fat_pp', 0) for d in chosen), 2),
        total_fiber_g=round(sum(getattr(d, 'fiber_pp', 0) for d in chosen), 2),
        total_sugar_g=round(sum(getattr(d, 'sugar_pp', 0) for d in chosen), 2),
    )


def build_standalone_meal(dish: Dish, meal_id: str) -> Meal:
    return Meal(
        dishes=[dish],
        total_kcal=dish.calories, total_protein_g=dish.protein_pp,
        total_fat_g=dish.fat_pp, total_fiber_g=dish.fiber_pp, total_sugar_g=dish.sugar_pp,
        meal_type="snack" if meal_id == "snack" else "standalone",
    )


# ── CBF: user-profile vector & dish-feature vector ───────────────────
def get_all_feature_values(food_db: List[Dish]) -> List[str]:
    """Liệt kê toàn bộ feature value cố định xuất hiện trong food_db."""
    values = set()
    for d in food_db:
        for s in d.protein_sources:
            values.add(f"protein_source:{s}")
        values.add(f"calo_band:{calo_band(d.calories)}")
        values.add(f"diet_type:{d.diet_type}")
        values.add(f"meal_category:{d.dish_type}")
    return sorted(values)


def calo_band(kcal: float) -> str:
    if kcal < 300:
        return "low"
    if kcal <= 500:
        return "mid"
    return "high"


def dish_has_feature(dish: Dish, feature_value: str) -> bool:
    key, val = feature_value.split(":", 1)
    if key == "protein_source":
        return val in dish.protein_sources
    if key == "calo_band":
        return calo_band(dish.calories) == val
    if key == "diet_type":
        return dish.diet_type == val
    if key == "meal_category":
        return dish.dish_type == val
    return False


def build_dish_feature_vector(dish: Dish, all_feature_values: List[str]) -> np.ndarray:
    return np.array([1.0 if dish_has_feature(dish, fv) else 0.0 for fv in all_feature_values])


def build_user_profile_vector(eaten_log: List[EatenEntry], food_db: Dict[int, Dish],
                               all_feature_values: List[str]) -> np.ndarray:
    """
    Mean rating per feature value, default 3.0 nếu chưa gặp. Normalize [0,1].
    Dùng dish_ratings (rating riêng từng món) — không dùng meal-level rating.
    """
    profile = np.zeros(len(all_feature_values))
    counts = np.zeros(len(all_feature_values))

    for entry in eaten_log:
        for fid, rating in entry.dish_ratings.items():
            dish = food_db.get(fid)
            if dish is None:
                continue
            for i, fv in enumerate(all_feature_values):
                if dish_has_feature(dish, fv):
                    profile[i] += rating
                    counts[i] += 1

    mask = counts > 0
    profile[mask] = profile[mask] / counts[mask]
    profile[~mask] = 3.0
    return (profile - 1) / 4


def compute_cbf_score(dish: Dish, user_profile_vector: np.ndarray,
                       all_feature_values: List[str]) -> float:
    if user_profile_vector is None:
        return 0.0
    d_vec = build_dish_feature_vector(dish, all_feature_values)
    denom = np.linalg.norm(user_profile_vector) * np.linalg.norm(d_vec)
    if denom == 0:
        return 0.0
    return float(np.dot(user_profile_vector, d_vec) / denom)


# ── score_candidate / score_meal (ĐỒNG BỘ công thức) ─────────────────
def score_candidate(dish: Dish, user: UserProfile, daily_pref: DailyPreference,
                    meal_target: MealTarget, eaten_log: List[EatenEntry],
                    day: int, branch: str,
                    user_profile_vector=None,
                    all_feature_values=None
                    ) -> Tuple[float, float]:
    """
    Tính điểm cho candidate dish dựa trên:
    - nutrition_score: dựa trên macro ratio so với target
    - diversity_score: dựa trên số lần ăn gần đây (NO_REPEAT_DAYS)
    - preference_score: dựa trên protein_sources có match với daily_pref
    - bonus_fiber: reward khi fiber >= P75 (2.5g)
    - sugar_score: penalty khi sugar vượt P75 (7g), tối đa tại P95 (13g)
    - cbf_score: dựa trên content-based filtering
    Trả về (final_score, cbf_score)
    """
    protein_ratio_target = meal_target.protein_target / max(meal_target.calo_quota, 1)
    fat_ratio_target     = meal_target.fat_target     / max(meal_target.calo_quota, 1)

    kcal = max(dish.calories, 1)
    nutrition_score = max(0.0, 1 - (
        abs(dish.protein_pp * 4 / kcal - protein_ratio_target) +
        abs(dish.fat_pp    * 9 / kcal - fat_ratio_target)
    ) / 2)

    n_recent = sum(1 for e in eaten_log
                   if e.protein_dish_id == dish.food_id
                   and day - NO_REPEAT_DAYS <= e.date < day)
    diversity_score = 1 - (n_recent / NO_REPEAT_DAYS)

    pref_sources   = set(daily_pref.get_protein_sources())
    actual_sources = set(dish.protein_sources)
    preference_score = 1.0 if (actual_sources & pref_sources) else 0.5

    bonus_fiber = min(dish.fiber_pp / 2.5, 1.0)

    sugar_penalty = max(0.0, (dish.sugar_pp - 7.0) / (13.0 - 7.0))
    sugar_score   = 1.0 - min(sugar_penalty, 1.0)

    # CBF
    cbf_score = 0.0 if branch == "cold_start" else compute_cbf_score(
        dish, user_profile_vector, all_feature_values
    )
    # Blend cbf theo branch
    cbf_weight = {"cold_start": 0.0, "warmup": 0.15, "full": 0.25}.get(branch, 0.0)
    base_score = (0.45 * nutrition_score
                  + 0.25 * diversity_score
                  + 0.20 * preference_score
                  + 0.10 * bonus_fiber
                  + 0.05 * sugar_score)
    final_score = (1 - cbf_weight) * base_score + cbf_weight * cbf_score

    return final_score, cbf_score


def score_meal(meal: Meal, meal_target: MealTarget, daily_pref: DailyPreference,
               eaten_log: List[EatenEntry], protein_dish_id: int, day: int) -> float:
    protein_ratio_target = meal_target.protein_target / meal_target.calo_quota
    fat_ratio_target = meal_target.fat_target / meal_target.calo_quota

    nutrition_score = max(0.0, 1 - np.mean([
        abs(meal.total_protein_g * 4 / meal.total_kcal - protein_ratio_target) if meal.total_kcal > 0 else 1,
        abs(meal.total_fat_g * 9 / meal.total_kcal - fat_ratio_target) if meal.total_kcal > 0 else 1,
    ]))

    n_recent = sum(1 for e in eaten_log
                   if e.protein_dish_id == protein_dish_id
                   and day - NO_REPEAT_DAYS <= e.date < day)
    diversity_score = 1 - min(n_recent / NO_REPEAT_DAYS, 1.0)

    protein_dish = meal.dishes[0]
    pref_sources = set(daily_pref.get_protein_sources())
    actual_sources = set(protein_dish.protein_sources)
    preference_score = 1.0 if (actual_sources & pref_sources) else 0.5

    bonus_fiber = min(meal.total_fiber_g / 2.5, 1.0)
    sugar_penalty = max(0.0, (meal.total_sugar_g - 7.0) / (13.0 - 7.0))
    sugar_score = 1.0 - min(sugar_penalty, 1.0)

    return (0.45 * nutrition_score + 0.25 * diversity_score
            + 0.20 * preference_score + 0.10 * bonus_fiber + 0.05 * sugar_score)

def compute_meal_target(user: UserProfile, daily_pref: DailyPreference,
                         meal_id: str) -> MealTarget:
    tdee = user.tdee_final
    ratio = MACRO_RATIO[user.goal]
 
    has_snack = daily_pref.has_snack
    meal_ratios = MEAL_RATIOS_BY_GOAL if has_snack else MEAL_RATIOS_BY_GOAL_no_snack
 
    r = meal_ratios[user.goal].get(meal_id, 0.25)  # 0.25 là giá `fallback` nếu meal_id không có trong dict
    calo_quota = tdee * r
 
    protein_target = calo_quota * ratio["protein"]
    fat_target     = calo_quota * ratio["fat"]
 
    # Xác định mode
    if meal_id == "breakfast":
        mode = "standalone"
    elif meal_id == "snack":
        mode = "snack"
    else:
        m = daily_pref.get_mode(meal_id)
        mode = "rice_meal" if m == 0 else "standalone"
 
    return MealTarget(
        meal_id=meal_id,
        calo_quota=calo_quota,
        protein_target=protein_target,
        fat_target=fat_target,
        mode=mode,
    )
