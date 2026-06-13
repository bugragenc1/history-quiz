import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os

# Sayfa ayarları (Mobil uyumluluk için geniş ekran)
st.set_page_config(page_title="Tarihin İzleri Quiz", layout="centered")

# 1. VERİYİ SADECE OKU VE TEMİZLE (Önbelleğe al, herkes için bir kere çalışır)
@st.cache_data
def load_data():
    csv_yolu = 'veri-v2.csv' 
    
    if not os.path.exists(csv_yolu):
        st.error(f"🚨 '{csv_yolu}' dosyası bulunamadı! Lütfen kodla aynı dizinde olduğundan emin olun.")
        return pd.DataFrame()
    try:
        df = pd.read_csv(csv_yolu)
        df = df.dropna(subset=['dogum_enlem', 'dogum_boylam', 'olum_enlem', 'olum_boylam'])
        # DİKKAT: Burada karıştırma (sample) yapmıyoruz. Sadece veriyi okuyoruz.
        return df
    except Exception as e:
        st.error(f"🚨 Veri okunurken hata: {e}")
        return pd.DataFrame()

orijinal_df = load_data()

if orijinal_df.empty:
    st.stop()

# 2. HER KULLANICI İÇİN ÖZEL KARIŞTIRMA VE HAFIZA YÖNETİMİ
# Eğer o anki kullanıcının hafızasında oyun verisi yoksa, orijinal listeyi karıştırıp ona özel kaydet
if 'oyun_verisi' not in st.session_state:
    st.session_state.oyun_verisi = orijinal_df.sample(frac=1).reset_index(drop=True)
    st.session_state.soru_index = 0
    st.session_state.skor = 0
    st.session_state.cevaplandi = False
    st.session_state.sonuc_mesaji = ""
    st.session_state.durum_renk = ""

# Oyun boyunca kullanıcının kendine özel karıştırılmış destesini kullan
df = st.session_state.oyun_verisi

# Mevcut sorudaki kişiyi çek
mevcut_kisi = df.iloc[st.session_state.soru_index]

st.title("🌍 Tarihin İzleri: Kim Bu?")
st.write(f"**Skor:** {st.session_state.skor} / {len(df)}")
st.write("Haritadaki doğum ve ölüm konumlarına (ve yıllarına) bakarak bu tarihi kişiliğin kim olduğunu tahmin et!")

# Koordinatları değişkenlere alalım
dogum_enlem = mevcut_kisi['dogum_enlem']
dogum_boylam = mevcut_kisi['dogum_boylam']
olum_enlem = mevcut_kisi['olum_enlem']
olum_boylam = mevcut_kisi['olum_boylam']

# Harita merkezi için ortalama hesaplama
merkez_enlem = (dogum_enlem + olum_enlem) / 2
merkez_boylam = (dogum_boylam + olum_boylam) / 2

# --- ÇAKIŞMA KONTROLÜ ---
if abs(dogum_enlem - olum_enlem) < 0.1 and abs(dogum_boylam - olum_boylam) < 0.1:
    olum_enlem -= 0.6
    olum_boylam += 0.6

m = folium.Map(
    location=[merkez_enlem, merkez_boylam], 
    zoom_start=4, 
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri World Imagery"
)

common_style = """
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-weight: bold;
    font-size: 14px;
    padding: 4px 8px;
    border-radius: 6px;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.5);
    white-space: nowrap;
"""

birth_style = f"""
    {common_style}
    color: #2ecc71; /* Yeşil */
    background-color: rgba(0, 0, 0, 0.75);
"""

death_style = f"""
    {common_style}
    color: #e74c3c; /* Kırmızı */
    background-color: rgba(0, 0, 0, 0.75);
"""

folium.Marker(
    [dogum_enlem, dogum_boylam],
    icon=folium.DivIcon(html=f"""
        <div style="display: flex; align-items: center; transform: translate(-50%, -100%);">
            <span style='font-size: 20px; margin-right: 4px;'>👶</span>
            <span style="{birth_style}">{mevcut_kisi['dogum_yil']}</span>
        </div>
    """)
).add_to(m)

folium.Marker(
    [olum_enlem, olum_boylam],
    icon=folium.DivIcon(html=f"""
        <div style="display: flex; align-items: center; transform: translate(-50%, -100%);">
            <span style='font-size: 20px; margin-right: 4px;'>⚰️</span>
            <span style="{death_style}">{mevcut_kisi['olum_yil']}</span>
        </div>
    """)
).add_to(m)

st_folium(m, height=450, use_container_width=True)

# --- CEVAPLAMA EKRANI MANTIĞI ---
if not st.session_state.cevaplandi:
    tahmin = st.text_input("Bu tarihi kişilik kimdir?", key=f"tahmin_input_{st.session_state.soru_index}")
    
    if st.button("Cevapla"):
        def tr_lower(text):
            return str(text).replace('I', 'ı').replace('İ', 'i').strip().lower()
            
        tahmin_clean = tr_lower(tahmin)
        isim_clean = tr_lower(mevcut_kisi['isim'])
        
        tahmin_kelimeleri = set(tahmin_clean.split())
        isim_kelimeleri = set(isim_clean.split())
        
        if (tahmin_clean == isim_clean) or (tahmin_kelimeleri.issubset(isim_kelimeleri) and len(tahmin_kelimeleri) > 0):
            st.session_state.durum_renk = "success"
            st.session_state.sonuc_mesaji = f"Tebrikler! Doğru cevap: {mevcut_kisi['isim']}"
            st.session_state.skor += 1
        else:
            st.session_state.durum_renk = "error"
            st.session_state.sonuc_mesaji = f"Yanlış! Doğru cevap: {mevcut_kisi['isim']} olacaktı."
        
        st.session_state.cevaplandi = True
        st.rerun()

else:
    if st.session_state.durum_renk == "success":
        st.success(st.session_state.sonuc_mesaji)
    else:
        st.error(st.session_state.sonuc_mesaji)
        
    if st.session_state.soru_index < len(df) - 1:
        if st.button("Sonraki Soru ➡️"):
            st.session_state.soru_index += 1
            st.session_state.cevaplandi = False 
            st.rerun()
    else:
        st.info(f"Oyun Bitti! Harika iş çıkardın. Toplam Skorun: {st.session_state.skor}")
        if st.button("Yeniden Başlat 🔄"):
            # OYUNCUYA ÖZEL HAFIZAYI TEMİZLE (Böylece kartlar baştan karılır)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
