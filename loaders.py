"""
loaders.py — Đọc CSV thành object. Đã sửa các lỗi phát hiện ở review trước:
- protein_sources của DailyPreference được split thành List[str]
- food_id fail-fast nếu thiếu
- Đồng bộ với models.py mới (get_protein_sources)
"""
import csv
from collections import defaultdict
from typing import List, Dict, Optional

from models import Dish, UserProfile, DailyPreference


def field(row: dict, name: str) -> Optional[str]:
    """Xử lý BOM dính vào tên cột đầu tiên khi file CSV lưu từ Excel/Sheets."""
    return row.get(name) or row.get(f"\ufeff{name}")


def normalize_diet_type(value: str) -> str:
    if not value:
        return ""
    text = value.strip().lower()
    if "mặn" in text or "man" in text:
        return "man"
    if "chay" in text:
        return "chay"
    return text


def load_food_db(path: str) -> List[Dish]:
    dishes = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            food_id_raw = field(row, "food_id")
            if not food_id_raw:
                raise ValueError(f"Thiếu food_id ở dòng: {row}")

            sources_raw = field(row, "protein_sources") or row.get("protein_sources_str", "")
            sources = [s.strip() for s in sources_raw.split("|") if s.strip()] if sources_raw else []

            dishes.append(Dish(
                food_id=int(food_id_raw),
                dish_name=row.get("dish_name", ""),
                dish_type=row.get("dish_type", ""),
                diet_type=normalize_diet_type(field(row, "diet_type") or row.get("diet_type", "")),
                meal_type=row.get("meal_type", ""),
                calories=float(row.get("calories") or 0.0),
                protein_pp=float(row.get("protein_pp") or 0.0),
                fat_pp=float(row.get("fat_pp") or 0.0),
                fiber_pp=float(row.get("fiber_pp") or 0.0),
                sugar_pp=float(row.get("sugar_pp") or 0.0),
                protein_sources=sources,
            ))
    return dishes


def load_users(path: str) -> List[UserProfile]:
    users = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            users.append(UserProfile(
                user_id=row["user_id"],
                persona_id=row["persona_id"],
                gender=row["gender"],
                age_group=row["age_group"],
                age=int(row["age"]),
                height_cm=float(row["height_cm"]),
                weight_kg=float(row["weight_kg"]),
                bmi=float(row["bmi"]),
                bmi_group=row["bmi_group"],
                activity_level=row["activity_level"],
                goal=row["goal"],
                bmr=float(row["bmr"]),
                tdee=float(row["tdee"]),
                tdee_final=float(row["tdee_final"]),
                tdee_clamped=row["tdee_clamped"].lower() == "true",
            ))
    return users


def load_daily_prefs(path: str) -> Dict[str, List[DailyPreference]]:
    prefs: Dict[str, List[DailyPreference]] = defaultdict(list)
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            # Xử lý protein_sources an toàn hơn
            sources_raw = row.get("protein_sources", "")
            sources = [s.strip() for s in sources_raw.split("|") if s.strip()]

            dp = DailyPreference(
                user_id=row["user_id"],
                date=int(row["date"]),
                diet_type=normalize_diet_type(row["diet_type"]),
                protein_sources=sources,          # List[str]
                lunch_mode=int(row["lunch_mode"]),
                dinner_mode=int(row["dinner_mode"]),
                has_snack=row["has_snack"].lower() == "true",
                snack_label=row.get("snack_label") if row.get("snack_label") else None,
            )
            prefs[dp.user_id].append(dp)

    # Sắp xếp theo ngày
    for uid in prefs:
        prefs[uid].sort(key=lambda x: x.date)
    return prefs