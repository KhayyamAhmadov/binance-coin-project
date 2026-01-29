# BinanceDB Database Schema

## dbo.Coins
| Column       | Data Type       | Constraints                        | Description                |
|--------------|----------------|-----------------------------------|----------------------------|
| CoinID       | INT            | PRIMARY KEY, IDENTITY(1,1)        | Unique coin ID            |
| Symbol       | NVARCHAR(10)   | NOT NULL, UNIQUE                   | Coin symbol (e.g., BTC)  |
| PairSymbol   | NVARCHAR(20)   | NOT NULL, UNIQUE                   | Trading pair (e.g., BTCUSDT) |
| CreatedDate  | DATETIME2      | DEFAULT SYSDATETIME()              | Record creation timestamp |

---

## dbo.PriceHistory
| Column                  | Data Type       | Constraints                               | Description                          |
|-------------------------|----------------|------------------------------------------|--------------------------------------|
| PriceID                 | BIGINT         | PRIMARY KEY, IDENTITY(1,1)               | Unique price history ID              |
| CoinID                  | INT            | FOREIGN KEY → dbo.Coins(CoinID), NOT NULL | Coin ID                              |
| OpenTime                | DATETIME2      | NOT NULL                                  | Candle open time                     |
| CloseTime               | DATETIME2      | NOT NULL                                  | Candle close time                    |
| OpenPrice               | DECIMAL(18,8)  | NOT NULL                                  | Opening price                        |
| HighPrice               | DECIMAL(18,8)  | NOT NULL                                  | Highest price                         |
| LowPrice                | DECIMAL(18,8)  | NOT NULL                                  | Lowest price                          |
| ClosePrice              | DECIMAL(18,8)  | NOT NULL                                  | Closing price                         |
| Volume                  | DECIMAL(30,8)  | NOT NULL                                  | Trading volume                        |
| QuoteAssetVolume        | DECIMAL(30,8)  | NOT NULL                                  | Quote asset volume                     |
| NumberOfTrades          | INT            | NOT NULL                                  | Number of trades                       |
| TakerBuyBaseVolume      | DECIMAL(30,8)  | NOT NULL                                  | Taker buy base asset volume            |
| TakerBuyQuoteVolume     | DECIMAL(30,8)  | NOT NULL                                  | Taker buy quote asset volume           |
| InsertedDate            | DATETIME2      | DEFAULT SYSDATETIME()                     | Record insertion timestamp             |
| **Unique Constraint**   |                | CoinID + OpenTime                          | Prevent duplicate entries             |

---

## dbo.Ticker24hStats
| Column             | Data Type      | Constraints                           | Description                          |
|-------------------|---------------|--------------------------------------|--------------------------------------|
| StatID            | BIGINT        | PRIMARY KEY, IDENTITY(1,1)           | Unique stat ID                        |
| CoinID            | INT           | FOREIGN KEY → dbo.Coins(CoinID), NOT NULL | Coin ID                              |
| SnapshotTime      | DATETIME2     | NOT NULL                              | Snapshot time                         |
| OpenPrice         | DECIMAL(18,8) | NOT NULL                              | Opening price                          |
| HighPrice         | DECIMAL(18,8) | NOT NULL                              | Highest price                          |
| LowPrice          | DECIMAL(18,8) | NOT NULL                              | Lowest price                           |
| ClosePrice        | DECIMAL(18,8) | NOT NULL                              | Closing price                          |
| Volume            | DECIMAL(30,8) | NOT NULL                              | Trading volume                         |
| QuoteAssetVolume  | DECIMAL(30,8) | NOT NULL                              | Quote asset volume                     |
| PriceChange       | DECIMAL(18,8) | NULL                                   | Price change                           |
| PriceChangePercent| DECIMAL(8,2)  | NULL                                   | Price change in percent                |
| NumberOfTrades    | INT           | NULL                                   | Number of trades                       |
| InsertedDate      | DATETIME2     | DEFAULT SYSDATETIME()                 | Record insertion timestamp             |

---

## dbo.OrderBookSnapshot
| Column        | Data Type      | Constraints                           | Description                          |
|---------------|---------------|--------------------------------------|--------------------------------------|
| SnapshotID    | BIGINT        | PRIMARY KEY, IDENTITY(1,1)           | Unique snapshot ID                     |
| CoinID        | INT           | FOREIGN KEY → dbo.Coins(CoinID), NOT NULL | Coin ID                              |
| SnapshotTime  | DATETIME2     | NOT NULL                              | Snapshot time                         |
| BidPrice      | DECIMAL(18,8) | NOT NULL                              | Highest bid price                     |
| BidQty        | DECIMAL(30,8) | NOT NULL                              | Bid quantity                           |
| AskPrice      | DECIMAL(18,8) | NOT NULL                              | Lowest ask price                       |
| AskQty        | DECIMAL(30,8) | NOT NULL                              | Ask quantity                           |
| InsertedDate  | DATETIME2     | DEFAULT SYSDATETIME()                 | Record insertion timestamp             |
