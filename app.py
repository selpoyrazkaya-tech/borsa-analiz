import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go
from google import genai
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import time

st.set_page_config(page_title="Yapay Zeka & Güncel Haber Destekli BIST Analiz", layout="wide")

# Session State Tanımlamaları
if "favorites" not in st.session_state:
    st.session_state.favorites = []

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = "ASELS.IS"

st.title("📈 Borsa İstanbul - Güncel Haber & Yapay Zeka Analiz Uygulaması")

# Streamlit Secrets'tan API Key Okuma
try:
    API_KEY = st.secrets["API_KEY"]
except Exception:
    API_KEY = None

# Borsa İstanbul Hisse Listesi (ISMEN.IS alfabetik sıraya tam eklendi)
BIST_TUM_HISSELER = sorted([
    "A1CAP.IS", "ACSEL.IS", "ADEL.IS", "ADESE.IS", "AEFES.IS", "AFYON.IS", "AGESA.IS", 
    "AGHOL.IS", "AGROT.IS", "AHGAZ.IS", "AKBNK.IS", "AKCNS.IS", "AKFGY.IS", "AKSA.IS", 
    "AKSEN.IS", "ALARK.IS", "ALBRK.IS", "ALFAS.IS", "ARCLK.IS", "ARDYZ.IS", "ASELS.IS", 
    "ASTOR.IS", "AYDEM.IS", "BIMAS.IS", "BKRGY.IS", "BRSAN.IS", "CANTE.IS", "CCOLA.IS", "CWENE.IS", 
    "DOAS.IS", "DOHOL.IS", "ECILC.IS", "EGEEN.IS", "EKGYO.IS", "ENJSA.IS", "ENKAI.IS", 
    "EREGL.IS", "EUPWR.IS", "FROTO.IS", "GARAN.IS", "GESAN.IS", "GUBRF.IS", "HALKB.IS", 
    "HEKTS.IS", "INTET.IS", "ISCTR.IS", "ISMEN.IS", "KCAER.IS", "KCHOL.IS", "KONTR.IS", "KOZAL.IS", "KRDMD.IS", 
    "MIATK.IS", "ODAS.IS", "OTKAR.IS", "OYAKC.IS", "PETKM.IS", "PGSUS.IS", "REEDR.IS", 
    "SAHOL.IS", "SASA.IS", "SISE.IS", "SKBNK.IS", "SMRTG.IS", "SOKM.IS", "TAVHL.IS", 
    "TCELL.IS", "THYAO.IS", "TKFEN.IS", "TOASO.IS", "TSKB.IS", "TTKOM.IS", "TTRAK.IS", 
    "TUPRS.IS", "ULKER.IS", "VAKBN.IS", "VESBE.IS", "VESTL.IS", "YKBNK.IS", "ZOREN.IS"
])

def get_latest_news(ticker_symbol):
    clean_ticker = ticker_symbol.replace(".IS", "")
    query = f"{clean_ticker} hisse"
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=tr&gl=TR&ceid=TR:tr"
    
    news_items = []
    try:
        req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            
            for item in root.findall('.//item')[:5]:
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                if title:
                    news_items.append({"title": title, "link": link})
    except Exception:
        pass
        
    return news_items

# --- SOL MENÜ (SIDEBAR) ---
st.sidebar.header("📊 Analiz Ayarları")

current_ticker = st.session_state.selected_ticker
default_index = BIST_TUM_HISSELER.index(current_ticker) if current_ticker in BIST_TUM_HISSELER else 0

selected_ticker_input = st.sidebar.selectbox(
    "Hisse Seçin:", 
    options=BIST_TUM_HISSELER, 
    index=default_index
)

if selected_ticker_input != st.session_state.selected_ticker:
    st.session_state.selected_ticker = selected_ticker_input
    st.rerun()

period = st.sidebar.selectbox("Zaman Aralığı:", ["1mo", "3mo", "6mo", "1y", "2y"], index=0)

# FAVORİLER BÖLÜMÜ
st.sidebar.markdown("---")
st.sidebar.header("⭐ Favori Hisselerim")

if st.session_state.favorites:
    for fav in st.session_state.favorites:
        col1, col2 = st.sidebar.columns([3, 1])
        if col1.button(f"📌 {fav}", key=f"btn_{fav}"):
            st.session_state.selected_ticker = fav
            st.rerun()
        if col2.button("❌", key=f"del_{fav}"):
            st.session_state.favorites.remove(fav)
            st.rerun()
else:
    st.sidebar.info("Henüz favori hisse eklemediniz.")

# PORTFÖYÜM BÖLÜMÜ
st.sidebar.markdown("---")
st.sidebar.header("💼 Portföyüm")

with st.sidebar.expander("➕ Portföye Hisse Ekle/Güncelle"):
    pf_ticker = st.selectbox("Hisse:", options=BIST_TUM_HISSELER, key="pf_ticker_select")
    pf_amount = st.number_input("Adet:", min_value=1, value=100, step=1, key="pf_amount_input")
    pf_cost = st.number_input("Maliyet (TL):", min_value=0.01, value=10.0, step=0.1, format="%.2f", key="pf_cost_input")
    
    if st.button("Portföye Ekle", key="pf_add_btn"):
        existing = next((item for item in st.session_state.portfolio if item['ticker'] == pf_ticker), None)
        if existing:
            existing['amount'] = pf_amount
            existing['cost'] = pf_cost
        else:
            st.session_state.portfolio.append({"ticker": pf_ticker, "amount": pf_amount, "cost": pf_cost})
        st.success(f"{pf_ticker} portföye eklendi.")
        st.rerun()

if st.session_state.portfolio:
    total_cost = 0.0
    total_val = 0.0

    for idx, item in enumerate(st.session_state.portfolio):
        t_symbol = item["ticker"]
        amt = item["amount"]
        c_price = item["cost"]
        
        try:
            live_data = yf.Ticker(t_symbol).history(period="1d")
            curr_price = float(live_data['Close'].iloc[-1]) if not live_data.empty else c_price
        except Exception:
            curr_price = c_price

        item_total_cost = amt * c_price
        item_total_val = amt * curr_price
        profit_loss = item_total_val - item_total_cost
        profit_loss_pct = ((curr_price - c_price) / c_price) * 100 if c_price > 0 else 0.0

        total_cost += item_total_cost
        total_val += item_total_val

        st.sidebar.markdown(f"**{t_symbol}** ({amt} Adet)")
        st.sidebar.caption(f"Maliyet: {c_price:.2f} TL | Anlık: {curr_price:.2f} TL")
        
        p_color = "🟢" if profit_loss >= 0 else "🔴"
        st.sidebar.write(f"{p_color} K/Z: {profit_loss:+.2f} TL (%{profit_loss_pct:+.2f})")

        p_col1, p_col2 = st.sidebar.columns([3, 1])
        if p_col1.button(f"📌 Analiz Et", key=f"pf_goto_{t_symbol}_{idx}"):
            st.session_state.selected_ticker = t_symbol
            st.rerun()
        if p_col2.button("❌", key=f"pf_del_{t_symbol}_{idx}"):
            st.session_state.portfolio.pop(idx)
            st.rerun()
        st.sidebar.markdown("<hr style='margin:5px 0;'>", unsafe_allow_html=True)

    total_profit_loss = total_val - total_cost
    total_profit_loss_pct = ((total_val - total_cost) / total_cost) * 100 if total_cost > 0 else 0.0
    
    st.sidebar.markdown("### 📊 Toplam Portföy Özeti")
    st.sidebar.write(f"**Toplam Değer:** {total_val:,.2f} TL")
    st.sidebar.write(f"**Toplam Kar/Zarar:** {total_profit_loss:+,.2f} TL (%{total_profit_loss_pct:+.2f})")
else:
    st.sidebar.info("Portföyünüzde henüz hisse bulunmuyor.")


# --- ANA EKRAN VE ANALİZ ---
selected_ticker = st.session_state.selected_ticker

if selected_ticker:
    col_title, col_fav = st.columns([4, 1])
    with col_title:
        st.subheader(f"📌 Seçili Hisse: {selected_ticker}")
    with col_fav:
        is_fav = selected_ticker in st.session_state.favorites
        fav_btn_label = "⭐ Favorilerden Çıkar" if is_fav else "⭐ Favorilere Ekle"
        if st.button(fav_btn_label, key="fav_toggle"):
            if is_fav:
                st.session_state.favorites.remove(selected_ticker)
            else:
                st.session_state.favorites.append(selected_ticker)
            st.rerun()

    ticker_obj = yf.Ticker(selected_ticker)
    
    with st.spinner(f"{selected_ticker} verileri indiriliyor..."):
        data = ticker_obj.history(period="max", interval="1d")
        news_list = get_latest_news(selected_ticker)
    
    if not data.empty and len(data) >= 1:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        high_series = data['High'].squeeze()
        low_series = data['Low'].squeeze()
        close_series = data['Close'].squeeze()
        volume_series = data['Volume'].squeeze()

        bar_count = len(data)
        
        data['EMA_20'] = ta.trend.ema_indicator(close=close_series, window=min(bar_count, 20)) if bar_count >= 2 else close_series
        data['EMA_50'] = ta.trend.ema_indicator(close=close_series, window=min(bar_count, 50)) if bar_count >= 2 else close_series
        
        try:
            if bar_count >= 14:
                adx_class = ta.trend.ADXIndicator(high=high_series, low=low_series, close=close_series, window=14)
                data['ADX'] = adx_class.adx()
            else:
                data['ADX'] = 0
        except Exception:
            data['ADX'] = 0

        try:
            if bar_count >= 14:
                data['RSI_14'] = ta.momentum.rsi(close=close_series, window=14)
            else:
                data['RSI_14'] = 50
        except Exception:
            data['RSI_14'] = 50

        data['Vol_SMA20'] = volume_series.rolling(window=min(bar_count, 20)).mean()

        filter_days = {"1mo": 22, "3mo": 65, "6mo": 130, "1y": 252, "2y": 504}
        days_to_show = filter_days.get(period, 22)
        plot_data = data.tail(days_to_show)

        last_close = round(float(close_series.iloc[-1]), 2)
        
        rsi_valid = data['RSI_14'].dropna()
        last_rsi = round(float(rsi_valid.iloc[-1]), 2) if not rsi_valid.empty else "N/A"
        
        ema20_valid = data['EMA_20'].dropna()
        last_ema20 = round(float(ema20_valid.iloc[-1]), 2) if not ema20_valid.empty else "N/A"
        
        ema50_valid = data['EMA_50'].dropna()
        last_ema50 = round(float(ema50_valid.iloc[-1]), 2) if not ema50_valid.empty else "N/A"
        
        adx_valid = data['ADX'].dropna()
        last_adx = round(float(adx_valid.iloc[-1]), 2) if not adx_valid.empty else "N/A"
        
        last_vol = float(volume_series.iloc[-1])
        vol_valid = data['Vol_SMA20'].dropna()
        avg_vol = float(vol_valid.iloc[-1]) if not vol_valid.empty else last_vol
        vol_change_ratio = round(((last_vol - avg_vol) / avg_vol) * 100, 2) if avg_vol > 0 else 0

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=plot_data.index, open=plot_data['Open'], high=plot_data['High'],
            low=plot_data['Low'], close=plot_data['Close'], name="Fiyat"
        ))
        if 'EMA_20' in plot_data and not plot_data['EMA_20'].isna().all():
            fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data['EMA_20'], line=dict(color='orange', width=1.5), name="EMA 20"))
        if 'EMA_50' in plot_data and not plot_data['EMA_50'].isna().all():
            fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data['EMA_50'], line=dict(color='purple', width=1.5), name="EMA 50"))
        
        fig.update_layout(title=f"{selected_ticker} Fiyat Grafiği ({period})", xaxis_rangeslider_visible=False, height=450)
        st.plotly_chart(fig, use_container_width=True)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Son Fiyat", f"{last_close} TL")
        c2.metric("RSI (14)", last_rsi)
        c3.metric("ADX (Trend)", last_adx)
        c4.metric("EMA 20 / EMA 50", f"{last_ema20} / {last_ema50}")
        c5.metric("Hacim Değişimi", f"%{vol_change_ratio}")

        with st.expander("📰 Anlık Güncel Haberler (Google News)"):
            if news_list:
                for n in news_list:
                    st.markdown(f"• [{n['title']}]({n['link']})")
            else:
                st.write("Güncel haber başlığı bulunamadı.")

        st.markdown("---")
        st.subheader("🤖 Haber & Teknik Odaklı Yapay Zeka Analizi")

        if not API_KEY:
            st.warning("⚠️ Lütfen Streamlit Cloud 'Secrets' alanına geçerli bir API_KEY ekleyin.")
        else:
            if st.button("🚀 Stratejik Analizi Başlat"):
                with st.spinner("Güncel haberler ve teknik indikatörler analiz ediliyor..."):
                    client = genai.Client(api_key=str(API_KEY).strip())
                    news_titles = "\n".join([f"- {n['title']}" for n in news_list]) if news_list else "Güncel haber bulunamadı."

                    prompt = f"""
                    Sen uzman bir Borsa İstanbul (BIST) finansal analistisin.

                    **Hisse:** {selected_ticker}
                    **Teknik Göstergeler:**
                    - Son Fiyat: {last_close} TL
                    - EMA 20: {last_ema20} TL | EMA 50: {last_ema50} TL
                    - ADX (Trend Gücü): {last_adx}
                    - RSI (14): {last_rsi}
                    - Hacim Değişimi: %{vol_change_ratio}

                    **Son Güncel Haber Başlıkları:**
                    {news_titles}

                    **GÖREV:**
                    1. Teknik indikatörleri yorumla (Trend yönü ve gücü).
                    2. Çekilen haber başlıklarının hisse üzerindeki olası duygu etkisini (Pozitif/Negatif/Nötr) değerlendir.
                    3. Teknik ve haber verilerini birleştirerek yatırımcı için somut bir strateji/beklenti özeti sun.
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
        st.error("Seçilen hisse için yeterli veri çekilemedi. Lütfen geçerli bir BIST hissesi seçin.")
