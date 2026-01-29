CREATE DATABASE BinanceDB;
GO

USE BinanceDB;
GO

CREATE TABLE dbo.Coins (
    CoinID INT IDENTITY(1,1) PRIMARY KEY,
    Symbol NVARCHAR(10) NOT NULL UNIQUE,
    PairSymbol NVARCHAR(20) NOT NULL UNIQUE,
    Name NVARCHAR(50),
    CreatedDate DATETIME2 DEFAULT SYSDATETIME()
);
GO

CREATE TABLE dbo.PriceHistory (
    PriceID BIGINT IDENTITY(1,1) PRIMARY KEY,
    CoinID INT NOT NULL,
    OpenTime DATETIME2 NOT NULL,
    CloseTime DATETIME2 NOT NULL,
    OpenPrice DECIMAL(18,8) NOT NULL,
    HighPrice DECIMAL(18,8) NOT NULL,
    LowPrice DECIMAL(18,8) NOT NULL,
    ClosePrice DECIMAL(18,8) NOT NULL,
    Volume DECIMAL(30,8) NOT NULL,
    QuoteAssetVolume DECIMAL(30,8) NOT NULL,
    NumberOfTrades INT NOT NULL,
    TakerBuyBaseVolume DECIMAL(30,8) NOT NULL,
    TakerBuyQuoteVolume DECIMAL(30,8) NOT NULL,
    InsertedDate DATETIME2 DEFAULT SYSDATETIME(),
    CONSTRAINT FK_PriceHistory_Coins FOREIGN KEY (CoinID) REFERENCES dbo.Coins(CoinID),
    CONSTRAINT UQ_Coin_OpenTime UNIQUE (CoinID, OpenTime)
);
GO

CREATE TABLE dbo.Ticker24hStats (
    StatID BIGINT IDENTITY(1,1) PRIMARY KEY,
    CoinID INT NOT NULL,
    SnapshotTime DATETIME2 NOT NULL,           -- snapshot zamanı
    OpenPrice DECIMAL(18,8) NOT NULL,
    HighPrice DECIMAL(18,8) NOT NULL,
    LowPrice DECIMAL(18,8) NOT NULL,
    ClosePrice DECIMAL(18,8) NOT NULL,
    Volume DECIMAL(30,8) NOT NULL,
    QuoteAssetVolume DECIMAL(30,8) NOT NULL,
    PriceChange DECIMAL(18,8) NULL,
    PriceChangePercent DECIMAL(8,2) NULL,
    NumberOfTrades INT NULL,
    InsertedDate DATETIME2 DEFAULT SYSDATETIME(),
    CONSTRAINT FK_Ticker24hStats_Coins FOREIGN KEY (CoinID) REFERENCES dbo.Coins(CoinID)
);
GO

CREATE TABLE dbo.OrderBookSnapshot (
    SnapshotID BIGINT IDENTITY(1,1) PRIMARY KEY,
    CoinID INT NOT NULL,
    SnapshotTime DATETIME2 NOT NULL,
    BidPrice DECIMAL(18,8) NOT NULL,
    BidQty DECIMAL(30,8) NOT NULL,
    AskPrice DECIMAL(18,8) NOT NULL,
    AskQty DECIMAL(30,8) NOT NULL,
    InsertedDate DATETIME2 DEFAULT SYSDATETIME(),
    CONSTRAINT FK_OrderBook_Coins FOREIGN KEY (CoinID) REFERENCES dbo.Coins(CoinID)
);
GO

CREATE TABLE dbo.AnomalyAlerts (
    AlertID INT IDENTITY(1,1) PRIMARY KEY,
    CoinID INT NOT NULL,
    AlertTime DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    AlertDate DATE NOT NULL,
    CurrentPrice DECIMAL(18,8) NOT NULL,
    ReferencePrice DECIMAL(18,8) NOT NULL,
    ChangePercent DECIMAL(10,4) NOT NULL,
    AlertType NVARCHAR(30) NOT NULL,
    CONSTRAINT FK_AnomalyAlerts_Coins FOREIGN KEY (CoinID) REFERENCES dbo.Coins(CoinID)
);
GO

CREATE INDEX IX_PriceHistory_CoinID ON dbo.PriceHistory (CoinID);
CREATE INDEX IX_PriceHistory_OpenTime ON dbo.PriceHistory (OpenTime);
CREATE INDEX IX_Ticker24hStats_CoinID ON dbo.Ticker24hStats (CoinID);
CREATE INDEX IX_Ticker24hStats_SnapshotTime ON dbo.Ticker24hStats (SnapshotTime);
CREATE INDEX IX_OrderBookSnapshot_CoinID ON dbo.OrderBookSnapshot (CoinID);
CREATE INDEX IX_OrderBookSnapshot_SnapshotTime ON dbo.OrderBookSnapshot (SnapshotTime);
CREATE UNIQUE INDEX UQ_AnomalyAlerts_CoinID_AlertDate ON dbo.AnomalyAlerts (CoinID, AlertDate);
GO