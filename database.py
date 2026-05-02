import json
import os

DATA_DIR = "data"
FOOD_DB_PATH = os.path.join(DATA_DIR, "food_db.json")
USER_PROFILE_PATH = os.path.join(DATA_DIR, "user_profile.json")
USER_RECORDS_PATH = os.path.join(DATA_DIR, "user_records.json")
HISTORY_PATH = os.path.join(DATA_DIR, "history.json")

def load_json(path, default_data):
    if not os.path.exists(path):
        save_json(path, default_data)
        return default_data
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default_data

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- Food Database ---
def load_food_db():
    return load_json(FOOD_DB_PATH, {})

def save_food_db(db):
    save_json(FOOD_DB_PATH, db)

def add_custom_food(name, calories, protein=0, carbs=0, fat=0):
    db = load_food_db()
    db[name] = {
        "calories": calories,
        "protein": protein,
        "carbs": carbs,
        "fat": fat
    }
    save_food_db(db)

# --- User Profile & Formulas ---
def load_user_profile():
    default_profile = {
        "age": 30,
        "gender": "Erkek",
        "weight_kg": 75.0,
        "height_cm": 180.0,
        "activity_level": "Orta",
        "hedef": "Kilo Koruma"
    }
    return load_json(USER_PROFILE_PATH, default_profile)

def save_user_profile(profile):
    save_json(USER_PROFILE_PATH, profile)

def calculate_bmr(profile):
    # Harris-Benedict Formula
    w = profile.get("weight_kg", 0)
    h = profile.get("height_cm", 0)
    a = profile.get("age", 0)
    gender = profile.get("gender", "Erkek")

    if gender == "Erkek":
        return 88.362 + (13.397 * w) + (4.799 * h) - (5.677 * a)
    else:
        return 447.593 + (9.247 * w) + (3.098 * h) - (4.330 * a)

def calculate_tdee(profile, bmr):
    activity_multipliers = {
        "Hareketsiz": 1.2,
        "Az Hareketli": 1.375,
        "Orta": 1.55,
        "Çok Hareketli": 1.725,
        "Ekstra Hareketli": 1.9
    }
    level = profile.get("activity_level", "Orta")
    multiplier = activity_multipliers.get(level, 1.55)
    return bmr * multiplier

def calculate_calorie_per_step(profile):
    w = profile.get("weight_kg", 70)
    # Roughly 0.04 calories for a 65-70kg person, scaling linearly.
    return w * 0.000628

# --- User Records (Daily) ---
def load_user_records():
    return load_json(USER_RECORDS_PATH, {})

def save_user_records(records):
    save_json(USER_RECORDS_PATH, records)

def load_history():
    return load_json(HISTORY_PATH, {})

def save_history(history_data):
    save_json(HISTORY_PATH, history_data)

def update_daily_snapshot(date_str, snapshot):
    history = load_history()
    history[date_str] = snapshot
    save_history(history)

def get_daily_record(date_str):
    records = load_user_records()
    if date_str not in records:
        records[date_str] = {
            "steps": 0,
            "foods": [],
            "activities": []
        }
        save_user_records(records)
    return records[date_str]

def update_daily_record(date_str, new_record):
    records = load_user_records()
    records[date_str] = new_record
    save_user_records(records)
def calculate_total_burn(bmr, steps, exercise_minutes, activity_level):
    activity_multipliers = {
        "Hareketsiz": 1.2,
        "Hafif": 1.375,
        "Orta": 1.55,
        "Çok Hareketli": 1.725
    }
    multiplier = activity_multipliers.get(activity_level, 1.2)
    step_burn = steps * 0.04
    exercise_burn = exercise_minutes * 6  # Ortalama 6 kcal / dk egzersiz
    return (bmr * multiplier) + step_burn + exercise_burn

# --- Activity Database (MET Values) ---
ACTIVITY_MET = {
    "Yürüyüş (Hafif Tempo)": 3.0,
    "Yürüyüş (Tempolu)": 4.5,
    "Koşu (Hafif Tempo)": 8.0,
    "Koşu (Tempolu)": 11.0,
    "Bisiklet (Hafif)": 6.0,
    "Bisiklet (Tempolu)": 10.0,
    "Yüzme": 8.0,
    "Fitness / Ağırlık Antrenmanı": 6.0,
    "Futbol": 10.0,
    "Basketbol": 8.0,
    "Tenis": 7.0,
    "Yoga / Pilates": 3.0,
    "Dans": 5.0,
    "Ev İşleri": 3.5,
    "Diğer (Manuel)": 1.0
}

def calculate_activity_calories(met, duration_min):
    # Formül: Kalori = MET * 98 * (Dakika / 60)
    return met * 98 * (duration_min / 60.0)