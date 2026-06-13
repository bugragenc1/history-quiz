import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os

# Sayfa ayarları (Mobil uyumluluk için geniş ekran)
st.set_page_config(page_title="Tarihin İzleri Quiz", layout="centered")

@st.cache_data
def load_data():
    # Buraya kendi dosya adını yaz (Örn: 'veri-v2.csv')
    csv_yolu = 'veri-v2.csv' 
    
    if not os.path.exists(csv_yolu):
        st.error(f"🚨 '{csv_yolu}' dosyası bulunamadı! Lütfen kodla aynı dizinde olduğundan emin olun.")
        return pd.DataFrame()
    try:
        # Pandas ile CSV'yi oku
        df = pd.read_csv(csv_yolu)
        
        # NaN (boş) koordinatları olan sorunlu satırları temizle
        df = df.dropna(subset=['dogum_enlem', 'dogum_boylam', 'olum_enlem', 'olum_boylam'])
        
        # Her oyunda soruların sıralamasını rastgele karıştır
        df = df.sample(frac=1).reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"🚨 Veri okunurken hata: {e}")
        return pd.DataFrame()

df = load_data()

# Veri gelmediyse oyunu durdur
if df.empty:
    st.stop()

# --- OYUN DURUM KONTROLLERİ ---
# Streamlit her rerun olduğunda bu değerleri korumak için session_state kullanılır
if 'soru_index' not in st.session_state:
    st.session_state.soru_index = 0
if 'skor' not in st.session_state:
    st.session_state.skor = 0
if 'cevaplandi' not in st.session_state:
    st.session_state.cevaplandi = False
if 'sonuc_mesaji' not in st.session_state:
    st.session_state.sonuc_mesaji = ""
if 'durum_renk' not in st.session_state:
    st.session_state.durum_renk = ""

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
# Eğer doğum ve ölüm yerleri birebir aynıysa, yılların üst üste binmemesi için 
# ölüm ikonunu görsel olarak hafifçe kaydırıyoruz.
if abs(dogum_enlem - olum_enlem) < 0.1 and abs(dogum_boylam - olum_boylam) < 0.1:
    olum_enlem -= 0.6
    olum_boylam += 0.6

# === HARİTA KATMANI SEÇİMİ (SEÇENEK 1: ESRI SATELLITE) ===
m = folium.Map(
    location=[merkez_enlem, merkez_boylam], 
    zoom_start=4, 
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri World Imagery"
)

# --- MODERN VE OKUNABİLİR METİN TASARIMI (CSS) ---
# Uydu haritası üzerinde okunabilirlik için arka planı dolu etiketler kullanıyoruz.
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
    background-color: rgba(0, 0, 0, 0.75); /* Siyah arka plan */
"""

death_style = f"""
    {common_style}
    color: #e74c3c; /* Kırmızı */
    background-color: rgba(0, 0, 0, 0.75); /* Siyah arka plan */
"""

# Doğum Yeri İşaretçisi (Modern Etiket)
folium.Marker(
    [dogum_enlem, dogum_boylam],
    icon=folium.DivIcon(html=f"""
        <div style="display: flex; align-items: center; transform: translate(-50%, -100%);">
            <span style='font-size: 20px; margin-right: 4px;'>👶</span>
            <span style="{birth_style}">{mevcut_kisi['dogum_yil']}</span>
        </div>
    """)
).add_to(m)

# Ölüm Yeri İşaretçisi (Modern Etiket)
folium.Marker(
    [olum_enlem, olum_boylam],
    icon=folium.DivIcon(html=f"""
        <div style="display: flex; align-items: center; transform: translate(-50%, -100%);">
            <span style='font-size: 20px; margin-right: 4px;'>⚰️</span>
            <span style="{death_style}">{mevcut_kisi['olum_yil']}</span>
        </div>
    """)
).add_to(m)

# Haritayı ekrana bas (use_container_width mobil için kritik)
st_folium(m, height=450, use_container_width=True)

# --- CEVAPLAMA EKRANI MANTIĞI ---
if not st.session_state.cevaplandi:
    # Henüz cevap verilmediyse input ve buton göster
    tahmin = st.text_input("Bu tarihi kişilik kimdir?", key=f"tahmin_input_{st.session_state.soru_index}")
    
    if st.button("Cevapla"):
        # Türkçe karakterleri doğru şekilde küçük harfe çevirme
        def tr_lower(text):
            return str(text).replace('I', 'ı').replace('İ', 'i').strip().lower()
            
        tahmin_clean = tr_lower(tahmin)
        isim_clean = tr_lower(mevcut_kisi['isim'])
        
        # Kelimeleri parçalara ayırıp küme (set) oluşturuyoruz
        tahmin_kelimeleri = set(tahmin_clean.split())
        isim_kelimeleri = set(isim_clean.split())
        
        # DOĞRULAMA MANTIĞI:
        # 1. Birebir tam yazdıysa
        # 2. VEYA yazdığı tüm kelimeler asıl ismin kelimeleri içinde eksiksiz geçiyorsa
        if (tahmin_clean == isim_clean) or (tahmin_kelimeleri.issubset(isim_kelimeleri) and len(tahmin_kelimeleri) > 0):
            st.session_state.durum_renk = "success"
            st.session_state.sonuc_mesaji = f"Tebrikler! Doğru cevap: {mevcut_kisi['isim']}"
            st.session_state.skor += 1
        else:
            st.session_state.durum_renk = "error"
            st.session_state.sonuc_mesaji = f"Yanlış! Doğru cevap: {mevcut_kisi['isim']} olacaktı."
        
        # Ekranın güncellenmesi ve mesajın kalıcı olması için state'i değiştir
        st.session_state.cevaplandi = True
        st.rerun()

else:
    # Cevap verildiyse inputu gizle, sadece sonucu ve "Sonraki Soru" butonunu göster
    if st.session_state.durum_renk == "success":
        st.success(st.session_state.sonuc_mesaji)
    else:
        st.error(st.session_state.sonuc_mesaji)
        
    if st.session_state.soru_index < len(df) - 1:
        if st.button("Sonraki Soru ➡️"):
            # State'leri bir sonraki soru için temizle
            st.session_state.soru_index += 1
            st.session_state.cevaplandi = False 
            st.rerun()
    else:
        st.info(f"Oyun Bitti! Harika iş çıkardın. Toplam Skorun: {st.session_state.skor}")
        if st.button("Yeniden Başlat 🔄"):
            # Her şeyi sıfırla ve soruları yeniden karıştırmak için cache'i temizle
            st.cache_data.clear()
            st.session_state.soru_index = 0
            st.session_state.skor = 0
            st.session_state.cevaplandi = False
            st.rerun()