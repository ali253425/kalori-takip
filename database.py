import json
import os

DATA_DIR = "data"
FOOD_DB_PATH = os.path.join(DATA_DIR, "food_db.json")
USERS_DB_PATH = os.path.join(DATA_DIR, "users.json")

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
    # Dizin yoksa oluştur
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- Auth System ---
def load_users():
    return load_json(USERS_DB_PATH, {})

def save_users(users):
    save_json(USERS_DB_PATH, users)

def get_user_dir(username):
    user_dir = os.path.join(DATA_DIR, username)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return user_dir

def register_user(username, password):
    users = load_users()
    if username in users:
        return False, "Kullanıcı adı zaten kullanımda."
    users[username] = {"password": password}
    save_users(users)
    get_user_dir(username) # Klasörü oluştur
    return True, "Kayıt başarılı."

def authenticate_user(username, password):
    users = load_users()
    if username in users and users[username]["password"] == password:
        return True
    return False

# --- User Paths Helper ---
def get_user_file(username, filename):
    return os.path.join(get_user_dir(username), filename)

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
def load_user_profile(username):
    default_profile = {
        "age": 30,
        "gender": "Erkek",
        "weight_kg": 75.0,
        "height_cm": 180.0,
        "activity_level": "Orta",
        "hedef": "Kilo Koruma"
    }
    path = get_user_file(username, "user_profile.json")
    return load_json(path, default_profile)

def save_user_profile(username, profile):
    path = get_user_file(username, "user_profile.json")
    save_json(path, profile)

def calculate_bmr(profile):
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
    return w * 0.000628

# --- User Records (Daily) ---
def load_user_records(username):
    path = get_user_file(username, "user_records.json")
    return load_json(path, {})

def save_user_records(username, records):
    path = get_user_file(username, "user_records.json")
    save_json(path, records)

def load_history(username):
    path = get_user_file(username, "history.json")
    return load_json(path, {})

def save_history(username, history_data):
    path = get_user_file(username, "history.json")
    save_json(path, history_data)

def update_daily_snapshot(username, date_str, snapshot):
    history = load_history(username)
    history[date_str] = snapshot
    save_history(username, history)

def get_daily_record(username, date_str):
    records = load_user_records(username)
    if date_str not in records:
        records[date_str] = {
            "steps": 0,
            "foods": [],
            "activities": []
        }
        save_user_records(username, records)
    return records[date_str]

def update_daily_record(username, date_str, new_record):
    records = load_user_records(username)
    records[date_str] = new_record
    save_user_records(username, records)

def calculate_total_burn(bmr, steps, exercise_minutes, activity_level):
    activity_multipliers = {
        "Hareketsiz": 1.2,
        "Hafif": 1.375,
        "Orta": 1.55,
        "Çok Hareketli": 1.725
    }
    multiplier = activity_multipliers.get(activity_level, 1.2)
    step_burn = steps * 0.04
    exercise_burn = exercise_minutes * 6
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
    return met * 98 * (duration_min / 60.0)