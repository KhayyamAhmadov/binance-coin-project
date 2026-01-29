import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database import execute_query, execute_non_query

def get_all_coins():
    query = "SELECT CoinID, Symbol FROM dbo.Coins ORDER BY Symbol"
    df = execute_query(query)
    if df is not None and not df.empty:
        return df.to_dict('records')
    return []


def get_price_history(coin_id, days=100):
    query = """
        SELECT TOP (?) CloseTime, ClosePrice
        FROM dbo.PriceHistory
        WHERE CoinID = ?
        ORDER BY CloseTime DESC
    """
    df = execute_query(query, params=(days, coin_id))
    if df is not None and not df.empty:
        df = df.sort_values('CloseTime').reset_index(drop=True)
        return df
    return None


def get_last_processed_date(coin_id):
    query = """
        SELECT TOP 1 AlertDate
        FROM dbo.AnomalyAlerts
        WHERE CoinID = ?
        ORDER BY AlertDate DESC
    """
    df = execute_query(query, params=(coin_id,))
    if df is not None and not df.empty:
        return pd.to_datetime(df['AlertDate'].iloc[0]).date()
    return None


def check_alerts_for_coin(coin):
    coin_id = coin['CoinID']
    symbol = coin['Symbol']
    df = get_price_history(coin_id, days=100)
    
    if df is None or len(df) < 10:
        return None 
    
    last_close_time = df['CloseTime'].iloc[-1]
    last_close_date = pd.to_datetime(last_close_time).date()
    last_processed = get_last_processed_date(coin_id)
    if last_processed and last_close_date <= last_processed:
        return None
    
    df['ChangePercent'] = df['ClosePrice'].pct_change() * 100
    valid_changes = df['ChangePercent'].dropna()
    if len(valid_changes) < 5:
        return None
    
    mean_change = valid_changes.abs().mean()
    last_change = df['ChangePercent'].iloc[-1]
    if pd.isna(last_change):
        return None
    
    threshold = max(mean_change * 3, 5.0)
    alert = None
    if abs(last_change) >= threshold:
        alert = {
            'CoinID': coin_id,
            'CoinSymbol': symbol,
            'CurrentPrice': float(df['ClosePrice'].iloc[-1]),
            'ReferencePrice': float(df['ClosePrice'].iloc[-2]),
            'ChangePercent': float(last_change),
            'AlertType': 'Böyük dəyişiklik',
            'AlertDate': last_close_date}
        save_alert(alert)
    
    return alert


def save_alert(alert):
    query = """
        INSERT INTO dbo.AnomalyAlerts
        (CoinID, CurrentPrice, ReferencePrice, ChangePercent, AlertType, AlertDate)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    params = (alert['CoinID'], alert['CurrentPrice'], alert['ReferencePrice'], alert['ChangePercent'], alert['AlertType'], alert['AlertDate'])
    execute_non_query(query, params)


def check_all_coins():
    print("\n" + "="*60)
    print(" - ALERT SİSTEMİ BAŞLADI")
    print("="*60)
    
    coins = get_all_coins()
    if not coins:
        print(" - Coin tapılmadı")
        return []
    
    print(f" - Yoxlanılacaq coinlər: {len(coins)}")
    print("-"*60)
    
    alerts = []
    for coin in coins:
        alert = check_alerts_for_coin(coin)
        if alert:
            alerts.append(alert)
            emoji = "📈" if alert['ChangePercent'] > 0 else "📉"
            print(f"{emoji} ALERT: {alert['CoinSymbol']:6s} | "
                  f"Dəyişiklik: {alert['ChangePercent']:+7.2f}% | "
                  f"Qiymət: ${alert['CurrentPrice']:.6f}")
    
    print("-"*60)
    if alerts:
        print(f" - Alert verilən coinlər: {len(alerts)}")
    else:
        print(" - Anomaly tapılmadı")
    print("="*60 + "\n")
    
    return alerts


if __name__ == "__main__":
    alerts = check_all_coins()