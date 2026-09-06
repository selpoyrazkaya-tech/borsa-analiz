import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go
from google import genai
import time

st.set_page_config(page_title="Yapay Zeka & Çoklu Strateji BIST Analiz", layout="wide")
st.title("📈 BIST - Trend, Hacim, Haber & Yapay Zeka Analiz Stratejisi")

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
    
    with st.spinner(f"{selected_ticker} verileri ve haberleri indiriliyor..."):
        data = ticker_obj.history(period=period, interval="1d")
        
        # Son Haberleri Çekme
        news_list = []
        try:
            raw_news = ticker_obj.news
            if raw_news:
                for item in raw_news[:5]:  # Son 5 haber
                    title = item.get("title") or item.get("content", {}).get("title", "")
                    if title:
                        news_list.append(title)
        except Exception:
            pass
    
    if not data.empty:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # --- 1. İNDİKATÖR HESAPLAMALARI ---
        # Trend İndikatörleri
        data['EMA_20'] = ta.trend.ema_indicator(close=data['Close'], window=20)
        data['EMA_50'] = ta.trend.ema_indicator(close=data['Close'], window=50)
        data['ADX'] = ta.trend.adx(high=data['High'], low=data['Low'], close=data['Close'], window=14)
        
        # Momentum İndikatörleri
        data['RSI_14'] = ta.momentum.rsi(close=data['Close'], window=14)
        
        # Hacim İndikatörleri
        data['Vol_SMA20'] = data['Volume'].rolling(window=20).mean()
        data['OBV'] = ta.volume.on_balance_volume(close=data['Close'], volume=data['Volume'])

        # --- 2. TEKNİK VERİ METRİKLERİ ---
        last_close = round(float(data['Close'].iloc[-1]), 2)
        last_rsi = round(float(data['RSI_14'].iloc[-1]), 2)
        last_ema20 = round(float(data['EMA_20'].iloc[-1]), 2)
        last_ema50 = round(float(data['EMA_50'].iloc[-1]), 2)
        last_adx = round(float(data['ADX'].iloc[-1]), 2)
        
        last_vol = float(data['Volume'].iloc[-1])
        avg_vol = float(data['Vol_SMA20'].iloc[-1])
        vol_change_ratio = round(((last_vol - avg_vol) / avg_vol) * 100, 2)

        # --- 3. GRAFİK ÇİZİMİ ---
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=data.index, open=data['Open'], high=data['High'],
            low=data['Low'], close=data['Close'], name="Fiyat"
        ))
        fig.add_trace(go.Scatter(x=data.index, y=data['EMA_20'], line=dict(color='orange', width=1.5), name="EMA 20 (Trend)"))
        fig.add_trace(go.Scatter(x=data.index, y=data['EMA_50'], line=dict(color='purple', width=1.5), name="EMA 50 (Ana Trend)"))
        fig.update_layout(title=f"{selected_ticker} Fiyat ve Trend Grafiği", xaxis_rangeslider_visible=False, height=450)
        st.plotly_chart(fig, width='stretch')

        # Metrikler
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Son Fiyat", f"{last_close} TL")
        c2.metric("RSI (14)", last_rsi)
        c3.metric("ADX (Trend Gücü)", last_adx, delta="Güçlü Trend" if last_adx > 25 else "Zayıf/Yatay")
        c4.metric("EMA 20 / EMA 50", f"{last_ema20} / {last_ema50}")
        c5.metric("Hacim Değişimi (vs 20G Ortalama)", f"%{vol_change_ratio}", delta_color="normal")

        # Haber Listesi Gösterimi
        with st.expander("📰 Son Haber Başlıkları (Piyasa Akışı)"):
            if news_list:
                for news in news_list:
                    st.write(f"• {news}")
            else:
                st.write("Güncel haber başlığı bulunamadı.")

        st.markdown("---")
        st.subheader("🤖 Stratejik Yapay Zeka Analiz Raporu")

        if not API_KEY:
            st.warning("⚠️ Lütfen Streamlit Cloud 'Secrets' alanına geçerli bir API_KEY ekleyin.")
        else:
            if st.button("🚀 Stratejik Analizi Başlat"):
                with st.spinner("Trend, Hacim ve Haber verileri harmanlanarak analiz oluşturuluyor..."):
                    client = genai.Client(api_key=str(API_KEY).strip())

                    news_context = "\n".join([f"- {n}" for n in news_list]) if news_list else "Güncel haber bulunamadı."

                    prompt = f"""
                    Sen TradingView indikatörleri, Hacim analizi ve Haber Akışını birleştiren disiplinli bir Borsa İstanbul (BIST) Cant/Quant Analistisin.

                    **Hisse:** {selected_ticker}
                    
                    **1. Trend İndikatörleri:**
                    - Kapanış Fiyatı: {last_close} TL
                    - EMA 20: {last_ema20} TL
                    - EMA 50: {last_ema50} TL
                    - ADX (Trend Güç İndeksi): {last_adx} (25 üzeri güçlü trend gösterir)

                    **2. Momentum & Hacim Verileri:**
                    - RSI (14): {last_rsi}
                    - Son Gün Hacim Değişimi (20 Günlük Ortalamaya Göre): %{vol_change_ratio}

                    **3. Son Haber Başlıkları:**
                    {news_context}

                    ---
                    **İSTENEN STRATEJİK ANALİZ FORMATI:**

                    🎯 **1. Genel Strateji Sinyali:** (NET BİR EYLEM: Güçlü Al / Kademeli Al / Nötr-İzle / Kar Al / Sat)
                    
                    📈 **2. Trend & Hacim Teyidi:**
                    - EMA 20 ve EMA 50 ilişkisi ne söylüyor?
                    - ADX değerine göre trend ne kadar güçlü?
                    - Hacim değişimi fiyat hareketini destekliyor mu (Para girişi var mı)?

                    📰 **3. Haber & Temel Duygu Analizi:**
                    - Haber başlıkları hisse üzerinde pozitif/negatif bir etki yaratıyor mu?

                    ⚠️ **4. Riskler & Kritik Seviyeler:**
                    - Stop-loss ve Kar-al için dikkat edilmesi gereken EMA veya teknik destek/direnç noktaları.
                    """

                    max_retries = 3
                    response = None
                    
                    for attempt in range(max_retries):
                        try:
                            response = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=prompt,
                            )
                            break
                        except Exception as e:
                            if "503" in str(e) or "UNAVAILABLE" in str(e):
                                if attempt < max_retries - 1:
                                    time.sleep(2)
                                    continue
                            # Yedek olarak 3.6-flash dene
                            try:
                                response = client.models.generate_content(
                                    model="gemini-3.6-flash",
                                    contents=prompt,
                                )
                                break
                            except Exception:
                                st.error(f"Yapay zeka analizi oluşturulurken hata oluştu: {e}")
                                break

                    if response:
                        st.success("Stratejik Analiz Tamamlandı!")
                        st.markdown(response.text)
