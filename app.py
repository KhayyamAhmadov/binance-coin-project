import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

API_URL = "http://localhost:8000"
st.set_page_config(page_title="Crypto Dashboard", page_icon="💰", layout="wide")
st.title("💰 Crypto Dashboard")

try:
    response = requests.get(f"{API_URL}/coins")
    if response.status_code == 200:
        coins = response.json()["coins"]
    else:
        st.warning("Coin siyahısı yüklənmədi")
except:
    st.error("API-yə qoşulmaq mümkün olmadı")


st.sidebar.header("Coin Siyahısı")
response = requests.get(f"{API_URL}/coins/detail")
if response.status_code == 200:
    data = response.json()
    df = pd.DataFrame(data["coins"])
    st.sidebar.dataframe(df, use_container_width=True, hide_index=True, height=600)
else:
    st.error("Məlumat tapılmadı")
        

selected_coin = st.selectbox("🪙 Coin seçin", coins, key="coin_selector")
tab1, tab2, tab3, tab4 = st.tabs(["📊 Qiymət Tarixi", "📈 Statistika", "📉 Tarix Aralığı", "🔔 Alertlər"])

with tab1:
    st.subheader(f"{selected_coin} - Son Qiymətlər")
    limit = st.slider("Neçə məlumat göstərilsin?", 10, 100, 50)
    try:
        response = requests.get(f"{API_URL}/prices/{selected_coin}?limit={limit}")
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data["data"])
            st.metric("Məlumat sayı", data["count"])
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["OpenTime"], 
                y=df["ClosePrice"],
                mode='lines+markers',
                name='Qiymət'))
            
            fig.update_layout(
                title=f"{selected_coin} Qiymət Dəyişimi",
                xaxis_title="Tarix",
                yaxis_title="Qiymət (USD)")
            
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df, use_container_width=True)
        else:
            st.error("Məlumat tapılmadı")
    except Exception as e:
        st.error(f"Xəta: {str(e)}")

with tab2:
    st.subheader(f"{selected_coin} - Statistika")
    try:
        response = requests.get(f"{API_URL}/stats/{selected_coin}")
        if response.status_code == 200:
            stats = response.json()["stats"]
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Minimum Qiymət", f"${stats['min_price']:.2f}")
            col2.metric("Maksimum Qiymət", f"${stats['max_price']:.2f}")
            col3.metric("Orta Qiymət", f"${stats['avg_price']:.2f}")
            
            col4, col5, col6 = st.columns(3)
            col4.metric("Ümumi Məlumat", stats['total_records'])
            col5.metric("İlk Tarix", stats['first_date'])
            col6.metric("Son Tarix", stats['last_date'])
        else:
            st.error("Məlumat tapılmadı")
    except Exception as e:
        st.error(f"Xəta: {str(e)}")

with tab3:
    st.subheader(f"{selected_coin} - Tarix Aralığı")
    col1, col2 = st.columns(2)
    start_date = col1.date_input("Başlanğıc tarixi")
    end_date = col2.date_input("Son tarix")
    try:
        response = requests.get(f"{API_URL}/prices/range/{selected_coin}?start_date={start_date}&end_date={end_date}")
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data["data"])
            st.metric("Məlumat sayı", data["count"])
            
            fig = go.Figure(data=[go.Candlestick(
                x=df['OpenTime'],
                open=df['OpenPrice'],
                high=df['HighPrice'],
                low=df['LowPrice'],
                close=df['ClosePrice'])])
            
            fig.update_layout(
                title=f"{selected_coin} - Candlestick Chart",
                xaxis_title="Tarix",
                yaxis_title="Qiymət (USD)")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df, use_container_width=True)
        else:
            st.error("Məlumat tapılmadı")
    except Exception as e:
        st.error(f"Xəta: {str(e)}")


with tab4:
    st.subheader("🔔 Anomaly Alertlər")
    if st.button("🔄 Alert Yoxla", type="primary"):
        try:
            response = requests.get(f"{API_URL}/alert")
            if response.status_code == 200:
                data = response.json()
                st.metric("Ümumi Alert", data['totalAlerts'])
                
                if data['totalAlerts'] > 0:
                    st.markdown("---")
                    for alert in data['alerts']:
                        change = float(alert['changePercent'].replace('%', '').replace('+', ''))
                        emoji = "📈" if change > 0 else "📉"
                        color = "red" if abs(change) > 10 else "orange"
                        
                        with st.container():
                            col1, col2, col3, col4 = st.columns([1, 2, 3, 2])
                            col1.markdown(f"### {emoji}")
                            col2.markdown(f"**{alert['coin']}**")
                            col3.markdown(f":{color}[{alert['changePercent']}]")
                            col4.markdown(f"{alert['alertDate']}")
                            
                            with st.expander("Detallar"):
                                st.write(f"Cari qiymət: {alert['currentPrice']}")
                                st.write(f"Əvvəlki qiymət: {alert['referencePrice']}")
                                st.write(f"Alert tipi: {alert['alertType']}")
                            
                            st.markdown("---")
                else:
                    st.success("🟢 Anomaly tapılmadı")
            else:
                st.error("Məlumat tapılmadı")
        except Exception as e:
            st.error(f"Xəta: {str(e)}")

st.markdown("---")