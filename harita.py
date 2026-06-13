import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import difflib
import json
import time

st.set_page_config(page_title="Tarihin İzleri Quiz", layout="centered", page_icon="🌍")

# --- MOBİL UYUMLULUK İÇİN CSS DOKUNUŞLARI ---
st.markdown("""
    <style>
        /* Buton metinlerinin mobilde taşmasını engellemek için küçük bir ayar */
        @media (max-width: 768px) {
            .stButton > button {
                padding: 4px 8px !important;
                font-size: 14px !important;
            }
        }
    </style>
""", unsafe_allow_html=True)

# --- HIGHSCORE YÖNETİMİ ---
SCORE_FILE = "highscores.json"

def load_highscores():
    if os.path.exists(SCORE_FILE):
        with open(SCORE_FILE, "r") as f:
            return json.load(f)
    return {"Karışık": 0, "Kolay": 0, "Orta": 0, "Zor": 0}

def save_highscore(zorluk, skor):
    scores = load_highscores()
    if skor > scores.get(zorluk, 0):
        scores[zorluk] = skor
        with open(SCORE_FILE, "w") as f:
            json.dump(scores, f)

# --- VERİYİ ÇEK VE HAZIRLA ---
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

# --- HAFIZA (STATE) YÖNETİMİ ---
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


# ==========================================
# EKRAN 1: ANA MENÜ 
# ==========================================
if st.session_state.ekran == "menu":
    st.title("🌍 Tarihin İzleri: Kim Bu?")
    st.write("Zorluk seviyesi seçin. Unutmayın, **sadece 200 saniyeniz** var!")
    
    scores = load_highscores()
    
    # Mobilde daha düzgün durması için 4'lü yerine 2x2 matris kullanıyoruz
    col_k, col_o = st.columns(2)
    col_k.metric("Rekor (Kolay)", f"{scores['Kolay']} / 10")
    col_o.metric("Rekor (Orta)", f"{scores['Orta']} / 10")
    
    col_z, col_m = st.columns(2)
    col_z.metric("Rekor (Zor)", f"{scores['Zor']} / 10")
    col_m.metric("Rekor (Karışık)", f"{scores['Karışık']} / 10")
    
    st.divider()
    
    zorluk_secimi = st.selectbox("Zorluk Seviyesini Seçin:", ["Karışık", "Kolay", "Orta", "Zor"])
    
    if st.button("🚀 Zamana Karşı Oyunu Başlat!", use_container_width=True):
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
        
        st.session_state.ekran = "oyun"
        st.rerun()


# ==========================================
# EKRAN 2: OYUN EKRANI
# ==========================================
elif
