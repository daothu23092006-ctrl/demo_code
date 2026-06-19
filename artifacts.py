"""
artifacts.py — Chạy 1 LẦN (offline) từ eaten_log train, lưu cache để engine.py
chỉ load + infer, không tính lại CBF/CF mỗi request.
"""
import pickle
import numpy as np
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Tuple

from models import Dish, UserProfile, EatenEntry
from core_logic import get_all_feature_values, build_user_profile_vector, K_MIN_CLUSTER


@dataclass
class Artifacts:
    food_db_by_id: Dict[int, Dish]
    all_feature_values: List[str]
    user_profile_vectors: Dict[str, np.ndarray]      # CBF feature-based — None nếu cold_start
    similar_users_index: Dict[Tuple[str, str, str], List[str]]   # CF cluster
    popular_dishes_by_group: Dict[Tuple[str, str, str], List[int]]  # CF top dishes


def build_similar_users_index(users: List[UserProfile]) -> Dict[Tuple, List[str]]:
    """Group user_id theo (bmi_group, goal, age_group) — tra cứu O(1) lúc infer."""
    index: Dict[Tuple, List[str]] = defaultdict(list)
    for u in users:
        key = (u.bmi_group, u.goal, u.age_group)
        index[key].append(u.user_id)
    return dict(index)


def build_popular_dishes_by_group(
    similar_users_index: Dict[Tuple, List[str]],
    eaten_log_by_user: Dict[str, List[EatenEntry]],
) -> Dict[Tuple, List[int]]:
    """
    Top món phổ biến theo rating trung bình (dish_ratings) trong mỗi cluster.
    Chỉ nhóm có >= K_MIN_CLUSTER user mới được tính collaborative filtering.
    """
    result: Dict[Tuple, List[int]] = {}
    for key, uids in similar_users_index.items():
        if len(uids) < K_MIN_CLUSTER:
            continue
        dish_scores = defaultdict(list)
        for uid in uids:
            for entry in eaten_log_by_user.get(uid, []):
                for fid, rating in entry.dish_ratings.items():
                    dish_scores[fid].append(rating)
        ranked = sorted(dish_scores.items(), key=lambda x: -np.mean(x[1]))
        result[key] = [fid for fid, _ in ranked[:50]]
    return result


def build_artifacts(
    food_db: List[Dish],
    users: List[UserProfile],
    eaten_log_by_user: Dict[str, List[EatenEntry]],
    warmup_min: int = 5,
) -> Artifacts:
    food_db_by_id = {d.food_id: d for d in food_db}
    all_feature_values = get_all_feature_values(food_db)

    user_profile_vectors: Dict[str, np.ndarray] = {}
    for u in users:
        log = eaten_log_by_user.get(u.user_id, [])
        if len(log) < warmup_min:
            continue  # cold_start — không tạo vector, engine sẽ fallback rule-based
        user_profile_vectors[u.user_id] = build_user_profile_vector(
            log, food_db_by_id, all_feature_values
        )

    similar_users_index = build_similar_users_index(users)
    popular_dishes_by_group = build_popular_dishes_by_group(
        similar_users_index, eaten_log_by_user
    )

    return Artifacts(
        food_db_by_id=food_db_by_id,
        all_feature_values=all_feature_values,
        user_profile_vectors=user_profile_vectors,
        similar_users_index=similar_users_index,
        popular_dishes_by_group=popular_dishes_by_group,
    )


def save_artifacts(artifacts: Artifacts, path: str) -> None:
    with open(path, "wb") as f:
        pickle.dump(artifacts, f)


def load_artifacts(path: str) -> Artifacts:
    with open(path, "rb") as f:
        return pickle.load(f)