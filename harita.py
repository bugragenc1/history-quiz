import streamlit as st
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

# --- ORTAK ODALAR VERİTABANI (SAYFALAR ARASI KÖPRÜ) ---
ROOM_FILE = "rooms.json"

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

# --- HAFIZA (STATE) KONTROLLERİ ---
if 'ekran' not in st.session_state:
    st.session_state.ekran = "menu"
if 'oda_kodu' not in st.session_state:
    st.session_state.oda_kodu = None
if 'rol' not in st.session_state:
    st.session_state.rol = None # 'p1' veya 'p2'
if 'kullanici_adi' not in st.session_state:
    st.session_state.kullanici_adi = ""

# ==========================================
# EKRAN 1: ANA MENÜ VE ODA KURMA / KATILMA
# ==========================================
if st.session_state.ekran == "menu":
    st.title("🌍 Tarihin İzleri: Canlı 1v1 Düello")
    st.write("Arkadaşınla aynı anda yarış! Soru başına **20 saniye** sınır vardır ve geri dönüş yoktur.")
    
    st.session_state.kullanici_adi = st.text_input("Takma Adınız (Username):", st.session_state.kullanici_adi).strip()
    
    col_kur, col_katil = st.columns(2)
    
    with col_kur:
        st.write("### 🏠 Yeni Düello Odası Kur")
        zorluk_secimi = st.selectbox("Zorluk Seviyesi:", ["Karışık", "Kolay", "Orta", "Zor"], key="duel_zorluk")
        if st.button("🚀 Oda Oluştur", use_container_width=True):
            if not st.session_state.kullanici_adi:
                st.error("Lütfen önce bir takma ad girin!")
            else:
                # Rastgele 4 haneli oda kodu üret
                kod = str(random.randint(1000, 9999))
                
                # Zorluğa göre 10 soru seç ve dict formatına çevir
                filtrelenmis = orijinal_df if zorluk_secimi == "Karışık" else orijinal_df[orijinal_df['zorluk'] == zorluk_secimi]
                sorular_dict = filtrelenmis.sample(n=min(10, len(filtrelenmis))).to_dict(orient="records")
                
                rooms = load_rooms()
                rooms[kod] = {
                    "status": "waiting",
                    "zorluk": zorluk_secimi,
                    "sorular": sorted(sorular_dict, key=lambda x: random.random()), # Karıştırılmış sorular
                    "current_question": 0,
                    "q_start_time": 0,
                    "p1_name": st.session_state.kullanici_adi,
                    "p2_name": "",
                    "p1_status": "waiting", # 'waiting', 'submitted'
                    "p2_status": "waiting",
                    "p1_answer": "",
                    "p2_answer": "",
                    "p1_score": 0,
                    "p2_score": 0
                }
                save_rooms(rooms)
                
                st.session_state.oda_kodu = kod
                st.session_state.rol = "p1"
                st.session_state.ekran = "bekleme"
                st.rerun()

    with col_katil:
        st.write("### 🔑 Davet Koduyla Katıl")
        girilen_kod = st.text_input("4 Haneli Oda Kodu:", "").strip()
        if st.button("🤝 Odaya Giriş Yap", use_container_width=True):
            rooms = load_rooms()
            if not st.session_state.kullanici_adi:
                st.error("Lütfen önce bir takma ad girin!")
            elif girilen_kod not in rooms:
                st.error("Oda bulunamadı! Kodu kontrol edin.")
            elif rooms[girilen_kod]["p2_name"] != "":
                st.error("Bu oda zaten dolu!")
            else:
                rooms[girilen_kod]["p2_name"] = st.session_state.kullanici_adi
                rooms[girilen_kod]["status"] = "playing"
                rooms[girilen_kod]["q_start_time"] = time.time() # Oyunu ve ilk sayacı başlat
                save_rooms(rooms)
                
                st.session_state.oda_kodu = girilen_kod
                st.session_state.rol = "p2"
                st.session_state.ekran = "oyun"
                st.rerun()

# ==========================================
# EKRAN 2: LOBİ / BEKLEME EKRANI (Sadece Kurucu Görür)
# ==========================================
elif st.session_state.ekran == "bekleme":
    # Arka planda saniyede bir odayı kontrol et
    st_autorefresh(interval=1000, key="lobby_refresh")
    
    st.title("⏳ Rakip Bekleniyor...")
    st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>ODA KODU: {st.session_state.oda_kodu}</h1>", unsafe_allow_html=True)
    st.write("Bu kodu arkadaşına gönder. O giriş yaptığı an düello otomatik olarak başlayacaktır!")
    
    rooms = load_rooms()
    room = rooms.get(st.session_state.oda_kodu)
    
    if room and room["status"] == "playing":
        st.success("Rakip bağlandı! Başlatılıyor...")
        st.session_state.ekran = "oyun"
        st.rerun()

# ==========================================
# EKRAN 3: CANLI DÜELLO OYUN ALANI
# ==========================================
elif st.session_state.ekran == "oyun":
    # Arka planda saniyede bir verileri senkronize et
    st_autorefresh(interval=1000, key="game_refresh")
    
    rooms = load_rooms()
    room = rooms.get(st.session_state.oda_kodu)
    
    if not room:
        st.error("Oda bağlantısı koptu.")
        st.stop()
        
    rol = st.session_state.rol
    rakip_rol = "p2" if rol == "p1" else "p1"
    
    q_idx = room["current_question"]
    sorular = room["sorular"]
    
    # --- OYUNUN OTOMATİK BİTİŞ KONTROLÜ ---
    if room["status"] == "finished" or q_idx >= len(sorular):
        st.session_state.ekran = "sonuc"
        st.rerun()
        
    mevcut_kisi = sorular[q_idx]
    
    # --- GERÇEK ZAMANLI SAYAÇ HESABI (20 Saniye) ---
    gecen_sure = time.time() - room["q_start_time"]
    kalan_sure = int(max(0, 20 - gecen_sure))
    
    # SÜRE BİTTİĞİNDE VEYA İKİ KİŞİ DE CEVAPLAYIP BEKLEDİĞİNDE DİĞER SORUYA GEÇİŞ
    both_submitted = (room["p1_status"] == "submitted" and room["p2_status"] == "submitted")
    
    if kalan_sure <= 0 or both_submitted:
        # Sadece bir oyuncunun tarayıcısı tetikleyip sunucu dosyasını bir kez günceller
        if q_idx < len(sorular) - 1:
            room["current_question"] += 1
            room["q_start_time"] = time.time()
            room["p1_status"] = "waiting"
            room["p2_status"] = "waiting"
            room["p1_answer"] = ""
            room["p2_answer"] = ""
            save_rooms(rooms)
            st.rerun()
        else:
            room["status"] = "finished"
            save_rooms(rooms)
            st.rerun()

    # Üst Bilgi Çubuğu
    st.title("⚔️ Canlı Düello")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Siz ({room[rol+'_name']})", f"{room[rol+'_score']} Puan")
    c2.markdown(f"<h3 style='text-align:center; color:red;'>⏱️ {kalan_sure} sn</h3>", unsafe_allow_html=True)
    c3.metric(f"Rakip ({room[rakip_rol+'_name']})", f"{room[rakip_rol+'_score']} Puan")
    
    st.write(f"**Soru {q_idx + 1} / {len(sorular)}**")

    # --- HARİTA ÇİZİMİ (ESRI UYDU HARİTASI) ---
    dogum_enlem = mevcut_kisi['dogum_enlem']
    dogum_boylam = mevcut_kisi['dogum_boylam']
    olum_enlem = mevcut_kisi['olum_enlem']
    olum_boylam = mevcut_kisi['olum_boylam']
    merkez_enlem = (dogum_enlem + olum_enlem) / 2
    merkez_boylam = (dogum_boylam + olum_boylam) / 2

    if abs(dogum_enlem - olum_enlem) < 0.1 and abs(dogum_boylam - olum_boylam) < 0.1:
        olum_enlem -= 0.6
        olum_boylam += 0.6

    m = folium.Map(location=[merkez_enlem, merkez_boylam], zoom_start=4, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri")
    c_style = "font-family: Arial; font-weight: bold; font-size: 14px; padding: 4px 8px; border-radius: 6px; box-shadow: 2px 2px 5px rgba(0,0,0,0.5); white-space: nowrap;"
    folium.Marker([dogum_enlem, dogum_boylam], icon=folium.DivIcon(html=f"""<div style="display: flex; align-items: center; transform: translate(-50%, -100%);"><span style='font-size: 20px; margin-right: 4px;'>👶</span><span style="{c_style} color: #2ecc71; background-color: rgba(0,0,0,0.75);">{mevcut_kisi['dogum_yil']}</span></div>""")).add_to(m)
    folium.Marker([olum_enlem, olum_boylam], icon=folium.DivIcon(html=f"""<div style="display: flex; align-items: center; transform: translate(-50%, -100%);"><span style='font-size: 20px; margin-right: 4px;'>⚰️</span><span style="{c_style} color: #e74c3c; background-color: rgba(0,0,0,0.75);">{mevcut_kisi['olum_yil']}</span></div>""")).add_to(m)

    st_folium(m, height=330, use_container_width=True)

    # --- ANLIK CEVAP KONTROLÜ VE EKRAN KİLİTLEME MANTIĞI ---
    kendi_durumu = room[rol + "_status"]
    
    if kendi_durumu == "waiting":
        tahmin = st.text_input("Bu tarihi kişilik kimdir?", key=f"tahmin_duel_{q_idx}")
        if st.button("✔️ Cevapla", use_container_width=True):
            def tr_lower(text):
                return str(text).replace('I', 'ı').replace('İ', 'i').strip().lower()
                
            tahmin_clean = tr_lower(tahmin)
            isim_clean = tr_lower(mevcut_kisi['isim'])
            tahmin_kelimeleri = tahmin_clean.split()
            isim_kelimeleri = isim_clean.split()
            
            tam_benzerlik = difflib.SequenceMatcher(None, tahmin_clean, isim_clean).ratio()
            alt_kume_dogru_mu = len(tahmin_kelimeleri) > 0 and all(
                any(difflib.SequenceMatcher(None, t_k, i_k).ratio() >= 0.75 for i_k in isim_kelimeleri) 
                for t_k in tahmin_kelimeleri
            )
            
            # Doğruysa o oyuncunun skorunu 1 artır
            if tam_benzerlik >= 0.80 or alt_kume_dogru_mu:
                room[rol + "_score"] += 1
                room[rol + "_answer"] = "correct"
            else:
                room[rol + "_answer"] = "wrong"
                
            room[rol + "_status"] = "submitted"
            save_rooms(rooms)
            st.rerun()
    else:
        # Oyuncu cevap verdi, süre bitene kadar sonuç ekranında kilitli bekliyor
        kendi_cevabi = room[rol + "_answer"]
        if kendi_cevabi == "correct":
            st.success(f"🎉 Doğru Bildin! Cevap: **{mevcut_kisi['isim']}**")
        else:
            st.error(f"❌ Yanlış Bildin! Doğru Cevap: **{mevcut_kisi['isim']}**")
            
        if room[rakip_rol + "_status"] == "waiting":
            st.info("⏳ Rakibinin cevap vermesi veya sürenin dolması bekleniyor...")
        else:
            st.warning("🔄 İki oyuncu da yanıtladı! Yeni soruya geçiliyor...")

# ==========================================
# EKRAN 4: DÜELLO SKOR TABLOSU VE KAZANAN
# ==========================================
elif st.session_state.ekran == "sonuc":
    st.balloons()
    st.title("🏆 Canlı Düello Bitti!")
    
    rooms = load_rooms()
    room = rooms.get(st.session_state.oda_kodu)
    
    if room:
        p1_n, p1_s = room["p1_name"], room["p1_score"]
        p2_n, p2_s = room["p2_name"], room["p2_score"]
        
        st.markdown(f"<h2 style='text-align: center; color: #4CAF50;'>{p1_n}: {p1_s} Puan | {p2_n}: {p2_s} Puan</h2>", unsafe_allow_html=True)
        
        if p1_s > p2_s:
            st.success(f"👑 KAZANAN: **{p1_n}**! Tebrikler!")
        elif p2_s > p1_s:
            st.success(f"👑 KAZANAN: **{p2_n}**! Tebrikler!")
        else:
            st.info("🤝 BERABERE! Gerçek bir yenişememe hikayesi.")
            
    if st.button("🔄 Ana Menüye Dön", use_container_width=True):
        st.session_state.ekran = "menu"
        st.rerun()
