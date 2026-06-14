import streamlit st
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import difflib
import json
import time
import random

st.set_page_config(page_title="Tarihin İzleri Quiz", layout="centered", page_icon="🌍")

# --- DOSYA YOLLARI ---
SCORE_FILE = "highscores.json"
ROOM_FILE = "rooms.json"

# --- YEREL VERİ TABANI YARDIMCI FONKSİYONLARI ---
def load_highscores():
    if os.path.exists(SCORE_FILE):
        try:
            with open(SCORE_FILE, "r") as f:
                return json.load(f)
        except:
            return {"Karışık": 0, "Kolay": 0, "Orta": 0, "Zor": 0}
    return {"Karışık": 0, "Kolay": 0, "Orta": 0, "Zor": 0}

def save_highscore(zorluk, skor):
    scores = load_highscores()
    if skor > scores.get(zorluk, 0):
        scores[zorluk] = skor
        with open(SCORE_FILE, "w") as f:
            json.dump(scores, f)

def load_rooms():
    if os.path.exists(ROOM_FILE):
        try:
            with open(ROOM_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_rooms(rooms):
    with open(ROOM_FILE, "w", encoding="utf-8") as f:
        json.dump(rooms, f, ensure_ascii=False, indent=4)

# --- CSV VERİ SETİNİ OKU ---
@st.cache_data
def load_data():
    csv_yolu = 'veri-v2.csv' 
    if not os.path.exists(csv_yolu):
        st.error(f"🚨 '{csv_yolu}' dosyası bulunamadı!")
        return pd.DataFrame()
    try:
        df = pd.read_csv(csv_yolu)
        df = df.dropna(subset=['dogum_enlem', 'dogum_boylam', 'olum_enlem', 'olum_boylam'])
        return df
    except Exception as e:
        st.error(f"🚨 Veri okunurken hata: {e}")
        return pd.DataFrame()

orijinal_df = load_data()
if orijinal_df.empty:
    st.stop()

# --- HAFIZA (STATE) KONTROLLERİ ---
if 'ekran' not in st.session_state:
    st.session_state.ekran = "menu"
if 'oyun_verisi' not in st.session_state:
    st.session_state.oyun_verisi = None
if 'aktif_soru_index' not in st.session_state:
    st.session_state.aktif_soru_index = 0
if 'cevap_durumlari' not in st.session_state:
    st.session_state.cevap_durumlari = [] 
if 'kullanici_cevaplari' not in st.session_state:
    st.session_state.kullanici_cevaplari = []
if 'secilen_zorluk' not in st.session_state:
    st.session_state.secilen_zorluk = "Karışık"
if 'baslangic_zamani' not in st.session_state:
    st.session_state.baslangic_zamani = 0
if 'oda_kodu' not in st.session_state:
    st.session_state.oda_kodu = None
if 'rol' not in st.session_state:
    st.session_state.rol = None
if 'kullanici_adi' not in st.session_state:
    st.session_state.kullanici_adi = ""


# ==========================================
# EKRAN 1: ANA MENÜ (MOD SEÇİMLİ)
# ==========================================
if st.session_state.ekran == "menu":
    st.title("🌍 Tarihin İzleri Quiz")
    st.write("Hoş geldiniz! Oynamak istediğiniz modu seçin:")
    
    # İki modu birbirinden ayıran ana şalter
    mod = st.radio("Oyun Modu Seçin:", ["👤 Tek Oyunculu (Zamana Karşı)", "⚔️ Canlı 1v1 Düello"], horizontal=True)
    
    st.divider()
    
    # --- TEK OYUNCULU SEÇENEĞİ ---
    if "Tek Oyunculu" in mod:
        st.subheader("👤 Tek Kişilik Mod")
        st.write("200 saniye içinde 10 soruyu bilin. İstediğiniz soruya Combobox panelinden geri dönebilirsiniz.")
        
        scores = load_highscores()
        col_k, col_o = st.columns(2)
        col_k.metric("Rekor (Kolay)", f"{scores['Kolay']} / 10")
        col_o.metric("Rekor (Orta)", f"{scores['Orta']} / 10")
        col_z, col_m = st.columns(2)
        col_z.metric("Rekor (Zor)", f"{scores['Zor']} / 10")
        col_m.metric("Rekor (Karışık)", f"{scores['Karışık']} / 10")
        
        st.divider()
        zorluk_secimi = st.selectbox("Zorluk Seviyesini Seçin:", ["Karışık", "Kolay", "Orta", "Zor"], key="tek_zorluk")
        
        if st.button("🚀 Tek Kişilik Oyunu Başlat", use_container_width=True):
            if zorluk_secimi != "Karışık":
                filtrelenmis_df = orijinal_df[orijinal_df['zorluk'] == zorluk_secimi]
            else:
                filtrelenmis_df = orijinal_df
                
            soru_sayisi = min(10, len(filtrelenmis_df))
            st.session_state.oyun_verisi = filtrelenmis_df.sample(n=soru_sayisi).reset_index(drop=True)
            
            st.session_state.aktif_soru_index = 0
            st.session_state.cevap_durumlari = ["bos"] * soru_sayisi
            st.session_state.kullanici_cevaplari = [""] * soru_sayisi
            st.session_state.secilen_zorluk = zorluk_secimi
            st.session_state.baslangic_zamani = time.time()
            st.session_state.ekran = "oyun_tek"
            st.rerun()
            
    # --- DÜELLO SEÇENEĞİ ---
    else:
        st.subheader("⚔️ Canlı Düello Odası")
        st.write("Arkadaşınızla eş zamanlı kapışın! Soru başı **20 saniye** sınır vardır ve geri dönüş yoktur.")
        
        st.session_state.kullanici_adi = st.text_input("Takma Adınız (Username):", st.session_state.kullanici_adi).strip()
        
        col_kur, col_katil = st.columns(2)
        
        with col_kur:
            st.write("### 🏠 Oda Kur")
            zorluk_secimi = st.selectbox("Oda Zorluğu:", ["Karışık", "Kolay", "Orta", "Zor"], key="duel_zorluk")
            if st.button("🚀 Oda Oluştur", use_container_width=True):
                if not st.session_state.kullanici_adi:
                    st.error("Lütfen önce bir takma ad girin!")
                else:
                    kod = str(random.randint(1000, 9999))
                    filtrelenmis = orijinal_df if zorluk_secimi == "Karışık" else orijinal_df[orijinal_df['zorluk'] == zorluk_secimi]
                    sorular_dict = filtrelenmis.sample(n=min(10, len(filtrelenmis))).to_dict(orient="records")
                    
                    rooms = load_rooms()
                    rooms[kod] = {
                        "status": "waiting", "zorluk": zorluk_secimi, "sorular": sorular_dict,
                        "current_question": 0, "q_start_time": 0,
                        "p1_name": st.session_state.kullanici_adi, "p2_name": "",
                        "p1_status": "waiting", "p2_status": "waiting",
                        "p1_answer": "", "p2_answer": "",
                        "p1_score": 0, "p2_score": 0
                    }
                    save_rooms(rooms)
                    st.session_state.oda_kodu = kod
                    st.session_state.rol = "p1"
                    st.session_state.ekran = "bekleme_duel"
                    st.rerun()

        with col_katil:
            st.write("### 🔑 Odaya Katıl")
            girilen_kod = st.text_input("4 Haneli Oda Kodu:", "").strip()
            if st.button("🤝 Giriş Yap", use_container_width=True):
                rooms = load_rooms()
                if not st.session_state.kullanici_adi:
                    st.error("Lütfen önce bir takma ad girin!")
                elif girilen_kod not in rooms:
                    st.error("Oda bulunamadı!")
                elif rooms[girilen_kod]["p2_name"] != "":
                    st.error("Bu oda dolu!")
                else:
                    rooms[girilen_kod]["p2_name"] = st.session_state.kullanici_adi
                    rooms[girilen_kod]["status"] = "playing"
                    rooms[girilen_kod]["q_start_time"] = time.time()
                    save_rooms(rooms)
                    st.session_state.oda_kodu = girilen_kod
                    st.session_state.rol = "p2"
                    st.session_state.ekran = "oyun_duel"
                    st.rerun()


# ==========================================
# EKRAN 2: TEK OYUNCULU OYUN ALANI
# ==========================================
elif st.session_state.ekran == "oyun_tek":
    soru_sayisi = len(st.session_state.oyun_verisi)
    gecen_sure = time.time() - st.session_state.baslangic_zamani
    kalan_sure = int(max(0, 200 - gecen_sure))
    
    if kalan_sure <= 0:
        st.warning("⏱️ SÜRE BİTTİ!")
        time.sleep(1)
        st.session_state.ekran = "sonuc_tek"
        st.rerun()

    timer_html = f"""<div style="font-family: Arial; font-size: 20px; font-weight: bold; color: #e74c3c; text-align: center; padding: 8px; border: 2px solid #e74c3c; border-radius: 8px; background-color: #fcebeb; margin-bottom: 10px;">⏱️ Kalan: <span id="timer">{kalan_sure}</span> saniye</div>
    <script>var timeLeft = {kalan_sure}; var timerEl = document.getElementById('timer'); var x = setInterval(function() {{ timeLeft--; if (timeLeft <= 0) {{ clearInterval(x); timerEl.parentElement.innerHTML = "⏱️ SÜRE DOLDU!"; }} else {{ timerEl.innerHTML = timeLeft; }} }}, 1000);</script>"""
    components.html(timer_html, height=60)

    # Senin istediğin o harika Combobox navigasyonu
    def soru_formati(i):
        durum = st.session_state.cevap_durumlari[i]
        if durum == "dogru": return f"🟢 Soru {i+1} (Doğru)"
        elif durum == "yanlis": return f"🔴 Soru {i+1} (Yanlış)"
        else: return f"⚪ Soru {i+1} (Boş)"

    secilen_soru = st.selectbox("📌 Gitmek istediğiniz soruyu seçin:", options=range(soru_sayisi), index=st.session_state.aktif_soru_index, format_func=soru_formati)
    if secilen_soru != st.session_state.aktif_soru_index:
        st.session_state.aktif_soru_index = secilen_soru
        st.rerun()
                
    st.divider()
    aktif_index = st.session_state.aktif_soru_index
    mevcut_kisi = st.session_state.oyun_verisi.iloc[aktif_index]
    st.write(f"**Soru {aktif_index + 1} / {soru_sayisi}** | ⭐ Skor: {st.session_state.cevap_durumlari.count('dogru')}")

    # Harita (Aynı kaldı)
    dogum_enlem, dogum_boylam, olum_enlem, olum_boylam = mevcut_kisi['dogum_enlem'], mevcut_kisi['dogum_boylam'], mevcut_kisi['olum_enlem'], mevcut_kisi['olum_boylam']
    merkez_enlem, merkez_boylam = (dogum_enlem + olum_enlem) / 2, (dogum_boylam + olum_boylam) / 2
    if abs(dogum_enlem - olum_enlem) < 0.1 and abs(dogum_boylam - olum_boylam) < 0.1:
        olum_enlem -= 0.6; olum_boylam += 0.6

    m = folium.Map(location=[merkez_enlem, merkez_boylam], zoom_start=4, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri")
    c_style = "font-family: Arial; font-weight: bold; font-size: 14px; padding: 4px 8px; border-radius: 6px; box-shadow: 2px 2px 5px rgba(0,0,0,0.5); white-space: nowrap;"
    folium.Marker([dogum_enlem, dogum_boylam], icon=folium.DivIcon(html=f"""<div style="display: flex; align-items: center; transform: translate(-50%, -100%);"><span style='font-size: 20px; margin-right: 4px;'>👶</span><span style="{c_style} color: #2ecc71; background-color: rgba(0,0,0,0.75);">{mevcut_kisi['dogum_yil']}</span></div>""")).add_to(m)
    folium.Marker([olum_enlem, olum_boylam], icon=folium.DivIcon(html=f"""<div style="display: flex; align-items: center; transform: translate(-50%, -100%);"><span style='font-size: 20px; margin-right: 4px;'>⚰️</span><span style="{c_style} color: #e74c3c; background-color: rgba(0,0,0,0.75);">{mevcut_kisi['olum_yil']}</span></div>""")).add_to(m)
    st_folium(m, height=330, use_container_width=True)

    durum = st.session_state.cevap_durumlari[aktif_index]
    if durum == "bos":
        tahmin = st.text_input("Bu tarihi kişilik kimdir?", key=f"tahmin_input_{aktif_index}")
        c_cev, c_gec = st.columns(2)
        with c_cev:
            if st.button("✔️ Cevapla", use_container_width=True):
                def tr_lower(text): return str(text).replace('I', 'ı').replace('İ', 'i').strip().lower()
                tam_benzerlik = difflib.SequenceMatcher(None, tr_lower(tahmin), tr_lower(mevcut_kisi['isim'])).ratio()
                alt_kume = len(tahmin.split()) > 0 and all(any(difflib.SequenceMatcher(None, tk, ik).ratio() >= 0.75 for ik in tr_lower(mevcut_kisi['isim']).split()) for tk in tr_lower(tahmin).split())
                st.session_state.cevap_durumlari[aktif_index] = "dogru" if (tam_benzerlik >= 0.80 or alt_kume) else "yanlis"
                st.session_state.kullanici_cevaplari[aktif_index] = tahmin
                st.rerun()
        with c_gec:
            if st.button("Pas Geç ➡️", use_container_width=True):
                st.session_state.aktif_soru_index = (aktif_index + 1) % soru_sayisi
                st.rerun()
    else:
        if durum == "dogru": st.success(f"🎉 Doğru Bildiniz! Cevap: **{mevcut_kisi['isim']}**")
        else: st.error(f"❌ Yanlış! Senin Yanıtın: '{st.session_state.kullanici_cevaplari[aktif_index]}' | Doğru: **{mevcut_kisi['isim']}**")
        
        if st.button("Sonraki Soruya Geç ➡️", use_container_width=True):
            st.session_state.aktif_soru_index = (aktif_index + 1) % soru_sayisi
            st.rerun()
            
        if "bos" not in st.session_state.cevap_durumlari:
            if st.button("Tüm Sorular Tamamlandı! Sonuçları Gör 🏆", use_container_width=True):
                save_highscore(st.session_state.secilen_zorluk, st.session_state.cevap_durumlari.count("dogru"))
                st.session_state.ekran = "sonuc_tek"
                st.rerun()
            
    st.divider()
    if st.button("Oyunu Erken Bitir ve Sonuçları Gör 🛑", type="secondary"):
        save_highscore(st.session_state.secilen_zorluk, st.session_state.cevap_durumlari.count("dogru"))
        st.session_state.ekran = "sonuc_tek"
        st.rerun()


# ==========================================
# EKRAN 3: TEK OYUNCULU SONUÇ ÖZETİ
# ==========================================
elif st.session_state.ekran == "sonuc_tek":
    st.balloons()
    st.title("🏆 Oyun Bitti!")
    soru_sayisi = len(st.session_state.oyun_verisi)
    skor = st.session_state.cevap_durumlari.count("dogru")
    st.markdown(f"<h2 style='text-align: center; color: #4CAF50;'>{st.session_state.secilen_zorluk} Seviye Skoru: {skor} / {soru_sayisi}</h2>", unsafe_allow_html=True)
    
    st.write("### 📝 Soru Özeti")
    for i in range(soru_sayisi):
        durum = st.session_state.cevap_durumlari[i]
        kisi_ismi = st.session_state.oyun_verisi.iloc[i]['isim']
        if durum == "dogru": st.markdown(f"**Soru {i+1}:** 🟢 Doğru (**{kisi_ismi}**)")
        elif durum == "yanlis": st.markdown(f"**Soru {i+1}:** 🔴 Yanlış (Yanıtın: *'{st.session_state.kullanici_cevaplari[i]}'* | Doğru Cevap: **{kisi_ismi}**)")
        else: st.markdown(f"**Soru {i+1}:** ⚪ Boş (Doğru Cevap: **{kisi_ismi}**)")
            
    st.divider()
    if st.button("🔄 Ana Menüye Dön", use_container_width=True):
        st.session_state.ekran = "menu"
        st.rerun()


# ==========================================
# EKRAN 4: DÜELLO LOBİSİ (BEKLEME)
# ==========================================
elif st.session_state.ekran == "bekleme_duel":
    st_autorefresh(interval=1000, key="lobby_refresh")
    st.title("⏳ Rakip Bekleniyor...")
    st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>ODA KODU: {st.session_state.oda_kodu}</h1>", unsafe_allow_html=True)
    room = load_rooms().get(st.session_state.oda_kodu)
    if room and room["status"] == "playing":
        st.session_state.ekran = "oyun_duel"
        st.rerun()


# ==========================================
# EKRAN 5: CANLI DÜELLO OYUN ALANI
# ==========================================
elif st.session_state.ekran == "oyun_duel":
    st_autorefresh(interval=1000, key="game_refresh")
    rooms = load_rooms()
    room = rooms.get(st.session_state.oda_kodu)
    if not room: st.error("Oda kapandı!"); st.stop()
        
    rol, rakip_rol = st.session_state.rol, ("p2" if st.session_state.rol == "p1" else "p1")
    q_idx = room["current_question"]
    sorular = room["sorular"]
    
    if room["status"] == "finished" or q_idx >= len(sorular):
        st.session_state.ekran = "sonuc_duel"; st.rerun()
        
    mevcut_kisi = sorular[q_idx]
    kalan_sure = int(max(0, 20 - (time.time() - room["q_start_time"])))
    both_submitted = (room["p1_status"] == "submitted" and room["p2_status"] == "submitted")
    
    if kalan_sure <= 0 or both_submitted:
        if q_idx < len(sorular) - 1:
            room["current_question"] += 1; room["q_start_time"] = time.time()
            room["p1_status"], room["p2_status"] = "waiting", "waiting"
            room["p1_answer"], room["p2_answer"] = "", ""
            save_rooms(rooms); st.rerun()
        else:
            room["status"] = "finished"; save_rooms(rooms); st.rerun()

    st.title("⚔️ Canlı Düello")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Siz ({room[rol+'_name']})", f"{room[rol+'_score']} P")
    c2.markdown(f"<h3 style='text-align:center; color:red;'>⏱️ {kalan_sure} sn</h3>", unsafe_allow_html=True)
    c3.metric(f"Rakip ({room[rakip_rol+'_name']})", f"{room[rakip_rol+'_score']} P")
    
    st.write(f"**Soru {q_idx + 1} / {len(sorular)}**")
    
    dogum_enlem, dogum_boylam, olum_enlem, olum_boylam = mevcut_kisi['dogum_enlem'], mevcut_kisi['dogum_boylam'], mevcut_kisi['olum_enlem'], mevcut_kisi['olum_boylam']
    merkez_enlem, merkez_boylam = (dogum_enlem + olum_enlem) / 2, (dogum_boylam + olum_boylam) / 2
    m = folium.Map(location=[merkez_enlem, merkez_boylam], zoom_start=4, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri")
    c_style = "font-family: Arial; font-weight: bold; font-size: 14px; padding: 4px 8px; border-radius: 6px; box-shadow: 2px 2px 5px rgba(0,0,0,0.5); white-space: nowrap;"
    folium.Marker([dogum_enlem, dogum_boylam], icon=folium.DivIcon(html=f"""<div style="display: flex; align-items: center; transform: translate(-50%, -100%);"><span style='font-size: 20px; margin-right: 4px;'>👶</span><span style="{c_style} color: #2ecc71; background-color: rgba(0,0,0,0.75);">{mevcut_kisi['dogum_yil']}</span></div>""")).add_to(m)
    folium.Marker([olum_enlem, olum_boylam], icon=folium.DivIcon(html=f"""<div style="display: flex; align-items: center; transform: translate(-50%, -100%);"><span style='font-size: 20px; margin-right: 4px;'>⚰️</span><span style="{c_style} color: #e74c3c; background-color: rgba(0,0,0,0.75);">{mevcut_kisi['olum_yil']}</span></div>""")).add_to(m)
    st_folium(m, height=330, use_container_width=True)

    if room[rol + "_status"] == "waiting":
        tahmin = st.text_input("Bu tarihi kişilik kimdir?", key=f"tahmin_duel_{q_idx}")
        if st.button("✔️ Cevapla", use_container_width=True):
            def tr_lower(text): return str(text).replace('I', 'ı').replace('İ', 'i').strip().lower()
            tam_benzerlik = difflib.SequenceMatcher(None, tr_lower(tahmin), tr_lower(mevcut_kisi['isim'])).ratio()
            alt_kume = len(tahmin.split()) > 0 and all(any(difflib.SequenceMatcher(None, tk, ik).ratio() >= 0.75 for ik in tr_lower(mevcut_kisi['isim']).split()) for tk in tr_lower(tahmin).split())
            if tam_benzerlik >= 0.80 or alt_kume:
                room[rol + "_score"] += 1; room[rol + "_answer"] = "correct"
            else: room[rol + "_answer"] = "wrong"
            room[rol + "_status"] = "submitted"; save_rooms(rooms); st.rerun()
    else:
        if room[rol + "_answer"] == "correct": st.success(f"🎉 Doğru Bildin! Cevap: **{mevcut_kisi['isim']}**")
        else: st.error(f"❌ Yanlış Bildin! Doğru Cevap: **{mevcut_kisi['isim']}**")
        if room[rakip_rol + "_status"] == "waiting": st.info("⏳ Rakibinin yanıt vermesi bekleniyor...")


# ==========================================
# EKRAN 6: DÜELLO SKOR TABLOSU
# ==========================================
elif st.session_state.ekran == "sonuc_duel":
    st.balloons(); st.title("🏆 Düello Bitti!")
    room = load_rooms().get(st.session_state.oda_kodu)
    if room:
        p1_n, p1_s, p2_n, p2_s = room["p1_name"], room["p1_score"], room["p2_name"], room["p2_score"]
        st.markdown(f"<h2 style='text-align: center; color: #4CAF50;'>{p1_n}: {p1_s} Puan | {p2_n}: {p2_s} Puan</h2>", unsafe_allow_html=True)
        if p1_s > p2_s: st.success(f"👑 KAZANAN: **{p1_n}**!")
        elif p2_s > p1_s: st.success(f"👑 KAZANAN: **{p2_n}**!")
        else: st.info("🤝 BERABERE!")
    if st.button("🔄 Ana Menüye Dön", use_container_width=True):
        st.session_state.ekran = "menu"; st.rerun()
