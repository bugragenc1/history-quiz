import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import difflib
import json

st.set_page_config(page_title="Tarihin İzleri Quiz", layout="centered")

# --- HIGHSCORE (EN YÜKSEK SKOR) YÖNETİMİ ---
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
if 'kalan_sorular' not in st.session_state: # Pas geçme kuyruğu
    st.session_state.kalan_sorular = []
if 'cozulen_soru_sayisi' not in st.session_state:
    st.session_state.cozulen_soru_sayisi = 0
if 'hedef_soru_sayisi' not in st.session_state:
    st.session_state.hedef_soru_sayisi = 0
if 'secilen_zorluk' not in st.session_state:
    st.session_state.secilen_zorluk = "Karışık"
if 'skor' not in st.session_state:
    st.session_state.skor = 0
if 'cevaplandi' not in st.session_state:
    st.session_state.cevaplandi = False


# ==========================================
# EKRAN 1: ANA MENÜ 
# ==========================================
if st.session_state.ekran == "menu":
    st.title("🌍 Tarihin İzleri: Kim Bu?")
    st.write("Zorluk seviyesi seçin ve oyuna başlayın. Zorlandığınız soruları sona atabilirsiniz!")
    
    # Mevcut rekorları göster
    scores = load_highscores()
    col_k, col_o, col_z, col_m = st.columns(4)
    col_k.metric("Rekor (Kolay)", f"{scores['Kolay']} / 10")
    col_o.metric("Rekor (Orta)", f"{scores['Orta']} / 10")
    col_z.metric("Rekor (Zor)", f"{scores['Zor']} / 10")
    col_m.metric("Rekor (Karışık)", f"{scores['Karışık']} / 10")
    
    st.divider()
    
    # Zorluk Seçimi
    zorluk_secimi = st.selectbox("Zorluk Seviyesini Seçin:", ["Karışık", "Kolay", "Orta", "Zor"])
    
    if st.button("🚀 Yeni Oyun Başlat", use_container_width=True):
        if zorluk_secimi != "Karışık":
            filtrelenmis_df = orijinal_df[orijinal_df['zorluk'] == zorluk_secimi]
        else:
            filtrelenmis_df = orijinal_df
            
        # Rastgele 10 kişi seç
        soru_sayisi = min(10, len(filtrelenmis_df))
        st.session_state.oyun_verisi = filtrelenmis_df.sample(n=soru_sayisi).reset_index(drop=True)
        
        # Soru kuyruğunu (indexleri) oluştur
        st.session_state.kalan_sorular = list(range(soru_sayisi))
        st.session_state.hedef_soru_sayisi = soru_sayisi
        st.session_state.cozulen_soru_sayisi = 0
        st.session_state.secilen_zorluk = zorluk_secimi
        
        st.session_state.skor = 0
        st.session_state.cevaplandi = False
        st.session_state.ekran = "oyun"
        st.rerun()


# ==========================================
# EKRAN 2: OYUN EKRANI
# ==========================================
elif st.session_state.ekran == "oyun":
    df = st.session_state.oyun_verisi
    # Kuyruğun en başındaki soruyu getir
    aktif_index = st.session_state.kalan_sorular[0]
    mevcut_kisi = df.iloc[aktif_index]

    st.title("🌍 Tarihin İzleri")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📍 **İlerleme:** {st.session_state.cozulen_soru_sayisi + 1} / {st.session_state.hedef_soru_sayisi} (Kalan: {len(st.session_state.kalan_sorular)})")
    with col2:
        st.success(f"⭐ **Skor:** {st.session_state.skor}")

    # --- Harita Çizimi ---
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

    st_folium(m, height=450, use_container_width=True)

    # --- Cevaplama ve Pas Geçme Mantığı ---
    if not st.session_state.cevaplandi:
        tahmin = st.text_input("Bu tarihi kişilik kimdir?", key=f"tahmin_input_{aktif_index}")
        
        c1, c2 = st.columns([2, 1])
        with c1:
            if st.button("✔️ Cevapla", use_container_width=True):
                def tr_lower(text):
                    return str(text).replace('I', 'ı').replace('İ', 'i').strip().lower()
                    
                tahmin_clean = tr_lower(tahmin)
                isim_clean = tr_lower(mevcut_kisi['isim'])
                tahmin_kelimeleri = tahmin_clean.split()
                isim_kelimeleri = isim_clean.split()
                
                # Typo (Yazım Hatası) ve Parça Kontrolü
                tam_benzerlik = difflib.SequenceMatcher(None, tahmin_clean, isim_clean).ratio()
                alt_kume_dogru_mu = len(tahmin_kelimeleri) > 0 and all(
                    any(difflib.SequenceMatcher(None, t_k, i_k).ratio() >= 0.75 for i_k in isim_kelimeleri) 
                    for t_k in tahmin_kelimeleri
                )
                
                if tam_benzerlik >= 0.80 or alt_kume_dogru_mu:
                    st.session_state.durum_renk = "success"
                    st.session_state.sonuc_mesaji = f"🎉 Tebrikler! Doğru cevap: {mevcut_kisi['isim']}"
                    st.session_state.skor += 1
                else:
                    st.session_state.durum_renk = "error"
                    st.session_state.sonuc_mesaji = f"❌ Yanlış! Doğru cevap: {mevcut_kisi['isim']} olacaktı."
                
                st.session_state.cevaplandi = True
                st.rerun()
                
        with c2:
            # Sadece kuyrukta 1'den fazla soru kaldıysa pas geçilebilir
            if len(st.session_state.kalan_sorular) > 1:
                if st.button("⏭️ Pas Geç", use_container_width=True):
                    # En baştaki soruyu al, kuyruğun en sonuna ekle
                    gecilen_soru = st.session_state.kalan_sorular.pop(0)
                    st.session_state.kalan_sorular.append(gecilen_soru)
                    st.rerun()

    else:
        # Sonucu göster
        if st.session_state.durum_renk == "success":
            st.success(st.session_state.sonuc_mesaji)
        else:
            st.error(st.session_state.sonuc_mesaji)
            
        # Eğer kuyrukta başka soru varsa "Sonraki Soru", yoksa "Sonuçları Gör"
        if len(st.session_state.kalan_sorular) > 1:
            if st.button("Sonraki Soru ➡️", use_container_width=True):
                st.session_state.kalan_sorular.pop(0) # Çözülen soruyu at
                st.session_state.cozulen_soru_sayisi += 1
                st.session_state.cevaplandi = False 
                st.rerun()
        else:
            if st.button("Sonuçları Gör 🏆", use_container_width=True):
                st.session_state.kalan_sorular.pop(0)
                st.session_state.cozulen_soru_sayisi += 1
                
                # Rekoru kaydet
                save_highscore(st.session_state.secilen_zorluk, st.session_state.skor)
                
                st.session_state.ekran = "sonuc"
                st.rerun()

# ==========================================
# EKRAN 3: BİTİŞ VE SONUÇLAR
# ==========================================
elif st.session_state.ekran == "sonuc":
    st.balloons()
    st.title("🏆 Oyun Bitti!")
    
    toplam = st.session_state.hedef_soru_sayisi
    skor = st.session_state.skor
    zorluk = st.session_state.secilen_zorluk
    
    st.markdown(f"<h2 style='text-align: center; color: #4CAF50;'>{zorluk} Seviye Skoru: {skor} / {toplam}</h2>", unsafe_allow_html=True)
    
    # Rekor kontrolü yapıp kullanıcıyı tebrik et
    scores = load_highscores()
    if skor >= scores.get(zorluk, 0) and skor > 0:
        st.warning("👑 YENİ REKOR KIRDIN!")
        
    if st.button("🔄 Ana Menüye Dön", use_container_width=True):
        st.session_state.ekran = "menu"
        st.rerun()
