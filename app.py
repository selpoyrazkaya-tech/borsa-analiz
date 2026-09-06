import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go
from google import genai
import time

st.set_page_config(page_title="Yapay Zeka Destekli BIST Analiz", layout="wide")
st.title("📈 Borsa İstanbul - Yapay Zeka Yorumlu Analiz Uygulaması")

# Streamlit Secrets'tan API Key Okuma
try:
    API_KEY = st.secrets["API_KEY"]
except Exception:
    API_KEY = None

# Borsa İstanbul Hisse Listesi
BIST_TUM_HISSELER = sorted([
    "A1CAP.IS", "ACSEL.IS", "ADEL.IS", "ADESE.IS", "AEFES.IS", "AFYON.IS", "AGESA.IS", 
    "AGHOL.IS", "AGROT.IS", "AHGAZ.IS", "AKBNK.IS", "AKCNS.IS", "AKFGY.IS", "AKSA.IS", 
    "AKSEN.IS", "ALARK.IS", "ALBRK.IS", "ALFAS.IS", "ARCLK.IS", "ARDYZ.IS", "ASELS.IS", 
    "ASTOR.IS", "AYDEM.IS", "BIMAS.IS", "BRSAN.IS", "CANTE.IS", "CCOLA.IS", "CWENE.IS", 
    "DOAS.IS", "DOHOL.IS", "ECILC.IS", "EGEEN.IS", "EKGYO.IS", "ENJSA.IS", "ENKAI.IS", 
    "EREGL.IS", "EUPWR.IS", "FROTO.IS", "GARAN.IS", "GESAN.IS", "GUBRF.IS", "HALKB.IS", 
    "HEKTS.IS", "ISCTR.IS", "KCAER.IS", "KCHOL.IS", "KONTR.IS", "KOZAL.IS", "KRDMD.IS", 
    "MIATK.IS", "ODAS.IS", "OTKAR.IS", "OYAKC.IS", "PETKM.IS", "PGSUS.IS", "REEDR.IS", 
    "SAHOL.IS", "SASA.IS", "SISE.IS", "SKBNK.IS", "SMRTG.IS", "SOKM.IS", "TAVHL.IS", 
    "TCELL.IS", "THYAO.IS", "TKFEN.IS", "TOASO.IS", "TSKB.IS", "TTKOM.IS", "TTRAK.IS", 
    "TUPRS.IS", "ULKER.IS", "VAKBN.IS", "VESBE.IS", "VESTL.IS", "YKBNK.IS", "ZOREN.IS"
])

st.sidebar.header("📊 Hisse Seçimi")
selected_ticker = st.sidebar.selectbox("Hisse Seçin:", options=BIST_TUM_HISSELER, index=BIST_TUM_HISSELER.index("BIMAS.IS") if "BIMAS.IS" in BIST_TUM_HISSELER else 0)
period = st.sidebar.selectbox("Zaman Aralığı:", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)

if selected_ticker:
    with st.spinner(f"{selected_ticker} verileri indiriliyor..."):
        data = yf.download(selected_ticker, period=period, interval="1d")
    
    if not data.empty:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        data['SMA_20'] = ta.trend.sma_indicator(close=data['Close'], window=20)
        data['SMA_50'] = ta.trend.sma_indicator(close=data['Close'], window=50)
        data['RSI_14'] = ta.momentum.rsi(close=data['Close'], window=14)

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=data.index, open=data['Open'], high=data['High'],
            low=data['Low'], close=data['Close'], name="Fiyat"
        ))
        fig.add_trace(go.Scatter(x=data.index, y=data['SMA_20'], line=dict(color='orange', width=1.5), name="SMA 20"))
        fig.add_trace(go.Scatter(x=data.index, y=data['SMA_50'], line=dict(color='blue', width=1.5), name="SMA 50"))
        fig.update_layout(title=f"{selected_ticker} Fiyat Grafiği", xaxis_rangeslider_visible=False, height=450)
        st.plotly_chart(fig, width='stretch')

        last_close = round(float(data['Close'].iloc[-1]), 2)
        last_rsi = round(float(data['RSI_14'].iloc[-1]), 2)
        last_sma20 = round(float(data['SMA_20'].iloc[-1]), 2)
        last_sma50 = round(float(data['SMA_50'].iloc[-1]), 2)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Son Kapanış Fiyatı", f"{last_close} TL")
        col2.metric("RSI (14)", last_rsi)
        col3.metric("SMA 20 (Kısa Vadeli)", f"{last_sma20} TL")
        col4.metric("SMA 50 (Orta Vadeli)", f"{last_sma50} TL")

        st.markdown("---")
        st.subheader("🤖 Yapay Zeka Hisse Yorumu ve Beklenti Analizi")

        if not API_KEY:
            st.warning("⚠️ Lütfen Streamlit Cloud 'Secrets' alanına geçerli bir API_KEY ekleyin.")
        else:
            if st.button("🤖 Yapay Zeka Analizini Başlat"):
                with st.spinner("Yapay zeka teknik verileri ve piyasa durumunu analiz ediyor..."):
                    client = genai.Client(api_key=str(API_KEY).strip())

                    prompt = f"""
                    Sen uzman bir Borsa İstanbul (BIST) finansal analistisin.
                    Aşağıda verilen teknik verileri ve şirketin genel sektör konumunu dikkate alarak {selected_ticker} hissesi için detaylı bir değerlendirme yap.

                    **Hisse Verileri:**
                    - Hisse: {selected_ticker}
                    - Son Kapanış Fiyatı: {last_close} TL
                    - RSI (14) Değeri: {last_rsi}
                    - 20 Günlük Hareketli Ortalama (SMA 20): {last_sma20} TL
                    - 50 Günlük Hareketli Ortalama (SMA 50): {last_sma50} TL

                    **İstenen Format:**
                    1. **Gelecek Beklentisi:** Hisse için (Yükseliş / Düşüş / Yatay) yönlü bir beklenti belirt.
                    2. **Somut Gerekçeler:**
                       - Verilen teknik verileri yorumla (RSI aşırı alım/satım bölgesinde mi, SMA 20 ile SMA 50 ilişkisi nasıl?).
                       - Şirketin faaliyet gösterdiği sektörün genel ekonomik durumdan nasıl etkilendiğini açıkla.
                    3. **Özet Yorum:** Yatırımcının dikkat etmesi gereken kritik noktalar ve riskler.
                    """

                    # Yoğunluk hatalarına karşı 3 kez tekrar deneme mantığı
                    max_retries = 3
                    response = None
                    
                    for attempt in range(max_retries):
                        try:
                            response = client.models.generate_content(
                                model="gemini-3.6-flash",
                                contents=prompt,
                            )
                            break
                        except Exception as e:
                            if "503" in str(e) or "UNAVAILABLE" in str(e):
                                if attempt < max_retries - 1:
                                    time.sleep(2)  # 2 saniye bekle ve tekrar dene
                                    continue
                            st.error(f"Yapay zeka analizi oluşturulurken bir hata oluştu: {e}")
                            break

                    if response:
                        st.success("Analiz Tamamlandı!")
                        st.markdown(response.text)
