import difflib
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os

st.set_page_config(page_title="Tarihin İzleri Quiz", layout="centered")

# --- 1. VERİYİ ÇEK (SADECE BİR KERE ÇALIŞIR) ---
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

# --- 2. HAFIZA (STATE) YÖNETİMİ ---
# Uygulama açılışında oyun hangi ekranda olmalı? (menu, oyun, sonuc)
if 'ekran' not in st.session_state:
    st.session_state.ekran = "menu"
if 'oyun_verisi' not in st.session_state:
    st.session_state.oyun_verisi = None
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


# ==========================================
# EKRAN 1: ANA MENÜ 
# ==========================================
if st.session_state.ekran == "menu":
    st.title("🌍 Tarihin İzleri: Kim Bu?")
    st.write("Hoş geldin! Lütfen bir zorluk seviyesi seç ve yeni oyuna başla. Her turda rastgele 10 soru sorulacaktır.")
    
    # Zorluk Seçimi
    zorluk_secimi = st.selectbox("Zorluk Seviyesini Seçin:", ["Karışık", "Kolay", "Orta", "Zor"])
    
    if st.button("🚀 Yeni Oyun Başlat", use_container_width=True):
        # Seçilen zorluğa göre veriyi filtrele
        if zorluk_secimi != "Karışık":
            filtrelenmis_df = orijinal_df[orijinal_df['zorluk'] == zorluk_secimi]
        else:
            filtrelenmis_df = orijinal_df
            
        # Filtrelenen havuzdan rastgele 10 kişi seç
        soru_sayisi = min(10, len(filtrelenmis_df))
        st.session_state.oyun_verisi = filtrelenmis_df.sample(n=soru_sayisi).reset_index(drop=True)
        
        # Oyun verilerini sıfırla ve oyun ekranına geç
        st.session_state.soru_index = 0
        st.session_state.skor = 0
        st.session_state.cevaplandi = False
        st.session_state.ekran = "oyun"
        st.rerun()


# ==========================================
# EKRAN 2: OYUN EKRANI
# ==========================================
elif st.session_state.ekran == "oyun":
    df = st.session_state.oyun_verisi
    mevcut_kisi = df.iloc[st.session_state.soru_index]
    toplam_soru = len(df)

    st.title("🌍 Tarihin İzleri")
    
    # İlerleme ve Skor Çubuğu (Örn: 5 / 10)
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📍 **Soru:** {st.session_state.soru_index + 1} / {toplam_soru}")
    with col2:
        st.success(f"⭐ **Skor:** {st.session_state.skor} / {toplam_soru}")

    # --- Harita ve Koordinat Ayarları ---
    dogum_enlem = mevcut_kisi['dogum_enlem']
    dogum_boylam = mevcut_kisi['dogum_boylam']
    olum_enlem = mevcut_kisi['olum_enlem']
    olum_boylam = mevcut_kisi['olum_boylam']

    merkez_enlem = (dogum_enlem + olum_enlem) / 2
    merkez_boylam = (dogum_boylam + olum_boylam) / 2

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
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: bold; font-size: 14px;
        padding: 4px 8px; border-radius: 6px; box-shadow: 2px 2px 5px rgba(0,0,0,0.5); white-space: nowrap;
    """
    birth_style = f"{common_style} color: #2ecc71; background-color: rgba(0, 0, 0, 0.75);"
    death_style = f"{common_style} color: #e74c3c; background-color: rgba(0, 0, 0, 0.75);"

    folium.Marker(
        [dogum_enlem, dogum_boylam],
        icon=folium.DivIcon(html=f"""<div style="display: flex; align-items: center; transform: translate(-50%, -100%);">
        <span style='font-size: 20px; margin-right: 4px;'>👶</span><span style="{birth_style}">{mevcut_kisi['dogum_yil']}</span></div>""")
    ).add_to(m)

    folium.Marker(
        [olum_enlem, olum_boylam],
        icon=folium.DivIcon(html=f"""<div style="display: flex; align-items: center; transform: translate(-50%, -100%);">
        <span style='font-size: 20px; margin-right: 4px;'>⚰️</span><span style="{death_style}">{mevcut_kisi['olum_yil']}</span></div>""")
    ).add_to(m)

    st_folium(m, height=450, use_container_width=True)

    # --- Cevaplama Mantığı ---
    if not st.session_state.cevaplandi:
        tahmin = st.text_input("Bu tarihi kişilik kimdir?", key=f"tahmin_input_{st.session_state.soru_index}")
        
        if st.button("Cevapla"):
            def tr_lower(text):
                return str(text).replace('I', 'ı').replace('İ', 'i').strip().lower()
                
            tahmin_clean = tr_lower(tahmin)
            isim_clean = tr_lower(mevcut_kisi['isim'])
            
            tahmin_kelimeleri = tahmin_clean.split()
            isim_kelimeleri = isim_clean.split()
            
            # 1. KONTROL: Tam Metin Benzerliği (Örn: "mahatma gandi" vs "mahatma gandhi")
            # İki metin birbiriyle %80 veya daha fazla eşleşiyorsa kabul et.
            tam_benzerlik = difflib.SequenceMatcher(None, tahmin_clean, isim_clean).ratio()
            
            # 2. KONTROL: Kelime Bazlı Alt Küme Benzerliği (Örn: Sadece "gandi" yazdıysa)
            alt_kume_dogru_mu = True
            if len(tahmin_kelimeleri) == 0:
                alt_kume_dogru_mu = False
            else:
                for t_kelime in tahmin_kelimeleri:
                    # Kullanıcının yazdığı her bir kelime, asıl ismin kelimelerinden herhangi birine %75 benziyor mu?
                    kelime_eslesti = any(difflib.SequenceMatcher(None, t_kelime, i_kelime).ratio() >= 0.75 for i_kelime in isim_kelimeleri)
                    if not kelime_eslesti:
                        alt_kume_dogru_mu = False
                        break
            
            # Eğer tam isim benzerliği %80'den büyükse VEYA girdiği kelimeler ismin parçalarına uyuyorsa:
            if tam_benzerlik >= 0.80 or alt_kume_dogru_mu:
                st.session_state.durum_renk = "success"
                st.session_state.sonuc_mesaji = f"🎉 Tebrikler! Doğru cevap: {mevcut_kisi['isim']}"
                st.session_state.skor += 1
            else:
                st.session_state.durum_renk = "error"
                st.session_state.sonuc_mesaji = f"❌ Yanlış! Doğru cevap: {mevcut_kisi['isim']} olacaktı."
            
            st.session_state.cevaplandi = True
            st.rerun()

    else:
        # Sonucu ekrana bas
        if st.session_state.durum_renk == "success":
            st.success(st.session_state.sonuc_mesaji)
        else:
            st.error(st.session_state.sonuc_mesaji)
            
        # Sonraki Soru veya Bitiş Butonu
        if st.session_state.soru_index < toplam_soru - 1:
            if st.button("Sonraki Soru ➡️", use_container_width=True):
                st.session_state.soru_index += 1
                st.session_state.cevaplandi = False 
                st.rerun()
        else:
            if st.button("Sonuçları Gör 🏆", use_container_width=True):
                # 10 soru bittiğinde bitiş ekranına geç
                st.session_state.ekran = "sonuc"
                st.rerun()


# ==========================================
# EKRAN 3: BİTİŞ VE SONUÇLAR
# ==========================================
elif st.session_state.ekran == "sonuc":
    st.balloons()
    st.title("🏆 Oyun Bitti!")
    
    toplam_soru = len(st.session_state.oyun_verisi)
    skor = st.session_state.skor
    
    # Büyük bir skor yazısı
    st.markdown(f"<h2 style='text-align: center; color: #4CAF50;'>Toplam Skor: {skor} / {toplam_soru}</h2>", unsafe_allow_html=True)
    
    # Skora göre geri bildirim
    if skor == toplam_soru:
        st.success("Kusursuz! Gerçek bir tarih profesörüsün.")
    elif skor >= toplam_soru / 2:
        st.info("Tebrikler, ortalamanın üstündesin!")
    else:
        st.warning("Biraz daha tarih çalışman gerekebilir.")
        
    if st.button("🔄 Ana Menüye Dön ve Yeni Oyun Başlat", use_container_width=True):
        st.session_state.ekran = "menu"
        st.rerun()
