"""
models.py — Schema dùng chung cho toàn bộ hệ thống (pipeline thật + simulate eaten_log). 
Mọi field đã được khoá theo các quyết định thiết kế đã thống nhất.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class Dish:
    food_id: int
    dish_name: str
    dish_type: str          
    diet_type: str           
    meal_type: str           
    calories: float
    protein_pp: float
    fat_pp: float
    fiber_pp: float
    sugar_pp: float
    protein_sources: List[str]

    def meal_type_compatible(self, meal_id: str) -> bool:
        if meal_id == "breakfast":
            return "bữa sáng" in self.meal_type or (self.dish_type == "món độc lập" and "bữa sáng" in self.meal_type)
        if meal_id in ("lunch", "dinner"):
            return "bữa chính" in self.meal_type
        if meal_id == "snack":
            return "bữa phụ" in self.meal_type
        return False


@dataclass
class Rice:
    portion_g: float
    food_id: Optional[int] = None
    dish_name: str = "cơm trắng"
    dish_type: str = "rice"
    diet_type: str = "any"
    protein_pp: float = 0.0
    fat_pp: float = 0.0
    fiber_pp: float = 0.0
    sugar_pp: float = 0.0
    protein_sources: List[str] = field(default_factory=list)
    calories: float = field(init=False)

    RICE_KCAL_PER_100G = 130.0

    def __post_init__(self):
        self.calories   = self.portion_g * self.RICE_KCAL_PER_100G / 100
        self.protein_pp = self.portion_g * 2.7 / 100
        self.fat_pp     = self.portion_g * 0.3 / 100
        self.fiber_pp   = self.portion_g * 0.4 / 100
        self.sugar_pp   = 0.0


@dataclass
class UserProfile:
    user_id: str
    persona_id: str
    gender: str
    age_group: str
    age: int
    height_cm: float
    weight_kg: float
    bmi: float
    bmi_group: str
    activity_level: str
    goal: str
    bmr: float
    tdee: float
    tdee_final: float
    tdee_clamped: bool
    daily_prefs: List["DailyPreference"] = field(default_factory=list)


@dataclass
class DailyPreference:
    user_id: str
    date: int
    diet_type: str               
    protein_sources: List[str]   # Nên là List[str để đồng bộ production
    lunch_mode: int              
    dinner_mode: int
    has_snack: bool
    snack_label: Optional[str]   

    def get_mode(self, meal_id: str) -> int:
        if meal_id == "lunch":
            return self.lunch_mode
        if meal_id == "dinner":
            return self.dinner_mode
        return 1  # breakfast/snack luôn standalone

    def get_protein_sources(self) -> List[str]:
        """Hàm helper được core_logic và simulate dùng."""
        if isinstance(self.protein_sources, str):
            return [s.strip() for s in self.protein_sources.split("|") if s.strip()]
        if isinstance(self.protein_sources, list):
            return [s.strip() for s in self.protein_sources if isinstance(s, str)]
        return []


@dataclass
class MealTarget:
    meal_id: str
    calo_quota: float
    protein_target: float
    fat_target: float
    mode: str = ""   
    snack_label: Optional[str] = None
    snack_calo_budget: Optional[float] = None


@dataclass
class Meal:
    dishes: List          
    total_kcal: float
    total_protein_g: float
    total_fat_g: float
    total_fiber_g: float
    total_sugar_g: float
    meal_type: str = "rice_meal"


@dataclass
class EatenEntry:
    user_id: str
    date: int
    meal_id: str                       
    meal_type: str                     
    protein_dish_id: int               
    full_meal: str              
    total_kcal: float
    total_protein_g: float
    total_fat_g: float
    total_fiber_g: float
    total_sugar_g: float
    diet_type: str
    protein_sources_actual: List[str]
    protein_sources_pref: List[str]

    dish_ratings: Dict[int, int]       

    slot_type: str                     
    branch: str                        
    cbf_score: float
    final_score: float
    is_exploration: bool
    source_matched: bool


def get_meal_rating(entry: EatenEntry, food_db: Dict[int, Dish],
                     role_weight: Optional[Dict[str, float]] = None) -> Optional[float]:
    role_weight = role_weight or {"món chính": 0.5, "món canh": 0.25, "món phụ": 0.25}
    weighted_sum, weight_total = 0.0, 0.0
    for fid, rating in entry.dish_ratings.items():
        dish = food_db.get(fid)
        if dish is None:
            continue
        w = role_weight.get(dish.dish_type, 1.0)
        weighted_sum += rating * w
        weight_total += w
    return round(weighted_sum / weight_total, 2) if weight_total > 0 else None