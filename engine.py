"""
engine.py — Production inference. Chỉ ĐỌC artifact đã build (không tính lại
CBF/CF từ đầu mỗi request). Tái sử dụng nguyên các hàm core_logic đã thiết
kế thống nhất với simulate eaten_log — không viết lại logic build bữa/scoring.
"""
from typing import List, Optional
from dataclasses import dataclass

from models import Dish, UserProfile, DailyPreference, MealTarget, Meal, EatenEntry
from artifacts import Artifacts
import core_logic as cl


@dataclass
class RecommendationResult:
    meal: Meal
    score: float
    branch: str
    cbf_score: float


class RecommendationEngine:
    def __init__(self, food_db: List[Dish], artifacts: Artifacts):
        self.food_db = food_db
        self.artifacts = artifacts
        self.protein_pool = [d for d in food_db if d.dish_type == "món chính"]
        self.soup_pool = [d for d in food_db if d.dish_type == "món canh"]
        self.veggie_pool = [d for d in food_db if d.dish_type == "món phụ"]
        self.standalone_pool = [d for d in food_db if d.dish_type == "món độc lập"]

    def _find_similar_users_pool(self, user: UserProfile) -> Optional[List[int]]:
        key = (user.bmi_group, user.goal, user.age_group)
        return self.artifacts.popular_dishes_by_group.get(key)

    def _protein_candidates(self, user: UserProfile, daily_pref: DailyPreference,
                             meal_target: MealTarget, meal_id: str, mode: str,
                             eaten_log: List[EatenEntry], day: int, branch: str) -> List[Dish]:
        
        base_pool = self.standalone_pool if mode == "standalone" else self.protein_pool

        # Gọi theo signature mới của core_logic
        candidates = cl.get_candidate_pool(
            user=user,
            day=day,
            meal_id=meal_id,
            meal_target=meal_target,
            daily_pref=daily_pref,
            food_db=base_pool,          
            eaten_log=eaten_log,
            slot_type="correct",
            relax=False
        )

        if not candidates:
            candidates = cl.get_candidate_pool(
                user=user,
                day=day,
                meal_id=meal_id,
                meal_target=meal_target,
                daily_pref=daily_pref,
                food_db=base_pool,
                eaten_log=eaten_log,
                slot_type="correct",
                relax=True
            )
        if not candidates:
            return []

        # Cold start branch
        if branch == "cold_start":
            protein_ratio_target = meal_target.protein_target / meal_target.calo_quota
            return sorted(candidates, key=lambda d: abs(cl.protein_pct_calo(d) - protein_ratio_target))

        # Content-based + Collaborative
        user_profile_vector = self.artifacts.user_profile_vectors.get(user.user_id)

        scored = [
            (d, cl.compute_cbf_score(d, user_profile_vector, self.artifacts.all_feature_values))
            for d in candidates
        ]
        scored.sort(key=lambda x: -x[1])
        content_pool_ids = {d.food_id for d, _ in scored[:20]}

        if mode == "rice_meal":
            similar_dish_ids = self._find_similar_users_pool(user) or []
            merged_ids = content_pool_ids | set(similar_dish_ids)
        else:
            merged_ids = content_pool_ids

        merged = [d for d in candidates if d.food_id in merged_ids]
        return merged if merged else candidates

    def recommend_meal(self, user: UserProfile, daily_pref: DailyPreference,
                        meal_target: MealTarget, meal_id: str,
                        eaten_log: List[EatenEntry], day: int, top_k: int = 10,
                        max_candidates_to_build: int = 30) -> List[RecommendationResult]:
        
        mode = cl.decide_mode(daily_pref, meal_id)
        meal_target.mode = mode
        branch = cl.get_branch(eaten_log)

        if mode == "snack":
            return self._recommend_snack(daily_pref, meal_target, eaten_log, day, top_k)

        protein_candidates = self._protein_candidates(
            user, daily_pref, meal_target, meal_id, mode, eaten_log, day, branch
        )
        if not protein_candidates:
            return []

        results = []
        for p in protein_candidates[:max_candidates_to_build]:
            meal = (cl.build_rice_meal(p, self.soup_pool, self.veggie_pool, meal_target)
                    if mode == "rice_meal" else cl.build_standalone_meal(p, meal_id))
            
            score = cl.score_meal(meal, meal_target, daily_pref, eaten_log, p.food_id, day)
            
            # CBF score
            user_profile_vector = self.artifacts.user_profile_vectors.get(user.user_id)
            cbf_score = cl.compute_cbf_score(p, user_profile_vector, self.artifacts.all_feature_values) \
                        if user_profile_vector is not None else 0.0

            results.append(RecommendationResult(
                meal=meal, 
                score=score, 
                branch=branch, 
                cbf_score=cbf_score
            ))

        results.sort(key=lambda r: -r.score)
        return results[:top_k]

    def _recommend_snack(self, daily_pref: DailyPreference, meal_target: MealTarget,
                          eaten_log: List[EatenEntry], day: int, top_k: int) -> List[RecommendationResult]:
        
        # Sửa gọi get_candidate_pool cho snack
        pool = cl.get_candidate_pool(
            user=None,                    # snack không cần user
            day=day,
            meal_id="snack",
            meal_target=meal_target,
            daily_pref=daily_pref,
            food_db=self.food_db,
            eaten_log=eaten_log,
            slot_type="snack"             # quan trọng
        )
        
        budget = meal_target.calo_quota
        pool = [d for d in pool if budget * 0.8 <= d.calories <= budget * 1.1]
        if not pool:
            return []

        import random
        scored = []
        for d in pool:
            calo_match = max(0.0, 1 - abs(d.calories - budget) / budget)
            score = 0.6 * calo_match + 0.4 * random.random()
            meal = cl.build_standalone_meal(d, "snack")
            scored.append(RecommendationResult(meal=meal, score=score, branch="snack", cbf_score=0.0))
        
        scored.sort(key=lambda r: -r.score)
        return scored[:top_k]