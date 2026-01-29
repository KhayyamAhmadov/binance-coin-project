import os
import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, mean_absolute_percentage_error
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from datetime import datetime
from database import execute_query


MODEL_FOLDER = "models"
LOOKBACK = 168
HORIZON = 3
EPOCHS = 100
BATCH_SIZE = 32

ALERT_THRESHOLD_PERCENT = 5.0
ALERT_MAPE_THRESHOLD = 15.0

os.makedirs(MODEL_FOLDER, exist_ok=True)


def get_all_coins():
    df = execute_query("SELECT Symbol FROM dbo.Coins")
    return df["Symbol"].tolist()


def load_price_data(symbol, limit=5000):
    query = """
        SELECT TOP (?)
            ph.OpenTime,
            ph.HighPrice,
            ph.LowPrice,
            ph.Volume,
            ph.ClosePrice,
            ph.OpenPrice
        FROM dbo.PriceHistory ph
        INNER JOIN dbo.Coins c ON ph.CoinID = c.CoinID
        WHERE c.Symbol = ?
        ORDER BY ph.OpenTime ASC
    """
    df = execute_query(query, params=(limit, symbol))
    df["OpenTime"] = pd.to_datetime(df["OpenTime"])
    df.set_index("OpenTime", inplace=True)
    return df


def add_features(df):
    df = df.copy()
    
    df["Volatility"] = df["HighPrice"] - df["LowPrice"]
    df["SMA_7"] = df["ClosePrice"].rolling(window=7, min_periods=1).mean()
    df["SMA_30"] = df["ClosePrice"].rolling(window=30, min_periods=1).mean()
    delta = df["ClosePrice"].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14, min_periods=1).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=14, min_periods=1).mean()
    rs = gain / (loss + 1e-10)
    df["RSI"] = 100 - (100 / (1 + rs))
    ema_12 = df["ClosePrice"].ewm(span=12, adjust=False).mean()
    ema_26 = df["ClosePrice"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema_12 - ema_26
    df["Volume_MA"] = df["Volume"].rolling(window=7, min_periods=1).mean()
    df = df.iloc[30:].copy()
    df = df.fillna(method='bfill').fillna(method='ffill').fillna(0)
    
    features = ["ClosePrice", "Volume", "Volatility", "SMA_7", "SMA_30", "RSI", "MACD", "Volume_MA"]
    
    return df[features]


def create_sequences(data, lookback, horizon):
    X, y = [], []
    for i in range(lookback, len(data) - horizon + 1):
        X.append(data[i - lookback:i])
        y.append(data[i:i + horizon, 0])
    return np.array(X), np.array(y)


def build_lstm(input_shape):
    model = Sequential([
        Bidirectional(LSTM(128, return_sequences=True), input_shape=input_shape),
        Dropout(0.3),
        Bidirectional(LSTM(64, return_sequences=True)),
        Dropout(0.3),
        LSTM(64, return_sequences=True),
        Dropout(0.2),
        LSTM(32),
        Dropout(0.2),
        Dense(64, activation="relu"),
        Dropout(0.2),
        Dense(32, activation="relu"),
        Dense(HORIZON)])
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model


def send_alert(symbol, alert_type, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    alert_msg = f"\n{'='*60}\n🚨 ALERT [{alert_type}] - {symbol}\n{timestamp}\n{message}\n{'='*60}\n"
    
    print(alert_msg)
    
    log_file = f"{MODEL_FOLDER}/alerts.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(alert_msg)


def check_prediction_alerts(symbol, current_price, predictions):
    alerts = []
    for i, pred in enumerate(predictions, 1):
        pct_change = ((pred - current_price) / current_price) * 100
        if abs(pct_change) >= ALERT_THRESHOLD_PERCENT:
            direction = "YÜKSƏLMƏ" if pct_change > 0 else "DÜŞMƏ"
            alert_msg = (
                f"Day +{i}: Keskin {direction} gözlənilir!\n"
                f"   Cari qiymət: ${current_price:.2f}\n"
                f"   Proqnoz: ${pred:.2f}\n"
                f"   Dəyişiklik: {pct_change:+.2f}%")
            alerts.append(alert_msg)
    
    if alerts:
        full_message = "\n".join(alerts)
        send_alert(symbol, "PREDICTION", full_message)


def check_evaluation_alerts(symbol, mape_values):
    avg_mape = np.mean(mape_values)
    if avg_mape >= ALERT_MAPE_THRESHOLD:
        alert_msg = (
            f"Dəqiqliyi aşağıdır!\n"
            f"   Ortalama MAPE: {avg_mape:.2f}%\n"
            f"   Threshold: {ALERT_MAPE_THRESHOLD}%")
        send_alert(symbol, "LOW ACCURACY", alert_msg)


def train_lstm(symbol):
    df = load_price_data(symbol)
    if df.empty or len(df) < LOOKBACK + HORIZON + 100:
        return None, None, None

    features = add_features(df)
    if features.empty or len(features) < LOOKBACK + HORIZON:
        return None, None, None
    
    split_idx = int(len(features) * 0.8)
    train_features = features.iloc[:split_idx]
    test_features = features.iloc[split_idx:]
    
    scaler = MinMaxScaler()
    scaler.fit(train_features.values)

    train_scaled = scaler.transform(train_features.values)
    test_scaled = scaler.transform(test_features.values)
    
    X_train, y_train = create_sequences(train_scaled, LOOKBACK, HORIZON)
    X_test, y_test = create_sequences(test_scaled, LOOKBACK, HORIZON)
    
    if len(X_train) < 100 or len(X_test) < 20:
        return None, None, None
    
    val_size = int(len(X_train) * 0.15)
    X_val = X_train[-val_size:]
    y_val = y_train[-val_size:]
    X_train = X_train[:-val_size]
    y_train = y_train[:-val_size]

    model = build_lstm((LOOKBACK, X_train.shape[2]))

    early_stop = EarlyStopping(
        monitor="val_loss",
        patience=20,
        restore_best_weights=True,
        verbose=0)
    
    reduce_lr = ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.5,
        patience=10,
        min_lr=0.00001,
        verbose=0)

    model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=[early_stop, reduce_lr],
        verbose=1)

    return model, scaler, (X_test, y_test, features.shape[1])


def evaluate_model(symbol, model, scaler, test_data):
    X_test, y_test, feature_count = test_data
    preds = model.predict(X_test, verbose=0)

    y_true, y_pred = [], []

    for i in range(len(y_test)):
        dy = np.zeros((HORIZON, feature_count))
        dp = np.zeros((HORIZON, feature_count))
        dy[:, 0] = y_test[i]
        dp[:, 0] = preds[i]
        y_true.append(scaler.inverse_transform(dy)[:, 0])
        y_pred.append(scaler.inverse_transform(dp)[:, 0])

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    mape_values = []
    
    for h in range(HORIZON):
        mape = mean_absolute_percentage_error(y_true[:, h], y_pred[:, h]) * 100
        mape_values.append(mape)
    
    check_evaluation_alerts(symbol, mape_values)


def predict_next_3_days(model, scaler, df):
    features = add_features(df)
    
    if len(features) < LOOKBACK:
        return None
    
    last_window = features.values[-LOOKBACK:]
    scaled = scaler.transform(last_window)
    X_input = np.expand_dims(scaled, axis=0)
    pred_scaled = model.predict(X_input, verbose=0)[0]
    dummy = np.zeros((HORIZON, features.shape[1]))
    dummy[:, 0] = pred_scaled

    return scaler.inverse_transform(dummy)[:, 0]


def run_all():
    log_file = f"{MODEL_FOLDER}/alerts.log"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"=== Alert Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
    
    coins = get_all_coins()
    
    for coin in coins:
        print(f"\nProcessing {coin}...")

        model, scaler, test_data = train_lstm(coin)
        
        if model is None:
            continue

        model.save(f"{MODEL_FOLDER}/lstm_{coin}.keras")
        with open(f"{MODEL_FOLDER}/lstm_{coin}_scaler.pkl", "wb") as f:
            pickle.dump(scaler, f)

        evaluate_model(coin, model, scaler, test_data)

        df_latest = load_price_data(coin)
        preds = predict_next_3_days(model, scaler, df_latest)

        if preds is not None:
            current = df_latest["ClosePrice"].iloc[-1]
            check_prediction_alerts(coin, current, preds)
        
        print(f"{coin} completed")


if __name__ == "__main__":
    run_all()