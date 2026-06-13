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
elif st.session_state.ekran == "oyun":
    soru_sayisi = len(st.session_state.oyun_verisi)
    
    # --- ZAMAN KONTROLÜ (200 Saniye) ---
    gecen_sure = time.time() - st.session_state.baslangic_zamani
    kalan_sure = int(max(0, 200 - gecen_sure))
    
    if kalan_sure <= 0:
        st.warning("⏱️ SÜRE BİTTİ!")
        time.sleep(1)
        st.session_state.ekran = "sonuc"
        st.rerun()

    timer_html = f"""
    <div style="font-family: Arial, sans-serif; font-size: 20px; font-weight: bold; color: #e74c3c; text-align: center; padding: 8px; border: 2px solid #e74c3c; border-radius: 8px; background-color: #fcebeb; margin-bottom: 10px;">
        ⏱️ Kalan: <span id="timer">{kalan_sure}</span> saniye
    </div>
    <script>
        var timeLeft = {kalan_sure};
        var timerEl = document.getElementById('timer');
        var x = setInterval(function() {{
            timeLeft--;
            if (timeLeft <= 0) {{
                clearInterval(x);
                timerEl.parentElement.innerHTML = "⏱️ SÜRE DOLDU!";
            }} else {{
                timerEl.innerHTML = timeLeft;
            }}
        }}, 1000);
    </script>
    """
    components.html(timer_html, height=60)

    # --- SORU NAVİGASYON PANELİ (Mobilde 5-5 İki Satır Mantığı) ---
    st.write("### Soru Paneli")
    
    satir1 = st.columns(5)
    satir2 = st.columns(5)
    
    for i in range(soru_sayisi):
        durum = st.session_state.cevap_durumlari[i]
        
        if durum == "dogru":
            ikon = "🟢"
        elif durum == "yanlis":
            ikon = "🔴"
        else:
            ikon = "⚪"
            
        buton_metni = f"📍 {i+1}" if i == st.session_state.aktif_soru_index else f"{ikon} {i+1}"
        
        # İlk 5 soruyu birinci satıra, geri kalanları ikinci satıra yerleştiriyoruz
        aktif_kolon = satir1[i] if i < 5 else satir2[i - 5]
        
        with aktif_kolon:
            if st.button(buton_metni, key=f"nav_btn_{i}", use_container_width=True):
                st.session_state.aktif_soru_index = i
                st.rerun()
                
    st.divider()

    # --- O ANKİ SORUYU GETİR ---
    aktif_index = st.session_state.aktif_soru_index
    df = st.session_state.oyun_verisi
    mevcut_kisi = df.iloc[aktif_index]
    
    anlik_skor = st.session_state.cevap_durumlari.count("dogru")
    st.write(f"**Soru {aktif_index + 1} / {soru_sayisi}** | ⭐ Anlık Skor: {anlik_skor}")

    # --- HARİTA ÇİZİMİ ---
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

    # Harita yüksekliği mobilde sığması için 330 yapıldı
    st_folium(m, height=330, use_container_width=True)

    # --- CEVAPLAMA MANTIĞI ---
    durum = st.session_state.cevap_durumlari[aktif_index]
    
    if durum == "bos":
        tahmin = st.text_input("Bu tarihi kişilik kimdir?", key=f"tahmin_input_{aktif_index}")
        
        col_cevap, col_gec = st.columns(2)
        with col_cevap:
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
                
                if tam_benzerlik >= 0.80 or alt_kume_dogru_mu:
                    st.session_state.cevap_durumlari[aktif_index] = "dogru"
                else:
                    st.session_state.cevap_durumlari[aktif_index] = "yanlis"
                    
                st.session_state.kullanici_cevaplari[aktif_index] = tahmin
                st.rerun()
                
        with col_gec:
            if st.button("Pas Geç ➡️", use_container_width=True):
                st.session_state.aktif_soru_index = (aktif_index + 1) % soru_sayisi
                st.rerun()
            
    else:
        kullanici_cevabi = st.session_state.kullanici_cevaplari[aktif_index]
        
        if durum == "dogru":
            st.success(f"🎉 Doğru Bildiniz! Cevap: **{mevcut_kisi['isim']}**")
        else:
            st.error(f"❌ Yanlış! Senin Yanıtın: '{kullanici_cevabi}' | Doğru Cevap: **{mevcut_kisi['isim']}**")
            
        if st.button("Sonraki Soruya Geç ➡️", use_container_width=True):
            st.session_state.aktif_soru_index = (aktif_index + 1) % soru_sayisi
            st.rerun()
            
        bos_kalanlar = [idx for idx, d in enumerate(st.session_state.cevap_durumlari) if d == "bos"]
        if not bos_kalanlar:
            if st.button("Tüm Sorular Tamamlandı! Sonuçları Gör 🏆", use_container_width=True):
                save_highscore(st.session_state.secilen_zorluk, st.session_state.cevap_durumlari.count("dogru"))
                st.session_state.ekran = "sonuc"
                st.rerun()
            
    st.divider()
    if st.button("Oyunu Erken Bitir ve Sonuçları Gör 🛑", type="secondary"):
        save_highscore(st.session_state.secilen_zorluk, st.session_state.cevap_durumlari.count("dogru"))
        st.session_state.ekran = "sonuc"
        st.rerun()


# ==========================================
# EKRAN 3: BİTİŞ VE SONUÇLAR
# ==========================================
elif st.session_state.ekran == "sonuc":
    st.balloons()
    st.title("🏆 Oyun Bitti!")
    
    soru_sayisi = len(st.session_state.oyun_verisi)
    skor = st.session_state.cevap_durumlari.count("dogru")
    bos_sayisi = st.session_state.cevap_durumlari.count("bos")
    zorluk = st.session_state.secilen_zorluk
    
    st.markdown(f"<h2 style='text-align: center; color: #4CAF50;'>{zorluk} Seviye Skoru: {skor} / {soru_sayisi}</h2>", unsafe_allow_html=True)
    
    if bos_sayisi > 0:
        st.warning(f"Zaman yetmediği veya erken bitirdiğin için {bos_sayisi} soruyu boş bıraktın.")
    
    scores = load_highscores()
    if skor >= scores.get(zorluk, 0) and skor > 0:
        st.success("👑 YENİ REKOR KIRDIN!")
        
    st.divider()
    
    st.write("### 📝 Soru Özeti")
    for i in range(soru_sayisi):
        durum = st.session_state.cevap_durumlari[i]
        kisi_ismi = st.session_state.oyun_verisi.iloc[i]['isim']
        kullanici_cevabi = st.session_state.kullanici_cevaplari[i]
        
        if durum == "dogru":
            st.markdown(f"**Soru {i+1}:** 🟢 Doğru (**{kisi_ismi}**)")
        elif durum == "yanlis":
            st.markdown(f"**Soru {i+1}:** 🔴 Yanlış (Senin Yanıtın: *'{kullanici_cevabi}'* | Doğru Cevap: **{kisi_ismi}**)")
        else:
            st.markdown(f"**Soru {i+1}:** ⚪ Boş (Doğru Cevap: **{kisi_ismi}**)")
            
    st.divider()

    if st.button("🔄 Ana Menüye Dön", use_container_width=True):
        st.session_state.ekran = "menu"
        st.rerun()
