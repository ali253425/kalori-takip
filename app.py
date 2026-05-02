import streamlit as st
import pandas as pd
import plotly.express as px
import database as db
import datetime
import calendar

# Mobil ve genel görünüm için sayfa ayarı
st.set_page_config(page_title="Kalori ve Aktivite Takip", page_icon="🍏", layout="wide", initial_sidebar_state="collapsed")

# Takvimden tıklanıp gelinen tarih varsa yakala
if "date" in st.query_params:
    st.session_state.selected_history_date = st.query_params["date"]
    st.query_params.clear()

# Özel CSS (Mobil Uyumluluk ve Görsellik için)
st.markdown("""
<style>
    /* Metrik kutularının daha estetik görünmesi için */
    div[data-testid="metric-container"] {
        background-color: rgba(28, 131, 225, 0.1);
        border: 1px solid rgba(28, 131, 225, 0.2);
        padding: 5% 5% 5% 10%;
        border-radius: 10px;
    }
    /* Mobilde paddingleri daraltma */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    /* İlerleme çubuğu etiketleri için margin ayarı */
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    
    /* Takvim CSS Grid Yapısı */
    .calendar-grid { 
        display: grid; 
        grid-template-columns: repeat(7, 1fr); 
        gap: 4px; 
        width: 100%; 
        margin-bottom: 20px;
    }
    .calendar-day { 
        text-align: center; 
        padding: 10px 2px; 
        border-radius: 6px; 
        font-size: 14px;
        background-color: rgba(128, 128, 128, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.2);
        color: inherit !important;
        text-decoration: none !important;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 55px;
        transition: transform 0.1s, background-color 0.2s;
    }
    .calendar-day:hover {
        transform: scale(1.05);
        background-color: rgba(128, 128, 128, 0.15);
    }
    .calendar-header {
        font-weight: bold;
        text-align: center;
        padding-bottom: 5px;
        font-size: 14px;
    }
    @media (max-width: 600px) {
        .calendar-day {
            font-size: 11px;
            padding: 5px 1px;
            min-height: 45px;
        }
        .calendar-header {
            font-size: 12px;
        }
    }
</style>
""", unsafe_allow_html=True)

# Sidebar - Date Selection
st.sidebar.title("📅 Tarih Seçimi")
selected_date = st.sidebar.date_input("Kayıt Tarihi", datetime.date.today())
date_str = selected_date.strftime("%Y-%m-%d")

# Load User Data
profile = db.load_user_profile()
bmr = db.calculate_bmr(profile)
cal_per_step = 0.045  # 1 adım = 0.045 kcal sabit

daily_record = db.get_daily_record(date_str)

# Dinamik TDEE (Limit) Hesaplaması
base_tdee = bmr * 1.2
step_cals = daily_record.get("steps", 0) * cal_per_step
act_cals = sum(item.get("calories", 0) for item in daily_record.get("activities", []))

hedef_secimi = profile.get("hedef", "Kilo Koruma")
dynamic_tdee = base_tdee + step_cals + act_cals

if hedef_secimi == "Yağ Yakma":
    dynamic_tdee -= 500
elif hedef_secimi == "Kas/Kilo Alma":
    dynamic_tdee += 500

food_db = db.load_food_db()

st.title(f"🍏 Kalori ve Aktivite Takibi - {date_str}")

# Sekmelerin sırası Günlük Özet başa alınacak şekilde güncellendi
tab_summary, tab_profile, tab_food, tab_activity, tab_history = st.tabs([
    "📊 Ana Sayfa (Özet)", 
    "👤 Profil ve Ayarlar", 
    "🍔 Besin Girişi", 
    "🏃 Aktivite", 
    "📅 Takvim"
])

with tab_summary:
    st.header("📊 Günlük İlerleme ve Özet")
    
    # Makro uyumluluğu için retro-kontrol (eski kayıtlarda makro olmayabilir)
    total_consumed = sum(item.get("calories", 0) for item in daily_record.get("foods", []))
    total_protein = sum(item.get("protein", 0) for item in daily_record.get("foods", []))
    total_carbs = sum(item.get("carbs", 0) for item in daily_record.get("foods", []))
    total_fat = sum(item.get("fat", 0) for item in daily_record.get("foods", []))
    
    total_activity_cals = sum(item.get("calories", 0) for item in daily_record.get("activities", []))
    current_steps = daily_record.get("steps", 0)
    total_step_cals = current_steps * cal_per_step
    total_burned = total_activity_cals + total_step_cals
    
    # Kalan kalori hakkını dinamik limite göre hesapla
    calorie_deficit = dynamic_tdee - total_consumed
    
    # Anlık durumu history.json'a kaydet
    if calorie_deficit >= 0:
        if hedef_secimi == "Yağ Yakma" and calorie_deficit > 1000:
            durum_kodu = "warning"
            durum_mesaj = "Çok Düşük (Kas Kaybı Riski)"
        else:
            durum_kodu = "success"
            durum_mesaj = "Yağ Yakımı Başarılı" if hedef_secimi == "Yağ Yakma" else "Hedefte"
    else:
        durum_kodu = "error"
        durum_mesaj = "Limit Aşıldı"
        
    db.update_daily_snapshot(date_str, {
        "alinan": total_consumed,
        "adim": current_steps,
        "sporlar": [act["name"] for act in daily_record.get("activities", [])],
        "net_durum": durum_mesaj,
        "durum_kodu": durum_kodu,
        "limit": dynamic_tdee
    })
    
    # --- İlerleme Çubukları (Progress Bars) ---
    st.subheader("🎯 Günlük Hedefler")
    
    # Akıllı Metinler (Smart Texts)
    if total_consumed <= dynamic_tdee:
        if hedef_secimi == "Yağ Yakma" and calorie_deficit > 1000:
            st.warning("⚠️ Çok Az Yedin, Kas Kaybı Riski!")
        else:
            st.success("✨ Harika! Hedefindesin.")
    else:
        st.error(f"🚨 Hedef aşıldı! Fazla Kalori: {total_consumed - dynamic_tdee:.0f} kcal")
    
    col_prog1, col_prog2 = st.columns(2)
    
    with col_prog1:
        st.write(f"**Kalori Alımı:** {total_consumed:.0f} / {dynamic_tdee:.0f} kcal")
        cal_prog = min(total_consumed / dynamic_tdee, 1.0) if dynamic_tdee > 0 else 0.0
        st.progress(cal_prog)
            
    with col_prog2:
        st.info(f"🚶 **Bugün Atılan Adım:** {current_steps}")

    st.divider()

    # --- Makro Özetleri ---
    st.subheader("🥩 Günlük Makro Alımı")
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Protein", f"{total_protein:.1f} g")
    col_m2.metric("Karbonhidrat", f"{total_carbs:.1f} g")
    col_m3.metric("Yağ", f"{total_fat:.1f} g")
    
    st.divider()
    
    # --- Genel Durum (Metrikler) ---
    st.subheader("📉 Genel Durum")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Alınan Kalori", f"{total_consumed:.0f} kcal", "🍔")
    col2.metric("Yakılan (Akt+Adım)", f"{total_burned:.0f} kcal", "🔥")
    col3.metric("Günlük Limit (Dinamik)", f"{dynamic_tdee:.0f} kcal", "⚙️")
    
    if calorie_deficit >= 0:
        if hedef_secimi == "Yağ Yakma" and calorie_deficit > 1000:
            kalan_renk = "#FFC107" # Sarı
            kalan_durum = "Çok Düşük (Kas Kaybı Riski)"
        else:
            kalan_renk = "#4CAF50" # Yeşil
            kalan_durum = "Hedefte"
    else:
        kalan_renk = "#F44336" # Kırmızı
        kalan_durum = "Limit Aşıldı"
        
    with col4:
        st.markdown(f"""
        <div style="background-color: {kalan_renk}15; padding: 10px; border-radius: 8px; border-left: 5px solid {kalan_renk}; text-align: center;">
            <p style="margin:0; font-size: 14px; font-weight: bold; color: {kalan_renk};">Kalan Kalori</p>
            <h3 style="margin:5px 0; color: {kalan_renk};">{abs(calorie_deficit):.0f} kcal</h3>
            <small style="color: {kalan_renk}; font-weight: bold;">{kalan_durum}</small>
        </div>
        """, unsafe_allow_html=True)


with tab_profile:
    st.header("👤 Kullanıcı Profili")
    st.write("Bilgilerinizi güncelleyerek bazal metabolizma (BMR) değerinizi hesaplayın.")
    
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Yaşınız", min_value=10, max_value=120, value=profile.get("age", 30))
        weight = st.number_input("Kilonuz (kg)", min_value=30.0, max_value=300.0, value=profile.get("weight_kg", 75.0))
        height = st.number_input("Boyunuz (cm)", min_value=100.0, max_value=250.0, value=profile.get("height_cm", 180.0))
    with col2:
        gender = st.selectbox("Cinsiyetiniz", ["Erkek", "Kadın"], index=0 if profile.get("gender", "Erkek") == "Erkek" else 1)
        hedef_list = ["Yağ Yakma", "Kilo Koruma", "Kas/Kilo Alma"]
        hedef_val = profile.get("hedef", "Kilo Koruma")
        hedef_index = hedef_list.index(hedef_val) if hedef_val in hedef_list else 1
        secilen_hedef = st.selectbox("Hedefiniz", hedef_list, index=hedef_index)
        
    if st.button("Profili Kaydet", type="primary", use_container_width=True):
        profile["age"] = age
        profile["weight_kg"] = weight
        profile["height_cm"] = height
        profile["gender"] = gender
        profile["hedef"] = secilen_hedef
        db.save_user_profile(profile)
        st.success("Profiliniz başarıyla güncellendi!")
        st.rerun()
        
    st.info(f"💡 Güncel BMR (Bazal Metabolizma): **{bmr:.0f} kcal**")
    st.info(f"💡 Adım Başına Yakılan Kalori: **{cal_per_step:.4f} kcal**")

    st.divider()
    st.subheader("⚙️ Dinamik Kalori Limit Sistemi")
    st.write("Günlük kalori limitiniz (TDEE) **dinamik** olarak anlık hesaplanmaktadır:")
    st.markdown(f"- **Rölanti Limit (Sadece Yaşamak):** {base_tdee:.0f} kcal")
    st.markdown(f"- **Adımlardan Kazanılan:** +{step_cals:.0f} kcal")
    st.markdown(f"- **Spor ve Aktivitelerden Kazanılan:** +{act_cals:.0f} kcal")
    st.info(f"🎯 **Güncel Dinamik Hedefiniz:** **{dynamic_tdee:.0f} kcal**")

with tab_food:
    st.header("🍔 Besin Girişi")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Tükettiğiniz Besini Ekleyin")
        food_list = list(food_db.keys())
        selected_food = st.selectbox("Besin Arayın (Otomatik Filtre)", food_list)
        
        # Seçilen besinin 100 gram makrolarını göster
        if selected_food:
            food_info = food_db[selected_food]
            # Eski veri yapısına karşı koruma
            if isinstance(food_info, dict):
                c = food_info.get("calories", 0)
                p = food_info.get("protein", 0)
                cb = food_info.get("carbs", 0)
                f = food_info.get("fat", 0)
            else:
                c = food_info
                p, cb, f = 0, 0, 0
                
            st.caption(f"100g için: {c} kcal, {p}g Protein, {cb}g Karbonhidrat, {f}g Yağ")
            
        grams = st.number_input("Miktar (Gram)", min_value=1, value=100, step=10)
        
        if st.button("Besini Günlüğe Ekle", key="add_food", use_container_width=True):
            if isinstance(food_db[selected_food], dict):
                calories = (food_db[selected_food].get("calories", 0) / 100) * grams
                protein = (food_db[selected_food].get("protein", 0) / 100) * grams
                carbs = (food_db[selected_food].get("carbs", 0) / 100) * grams
                fat = (food_db[selected_food].get("fat", 0) / 100) * grams
            else:
                calories = (food_db[selected_food] / 100) * grams
                protein, carbs, fat = 0, 0, 0
                
            daily_record["foods"].append({
                "name": selected_food, 
                "grams": grams, 
                "calories": calories,
                "protein": protein,
                "carbs": carbs,
                "fat": fat
            })
            db.update_daily_record(date_str, daily_record)
            st.success(f"{grams}g {selected_food} eklendi ({calories:.1f} kcal).")
            st.rerun()
            
    with col2:
        st.subheader("Yeni Besin Tanımla")
        with st.form("custom_food_form"):
            new_food_name = st.text_input("Besin Adı")
            new_food_cals = st.number_input("100g Kalorisi", min_value=1, value=100)
            new_food_prot = st.number_input("100g Protein", min_value=0.0, value=0.0, step=0.1)
            new_food_carb = st.number_input("100g Karbonhidrat", min_value=0.0, value=0.0, step=0.1)
            new_food_fat = st.number_input("100g Yağ", min_value=0.0, value=0.0, step=0.1)
            
            submitted = st.form_submit_button("Veritabanına Ekle", use_container_width=True)
            if submitted and new_food_name:
                db.add_custom_food(new_food_name, new_food_cals, new_food_prot, new_food_carb, new_food_fat)
                st.success(f"{new_food_name} eklendi!")
                st.rerun()

    if daily_record["foods"]:
        st.subheader("Bugün Tüketilenler")
        for idx, food in enumerate(daily_record["foods"]):
            col_f1, col_f2 = st.columns([5, 1])
            with col_f1:
                st.markdown(f"🍔 **{food['name']}** - {food['grams']}g ({food['calories']:.0f} kcal) <br> <small style='color:gray;'>Pro: {food['protein']:.1f}g | Karb: {food['carbs']:.1f}g | Yağ: {food['fat']:.1f}g</small>", unsafe_allow_html=True)
            with col_f2:
                with st.popover("🗑️ Sil"):
                    st.write("Silmek istediğinize emin misiniz?")
                    if st.button("Evet, Sil", key=f"del_food_{idx}", type="primary"):
                        daily_record["foods"].pop(idx)
                        db.update_daily_record(date_str, daily_record)
                        st.rerun()
            st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)

with tab_activity:
    st.header("🏃 Aktivite ve Adımlar")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Adım Sayısı")
        steps = st.number_input("Bugünkü Adım Sayınız", min_value=0, value=daily_record.get("steps", 0), step=500)
        if st.button("Adımı Kaydet", use_container_width=True):
            daily_record["steps"] = steps
            db.update_daily_record(date_str, daily_record)
            st.success("Adım sayısı güncellendi!")
            st.rerun()
            
    with col2:
        st.subheader("Spor ve Aktivite Ekle")
        activity_list = list(db.ACTIVITY_MET.keys())
        selected_activity = st.selectbox("Aktivite Türü Seçin", activity_list)
        
        duration = st.number_input("Süre (Dakika)", min_value=1, value=30)
        
        if selected_activity == "Diğer (Manuel)":
            custom_name = st.text_input("Aktivite Adı")
            act_calories = st.number_input("Yakılan Kalori (Manuel)", min_value=1, value=150)
            final_activity_name = custom_name if custom_name else "Diğer Aktivite"
        else:
            met_value = db.ACTIVITY_MET[selected_activity]
            act_calories = db.calculate_activity_calories(met_value, duration)
            st.info(f"💡 Tahmini Yakılan Kalori: **{act_calories:.0f} kcal**")
            final_activity_name = selected_activity

        if st.button("Aktiviteyi Ekle", use_container_width=True):
            daily_record["activities"].append({"name": final_activity_name, "duration_min": duration, "calories": act_calories})
            db.update_daily_record(date_str, daily_record)
            st.success(f"{final_activity_name} eklendi!")
            st.rerun()
            
    if daily_record["activities"]:
        st.subheader("Bugünkü Aktiviteler")
        for idx, act in enumerate(daily_record["activities"]):
            col_a1, col_a2 = st.columns([5, 1])
            with col_a1:
                st.markdown(f"🏃 **{act['name']}** - {act.get('duration_min', 0)} dk ({act['calories']:.0f} kcal)")
            with col_a2:
                with st.popover("🗑️ Sil"):
                    st.write("Silmek istediğinize emin misiniz?")
                    if st.button("Evet, Sil", key=f"del_act_{idx}", type="primary"):
                        daily_record["activities"].pop(idx)
                        db.update_daily_record(date_str, daily_record)
                        st.rerun()
            st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)

with tab_history:
    st.header("📅 İnteraktif Takvim ve Geçmiş")
    
    history_data = db.load_history()
    
    if not history_data:
        st.info("Henüz kaydedilmiş geçmiş veri bulunmuyor.")
    else:
        if "cal_year" not in st.session_state:
            st.session_state.cal_year = datetime.datetime.now().year
        if "cal_month" not in st.session_state:
            st.session_state.cal_month = datetime.datetime.now().month
            
        cal_year = st.session_state.cal_year
        cal_month = st.session_state.cal_month
        
        # Türkçe ay isimleri için sözlük
        aylar = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
                 7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}
        
        col_prev, col_curr, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("⬅️", use_container_width=True):
                st.session_state.cal_month -= 1
                if st.session_state.cal_month == 0:
                    st.session_state.cal_month = 12
                    st.session_state.cal_year -= 1
                st.rerun()
                
        with col_curr:
            st.markdown(f"<h4 style='text-align: center; margin-top:5px;'>🗓️ {aylar[cal_month]} {cal_year}</h4>", unsafe_allow_html=True)
            
        with col_next:
            if st.button("➡️", use_container_width=True):
                st.session_state.cal_month += 1
                if st.session_state.cal_month == 13:
                    st.session_state.cal_month = 1
                    st.session_state.cal_year += 1
                st.rerun()
        
        days_of_week = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
        cal_html = '<div class="calendar-grid">'
        for day_name in days_of_week:
            cal_html += f'<div class="calendar-header">{day_name}</div>'
            
        cal = calendar.monthcalendar(cal_year, cal_month)
        for week in cal:
            for day in week:
                if day == 0:
                    cal_html += '<div class="calendar-day" style="background: transparent; border: none;"></div>'
                else:
                    date_key = f"{cal_year}-{cal_month:02d}-{day:02d}"
                    emoji = "⬜"
                    if date_key in history_data:
                        kodu = history_data[date_key]["durum_kodu"]
                        if kodu == "success": emoji = "🟢"
                        elif kodu == "error": emoji = "🔴"
                        else: emoji = "🟡"
                    
                    cal_html += f'<a href="?date={date_key}" target="_self" class="calendar-day">{emoji}<br>{day}</a>'
        cal_html += '</div>'
        st.markdown(cal_html, unsafe_allow_html=True)
        
        st.divider()
        
        selected_d = st.session_state.get("selected_history_date", None)
        if selected_d and selected_d in history_data:
            snap = history_data[selected_d]
            st.subheader(f"🔍 {selected_d} Detayları")
            
            st.markdown(f"**O gün toplam {snap['alinan']:.0f} kcal alındı.** (Dinamik Hedef: {snap['limit']:.0f} kcal)")
            
            sporlar_str = ", ".join(snap['sporlar']) if snap['sporlar'] else "Yok"
            st.markdown(f"**Atılan Adım:** {snap['adim']} | **Yapılan Sporlar:** {sporlar_str}")
            
            color = "green" if snap['durum_kodu'] == "success" else "red" if snap['durum_kodu'] == "error" else "orange"
            st.markdown(f"**Net Durum:** <span style='color:{color}; font-weight:bold;'>{snap['net_durum']}</span>", unsafe_allow_html=True)
            
        elif selected_d:
            st.info(f"{selected_d} tarihi için henüz bir kayıt bulunmuyor.")
        else:
            st.info("👆 Detaylarını görmek için yukarıdaki takvimden bir güne tıklayın.")
            
        st.divider()
        st.subheader("📈 Aylık Eğilim")
        history_df_data = []
        for d, snap in history_data.items():
            history_df_data.append({
                "Tarih": d,
                "Alınan": snap["alinan"],
                "Limit": snap["limit"]
            })
        if history_df_data:
            df = pd.DataFrame(history_df_data).sort_values(by="Tarih")
            fig = px.line(df, x="Tarih", y="Alınan", markers=True, title="Günlük Alınan Kalori vs Limit")
            fig.add_scatter(x=df["Tarih"], y=df["Limit"], mode='lines+markers', name='Dinamik Limit')
            st.plotly_chart(fig, use_container_width=True)
