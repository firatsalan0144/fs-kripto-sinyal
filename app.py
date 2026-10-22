import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(
    page_title="FS Kripto Sinyal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp { max-width: 100%; }
    .signal-long { background-color: #0d9488; color: white; padding: 12px; border-radius: 10px; margin: 8px 0; }
    .signal-short { background-color: #dc2626; color: white; padding: 12px; border-radius: 10px; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

st.title("📈 FS Kripto Sinyal Dashboard")
st.caption("Binance Futures · Para Akışı Proxy + Destek/Direnç · Canlı")

@st.cache_data(ttl=60)
def get_futures_tickers():
    try:
        url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
        r = requests.get(url, timeout=10)
        data = r.json()
        if not isinstance(data, list) or len(data) == 0:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        df = df[df['symbol'].str.endswith('USDT')].copy()
        df['priceChangePercent'] = pd.to_numeric(df['priceChangePercent'], errors='coerce')
        df['quoteVolume'] = pd.to_numeric(df['quoteVolume'], errors='coerce')
        df['lastPrice'] = pd.to_numeric(df['lastPrice'], errors='coerce')
        df = df.dropna(subset=['priceChangePercent', 'quoteVolume', 'lastPrice'])
        return df.sort_values('quoteVolume', ascending=False).head(80)
    except Exception as e:
        st.error(f"Veri alınamadı: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=120)
def get_oi_and_ratio(symbol):
    try:
        oi = requests.get(f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}", timeout=5).json()
        ls = requests.get(f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={symbol}&period=5m&limit=1", timeout=5).json()
        return {
            "oi": float(oi.get("openInterest", 0)),
            "longShort": float(ls[0]["longShortRatio"]) if ls and len(ls) > 0 else 1.0
        }
    except:
        return {"oi": 0, "longShort": 1.0}

def simple_sr(price, change):
    support = price * (1 - abs(change)/100 * 0.6)
    resistance = price * (1 + abs(change)/100 * 0.6)
    return round(support, 4), round(resistance, 4)

df = get_futures_tickers()

if df.empty:
    st.warning("Veri yükleniyor veya hata oluştu. Sayfayı yenile.")
    st.stop()

st.subheader("🔥 Aktif Sinyaller (Top Hacim)")

signals = []
for _, row in df.head(30).iterrows():
    symbol = row['symbol']
    price = float(row['lastPrice'])
    change = float(row['priceChangePercent'])
    vol = float(row['quoteVolume'])
    
    extra = get_oi_and_ratio(symbol)
    support, resistance = simple_sr(price, change)
    
    signal = None
    reason = ""
    if change > 3 and extra["longShort"] > 1.15 and price > support * 1.01:
        signal = "LONG"
        reason = f"Yükseliş + Long bias ({extra['longShort']:.2f}) + Destek üstü"
    elif change < -3 and extra["longShort"] < 0.85 and price < resistance * 0.99:
        signal = "SHORT"
        reason = f"Düşüş + Short bias ({extra['longShort']:.2f}) + Direnç altı"
    elif abs(change) > 5:
        signal = "LONG" if change > 0 else "SHORT"
        reason = f"Güçlü hareket %{change:.1f}"
    
    if signal:
        signals.append({
            "symbol": symbol,
            "signal": signal,
            "price": price,
            "change": change,
            "support": support,
            "resistance": resistance,
            "longShort": extra["longShort"],
            "reason": reason,
            "vol": vol
        })

if not signals:
    st.info("Şu an güçlü sinyal yok. Piyasa sakin veya filtre sıkı. Birkaç dakika sonra yenile.")
else:
    for s in signals[:12]:
        css = "signal-long" if s["signal"] == "LONG" else "signal-short"
        st.markdown(f"""
        <div class="{css}">
            <b>{s['symbol']}</b> → <b>{s['signal']}</b><br>
            Fiyat: ${s['price']:.4f} | Değişim: {s['change']:.2f}%<br>
            Destek: {s['support']} | Direnç: {s['resistance']}<br>
            L/S Ratio: {s['longShort']:.2f}<br>
            <small>{s['reason']}</small>
        </div>
        """, unsafe_allow_html=True)

st.divider()
st.subheader("📊 En Yüksek Hacimli Coinler")
show_df = df[['symbol', 'lastPrice', 'priceChangePercent', 'quoteVolume']].head(20).copy()
show_df.columns = ['Coin', 'Fiyat', '24s %', 'Hacim (USDT)']
st.dataframe(show_df, use_container_width=True, hide_index=True)

st.caption(f"Son güncelleme: {datetime.now().strftime('%H:%M:%S')} · Ücretsiz Binance public data · Sinyaller test amaçlıdır.")

if st.button("🔄 Yenile"):
    st.cache_data.clear()
    st.rerun()
