from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
from database import execute_query
from alert import check_all_coins

app = FastAPI(title="Crypto API", version="1.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/")
def root():
    return {"status": "OK", "message": "Crypto API işləyir"}

@app.get("/prices/{symbol}")
def get_prices(symbol: str, limit: int = 50):
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="Limit 1-1000 arasında olmalıdır")
    
    query = """
        SELECT TOP (?) ph.OpenTime, ph.ClosePrice, ph.Volume FROM PriceHistory ph JOIN Coins c ON ph.CoinID = c.CoinID
        WHERE c.Symbol = ?
        ORDER BY ph.OpenTime DESC
    """
    
    df = execute_query(query, params=(limit, symbol))
    
    if df is None:
        raise HTTPException(status_code=500, detail="Database xətası")
    
    if df.empty:
        raise HTTPException(status_code=404, detail=f"{symbol} üçün data tapılmadı")
    
    return {"symbol": symbol, "count": len(df), "data": df.to_dict(orient="records")}


@app.get("/coins")
def get_coins():
    query = "SELECT Symbol FROM Coins ORDER BY Symbol"
    df = execute_query(query)
    
    if df is None:
        raise HTTPException(status_code=500, detail="Database xətası")
    
    if df.empty:
        raise HTTPException(status_code=404, detail="Heç bir coin tapılmadı")
    
    return {"count": len(df), "coins": df['Symbol'].tolist()}


#==========================================
@app.get("/coins/detail")
def coins_detail():
    query = "select Symbol, Name from dbo.Coins order by Name"
    df = execute_query(query)
    
    if df is None:
        raise HTTPException(status_code=500, detail="Database xətası")
    
    if df.empty:
        raise HTTPException(status_code=404, detail="Heç bir coin tapılmadı")

    return {"count": len(df), "coins": df.to_dict(orient="records")}
#============================================


@app.get("/stats/{symbol}")
def get_stats(symbol: str):
    query = """
        SELECT COUNT(*) as total_records, MIN(ph.ClosePrice) as min_price, MAX(ph.ClosePrice) as max_price, AVG(ph.ClosePrice) as avg_price, MIN(ph.OpenTime) as first_date, MAX(ph.OpenTime) as last_date
        FROM PriceHistory ph
        JOIN Coins c ON ph.CoinID = c.CoinID
        WHERE c.Symbol = ?
    """
    
    df = execute_query(query, params=(symbol,))
    
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"{symbol} üçün data tapılmadı")
    
    return {"symbol": symbol, "stats": df.to_dict(orient="records")[0]}


@app.get("/prices/range/{symbol}")
def get_price_range(symbol: str, start_date: str, end_date: str):
    query = """
        SELECT ph.OpenTime, ph.OpenPrice, ph.HighPrice, ph.LowPrice, ph.ClosePrice, ph.Volume FROM PriceHistory ph JOIN Coins c ON ph.CoinID = c.CoinID
        WHERE c.Symbol = ?
        AND ph.OpenTime >= ? AND ph.OpenTime <= ?
        ORDER BY ph.OpenTime ASC
    """
    
    df = execute_query(query, params=(symbol, start_date, end_date))
    
    if df is None:
        raise HTTPException(status_code=500, detail="Database xətası")
    
    if df.empty:
        raise HTTPException(status_code=404, detail="Data tapılmadı")
    
    return {"symbol": symbol, "count": len(df), "data": df.to_dict(orient="records")}


@app.get("/latest/{symbol}")
def get_latest(symbol: str):
    query = """
        SELECT TOP 1 ph.OpenTime, ph.OpenPrice, ph.HighPrice, ph.LowPrice, ph.ClosePrice, ph.Volume, ph.NumberOfTrades
        FROM PriceHistory ph
        JOIN Coins c ON ph.CoinID = c.CoinID
        WHERE c.Symbol = ?
        ORDER BY ph.OpenTime DESC
    """
    
    df = execute_query(query, params=(symbol,))

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"{symbol} üçün data tapılmadı")
    
    return {"symbol": symbol, "latest": df.to_dict(orient="records")[0]}


@app.get("/prices/daily/{symbol}")
def daily_return(symbol: str):
    query = """
        SELECT
        c.Symbol,
        ph.OpenTime,
        ph.ClosePrice,
        LAG(ph.ClosePrice) OVER (PARTITION BY ph.CoinID ORDER BY ph.OpenTime) AS PrevClose,
        (ph.ClosePrice - LAG(ph.ClosePrice) OVER (PARTITION BY ph.CoinID ORDER BY ph.OpenTime)) 
        / LAG(ph.ClosePrice) OVER (PARTITION BY ph.CoinID ORDER BY ph.OpenTime) * 100 AS DailyReturnPct
        FROM dbo.PriceHistory ph
        JOIN dbo.Coins c ON c.CoinID = ph.CoinID
        WHERE c.Symbol = ?
        ORDER BY ph.OpenTime
    """

    df = execute_query(query, params=(symbol,))

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"{symbol} üçün data tapılmadı")

    return {"symbol": symbol, "count": len(df), "data": df.to_dict(orient="records")}


@app.get("/coins/difference/{symbol}")
def coins_vs(symbol: str):
    query = """
        SELECT
        c.Symbol,
        AVG((ph.HighPrice - ph.LowPrice) / ph.OpenPrice * 100) AS AvgVolatility
        FROM dbo.PriceHistory ph
        JOIN dbo.Coins c ON c.CoinID = ph.CoinID
        WHERE c.Symbol = ?
        GROUP BY c.Symbol
    """

    df = execute_query(query, params=(symbol,))

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"{symbol} üçün data tapılmadı")

    return {"symbol": symbol, "avg_volatility": df.to_dict(orient="records")[0]["AvgVolatility"]}


@app.get("/compare")
def compare_coins(symbols: str, days: int = 30):
    symbol_list = [s.strip().upper() for s in symbols.split(',')]
    
    if len(symbol_list) < 2:
        raise HTTPException(status_code=400, detail="Ən azı 2 coin seçin")
    
    results = []
    
    for symbol in symbol_list:
        query = """
            SELECT TOP 1 ph.ClosePrice, ph.OpenTime
            FROM PriceHistory ph
            JOIN Coins c ON ph.CoinID = c.CoinID
            WHERE c.Symbol = ?
            ORDER BY ph.OpenTime DESC
        """
        df = execute_query(query, params=(symbol,))
        
        if df is None or df.empty:
            continue
        
        latest_price = float(df['ClosePrice'].iloc[0])
        
        past_query = f"""
            SELECT TOP 1 ph.ClosePrice
            FROM PriceHistory ph
            JOIN Coins c ON ph.CoinID = c.CoinID
            WHERE c.Symbol = ?
            AND ph.OpenTime <= DATEADD(day, -{days}, (SELECT MAX(OpenTime) FROM PriceHistory))
            ORDER BY ph.OpenTime DESC
        """
        df_past = execute_query(past_query, params=(symbol,))
        
        result = {"symbol": symbol, "current_price": latest_price}
        
        if df_past is not None and not df_past.empty:
            past_price = float(df_past['ClosePrice'].iloc[0])
            change_pct = ((latest_price - past_price) / past_price) * 100
            result["change_pct"] = round(change_pct, 2)
        
        results.append(result)
    
    if not results:
        raise HTTPException(status_code=404, detail="Data tapılmadı")
    
    best = max(results, key=lambda x: x.get('change_pct', -999)) if results else None
    worst = min(results, key=lambda x: x.get('change_pct', 999)) if results else None
    
    return {"days": days, "coins": results, "best": best['symbol'] if best else None, "worst": worst['symbol'] if worst else None}


@app.get("/alert")
def alert():
    try:
        alerts = check_all_coins()
        
        formatted_alerts = []
        for alert in alerts:
            formatted_alerts.append({
                "coin": alert['CoinSymbol'],
                "changePercent": f"{alert['ChangePercent']:+.2f}%",
                "currentPrice": f"${alert['CurrentPrice']:.6f}",
                "referencePrice": f"${alert['ReferencePrice']:.6f}",
                "alertDate": str(alert['AlertDate']),
                "alertType": alert['AlertType']})
        
        return {"success": True,  "totalAlerts": len(alerts),  "alerts": formatted_alerts,
            "message": f"{len(alerts)} anomaly tapıldı" if alerts else "Anomaly tapılmadı"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)