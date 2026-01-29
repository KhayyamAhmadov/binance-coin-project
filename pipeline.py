from binance.spot import Spot
import pandas as pd
import time
import os
from dotenv import load_dotenv
from datetime import datetime
from database import execute_non_query, execute_query
from coins import COINS

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

client = Spot(api_key=API_KEY, api_secret=API_SECRET)
INTERVAL = "1d"
DEFAULT_START = datetime(2017, 8, 17)

def get_or_create_coin(pair_symbol: str) -> str:
    symbol = pair_symbol.replace("USDT", "")
    df = execute_query("select CoinID from dbo.Coins where PairSymbol = ?", (pair_symbol,))

    if df is not None and not df.empty:
        return int(df.iloc[0]["CoinID"])
    
    execute_non_query("Insert into dbo.Coins (Symbol, PairSymbol) Values (?, ?)", [(symbol, pair_symbol)])
    df = execute_query("select CoinID from dbo.Coins where PairSymbol = ?", (pair_symbol,))
    return int(df.iloc[0]["CoinID"])


def get_last_opentime(coin_id: int):
    df = execute_query("select max(OpenTime) as last_open_time from dbo.PriceHistory where CoinID = ?", (coin_id,))
    return df.iloc[0]["last_open_time"] if df is not None and df.iloc[0]["last_open_time"] is not None else None


def save_price_history(coin_id: int, df: pd.DataFrame) -> int:
    sql = """
        INSERT INTO dbo.PriceHistory (CoinID, OpenTime, CloseTime, OpenPrice, HighPrice, LowPrice, ClosePrice, Volume, QuoteAssetVolume, NumberOfTrades, TakerBuyBaseVolume, TakerBuyQuoteVolume) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

    rows = [(coin_id, r.open_time, r.close_time, float(r.open), float(r.high), float(r.low), float(r.close), float(r.volume), float(r.quote_asset_volume), int(r.number_of_trades), float(r.taker_buy_base_asset_volume), float(r.taker_buy_quote_asset_volume))
        for _, r in df.iterrows()]

    inserted = 0
    for i in range(0, len(rows), 500):
        try:
            execute_non_query(sql, rows[i:i+500])
            inserted += len(rows[i:i+500])
        except Exception as e:
            print(f" X Insert Error: {e}")
    return inserted


def process_price_history(pair_symbol: str):
    print(f" {pair_symbol}")
    coin_id = get_or_create_coin(pair_symbol)
    last_time = get_last_opentime(coin_id)
    start_time = last_time + pd.Timedelta(milliseconds=1) if last_time else DEFAULT_START
    start_ts = int(start_time.timestamp() * 1000)
    end_ts = int(datetime.utcnow().timestamp() * 1000)

    if start_ts > end_ts:
        print(" No New Data ")
        return 0
    
    klines = []
    while start_ts < end_ts:
        data = client.klines(symbol=pair_symbol, interval=INTERVAL, startTime=start_ts, limit=1000)

        if not data:
            break
        klines.extend(data)
        start_ts = data[-1][0] + 1
        time.sleep(0.3)

    if not klines:
        print(" No New Data ")
        return 0
    
    df = pd.DataFrame(klines, columns=["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")

    inserted = save_price_history(coin_id, df)
    print(f" {inserted} row inserted")
    return inserted
    

def save_ticker24h(pair_symbol: str):
    coin_id = get_or_create_coin(pair_symbol)
    stats = client.ticker_24hr(pair_symbol)
    sql = """
        insert into dbo.Ticker24hStats (CoinID, SnapshotTime, OpenPrice, HighPrice, LowPrice, ClosePrice, Volume, QuoteAssetVolume, PriceChange, PriceChangePercent, NumberOfTrades)
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
    
    row = (coin_id, datetime.utcnow(), float(stats['openPrice']), float(stats['highPrice']), float(stats['lowPrice']), float(stats['lastPrice']), float(stats['volume']), float(stats['quoteVolume']), float(stats['priceChange']), float(stats['priceChangePercent']), int(stats['count']))
        
    execute_non_query(sql, [row])
    print(" Ticker24h saved ")


def save_order_book(pair_symbol: str):
    coin_id = get_or_create_coin(pair_symbol)
    order_book = client.book_ticker(pair_symbol)
    sql = """
        insert into dbo.OrderBookSnapshot (CoinID, SnapshotTime, BidPrice, BidQty, AskPrice, AskQty)
        values (?, ?, ?, ?, ?, ?)
        """
    
    row = (coin_id, datetime.utcnow(), float(order_book["bidPrice"]), float(order_book["bidQty"]), float(order_book["askPrice"]), float(order_book["askQty"]))

    execute_non_query(sql, [row])
    print(" OrderBook saved")


def main():
    print("\n===== Binance ETL =====\n")
    
    total = 0
    for i, coin in enumerate(COINS, 1):
        print(f"[{i}/{len(COINS)}] ", end="")
        total += process_price_history(coin)
        save_ticker24h(coin)
        save_order_book(coin)
        time.sleep(1)
    print(f"\nTotal: {total} rows\n")


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"Error occurred: {e}")
        print("Waiting 5 minutes before next run...")
        time.sleep(300)  # 300 saniyə = 5 dəqiqə
