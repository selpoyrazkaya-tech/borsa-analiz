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

st.sidebar.header("📊 Analiz Ayarları")
selected_ticker = st.sidebar.selectbox("Hisse Seçin:", options=BIST_TUM_HISSELER, index=BIST_TUM_HISSELER.index("THYAO.IS") if "THYAO.IS" in BIST_TUM_HISSELER else 0)
period = st.sidebar.selectbox("Zaman Aralığı:", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)

if selected_ticker:
    ticker_obj = yf.Ticker(selected_ticker)
    
    with st.spinner(f"{selected_ticker} verileri indiriliyor..."):
        data = ticker_obj.history(period=period, interval="1d")
        
        news_list = []
        try:
            raw_news = ticker_obj.news
            if raw_news:
                for item in raw_news[:5]:
                    title = item.get("title") or item.get("content", {}).get("title", "")
                    if title:
                        news_list.append(title)
        except Exception:
            pass
    
    if not data.empty and len(data) >= 30:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        high_series = data['High'].squeeze()
        low_series = data['Low'].squeeze()
        close_series = data['Close'].squeeze()
        volume_series = data['Volume'].squeeze()

        data['EMA_20'] = ta.trend.ema_indicator(close=close_series, window=20)
        data['EMA_50'] = ta.trend.ema_indicator(close=close_series, window=50)
        
        adx_class = ta.trend.ADXIndicator(high=high_series, low=low_series, close=close_series, window=14)
        data['ADX'] = adx_class.adx()
        
        data['RSI_14'] = ta.momentum.rsi(close=close_series, window=14)
        data['Vol_SMA20'] = volume_series.rolling(window=20).mean()

        last_close = round(float(close_series.iloc[-1]), 2)
        last_rsi = round(float(data['RSI_14'].iloc[-1]), 2)
        last_ema20 = round(float(data['EMA_20'].iloc[-1]), 2)
        last_ema50 = round(float(data['EMA_50'].iloc[-1]), 2)
        last_adx = round(float(data['ADX'].iloc[-1]), 2)
        
        last_vol = float(volume_series.iloc[-1])
        avg_vol = float(data['Vol_SMA20'].iloc[-1])
        vol_change_ratio = round(((last_vol - avg_vol) / avg_vol) * 100, 2) if avg_vol > 0 else 0

        # Grafik
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=data.index, open=data['Open'], high=data['High'],
            low=data['Low'], close=data['Close'], name="Fiyat"
        ))
        fig.add_trace(go.Scatter(x=data.index, y=data['EMA_20'], line=dict(color='orange', width=1.5), name="EMA 20"))
        fig.add_trace(go.Scatter(x=data.index, y=data['EMA_50'], line=dict(color='purple', width=1.5), name="EMA 50"))
        fig.update_layout(title=f"{selected_ticker} Fiyat Grafiği", xaxis_rangeslider_visible=False, height=450)
        st.plotly_chart(fig, use_container_width=True)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Son Fiyat", f"{last_close} TL")
        c2.metric("RSI (14)", last_rsi)
        c3.metric("ADX (Trend Gücü)", last_adx)
        c4.metric("EMA 20 / EMA 50", f"{last_ema20} / {last_ema50}")
        c5.metric("Hacim Değişimi", f"%{vol_change_ratio}")

        with st.expander("📰 Son Haber Başlıkları"):
            if news_list:
                for news in news_list:
                    st.write(f"• {news}")
            else:
                st.write("Güncel haber başlığı bulunamadı.")

        st.markdown("---")
        st.subheader("🤖 Yapay Zeka Hisse Analizi")

        if not API_KEY:
            st.warning("⚠️ Lütfen Streamlit Cloud 'Secrets' alanına geçerli bir API_KEY ekleyin.")
        else:
            if st.button("🚀 Stratejik Analizi Başlat"):
                with st.spinner("Analiz oluşturuluyor..."):
                    client = genai.Client(api_key=str(API_KEY).strip())
                    news_context = "\n".join([f"- {n}" for n in news_list]) if news_list else "Güncel haber yok."

                    prompt = f"""
                    Sen uzman bir Borsa İstanbul (BIST) analistisin.

                    Hisse: {selected_ticker}
                    Son Fiyat: {last_close} TL
                    EMA 20: {last_ema20} | EMA 50: {last_ema50}
                    ADX (Trend Gücü): {last_adx} | RSI: {last_rsi}
                    20 Günlük Ortalamaya Göre Hacim Değişimi: %{vol_change_ratio}
                    Son Haberler:
                    {news_context}

                    Gelişmiş teknik indikatörler, hacim ve haber akışını harmanlayarak stratejik bir analiz çıkart.
                    """

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
                            if ("503" in str(e) or "UNAVAILABLE" in str(e)) and attempt < max_retries - 1:
                                time.sleep(2)
                                continue
                            st.error(f"Analiz sırasında hata oluştu: {e}")
                            break

                    if response:
                        st.success("Analiz Tamamlandı!")
                        st.markdown(response.text)
    else:
        st.error("Seçilen zaman aralığı için yeterli veri çekilemedi. Lütfen sol menüden farklı bir 'Zaman Aralığı' seçin.")
