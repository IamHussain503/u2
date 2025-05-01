import os

# Create model_trainer.py
model_trainer_code = """\
import os
import threading
import time
import yaml
import pandas as pd
import joblib
import xgboost as xgb
from datetime import datetime, timedelta
from exchange.binance_connector import BinanceFuturesConnector
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange, BollingerBands
from sklearn.model_selection import train_test_split

class ModelTrainer:
    def __init__(self, config_path="config.yaml"):
        # load settings
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)

        self.symbol       = cfg["symbol"]
        self.timeframes   = ["5m", "15m", "1h", "4h"]
        self.limit        = cfg.get("limit", 1000)
        self.model_dir    = cfg.get("model_dir", "models")
        os.makedirs(self.model_dir, exist_ok=True)

        self.connector    = BinanceFuturesConnector()

    def fetch_data(self, timeframe):
        df = self.connector.fetch_ohlcv(
            symbol=self.symbol,
            timeframe=timeframe,
            limit=self.limit
        )
        df.columns = ["timestamp","open","high","low","close","volume"]
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df

    def prepare_features(self, df):
        # EMA spread
        df["ema9"]  = df["close"].ewm(span=9).mean()
        df["ema21"] = df["close"].ewm(span=21).mean()
        df["ema_spread"] = df["ema9"] - df["ema21"]
        # RSI
        df["rsi"]  = RSIIndicator(df["close"], window=14).rsi()
        # ATR
        df["atr"]  = AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range()
        # MACD hist
        macd = MACD(df["close"], window_slow=26, window_fast=12, window_sign=9)
        df["macd_hist"] = macd.macd_diff()
        # Volume ratio
        df["vol_ma10"] = df["volume"].rolling(10).mean()
        df["vol_ratio"] = df["volume"] / df["vol_ma10"]
        # Lagged return
        df["lag_return"] = df["close"].pct_change()
        # Bollinger bandwidth
        bb = BollingerBands(df["close"], window=20, window_dev=2)
        df["bb_bandwidth"] = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg()

        # drop NaNs
        feature_cols = ["ema_spread", "rsi", "atr", "macd_hist", 
                        "vol_ratio", "lag_return", "bb_bandwidth"]
        df = df.dropna(subset=feature_cols + ["close"])
        X = df[feature_cols]
        # target: next-bar up/down
        df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
        y = df["target"].iloc[:-1]
        X = X.iloc[:-1]
        return X, y

    def train_timeframe(self, tf):
        print(f"[TRAIN] Fetching data for {tf}")
        df = self.fetch_data(tf)
        X, y = self.prepare_features(df)
        if len(y) < 50:
            print(f"[SKIP] Not enough data for {tf}")
            return
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        model = xgb.XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.1, use_label_encoder=False, eval_metric='logloss')
        model.fit(
            X_train, y_train, 
            eval_set=[(X_test, y_test)],
            early_stopping_rounds=10,
            verbose=False
        )
        path = os.path.join(self.model_dir, f"model_{tf}.pkl")
        joblib.dump(model, path)
        print(f"[SAVE] Model saved to {path}")

    def run_all(self):
        for tf in self.timeframes:
            try:
                self.train_timeframe(tf)
            except Exception as e:
                print(f"[ERROR] {tf}: {e}")

    def schedule_hourly(self):
        # run immediately on start
        self.run_all()
        while True:
            now = datetime.now()
            # next top of hour
            next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            sleep_secs = (next_hour - now).total_seconds()
            time.sleep(sleep_secs)
            self.run_all()

if __name__ == "__main__":
    trainer = ModelTrainer()
    thread  = threading.Thread(target=trainer.schedule_hourly, daemon=True)
    thread.start()
    # keep main thread alive
    while True:
        time.sleep(3600)
"""

with open("model_trainer.py", "w", encoding="utf-8") as f:
    f.write(model_trainer_code)

# Create updated ml_signal.py
ml_signal_code = """\
# strategies/ml_signal.py

import yaml
import joblib
import pandas as pd
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange, BollingerBands

class MachineLearningSignalStrategy:
    def __init__(self):
        # load config
        with open("config.yaml", "r") as f:
            cfg = yaml.safe_load(f)
        self.timeframe = cfg["timeframe"]
        model_dir = cfg.get("model_dir", "models")
        model_path = f"{model_dir}/model_{self.timeframe}.pkl"
        # load model
        self.model = joblib.load(model_path)
        # define feature columns
        self.features = [
            "ema_spread", "rsi", "atr", "macd_hist",
            "vol_ratio", "lag_return", "bb_bandwidth"
        ]

    def generate_signal(self, df):
        df = df.copy()
        # compute features
        df["ema9"]  = df["close"].ewm(span=9).mean()
        df["ema21"] = df["close"].ewm(span=21).mean()
        df["ema_spread"] = df["ema9"] - df["ema21"]
        df["rsi"]  = RSIIndicator(df["close"], window=14).rsi()
        df["atr"]  = AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range()
        macd = MACD(df["close"], window_slow=26, window_fast=12, window_sign=9)
        df["macd_hist"] = macd.macd_diff()
        df["vol_ma10"] = df["volume"].rolling(10).mean()
        df["vol_ratio"] = df["volume"] / df["vol_ma10"]
        df["lag_return"] = df["close"].pct_change()
        bb = BollingerBands(df["close"], window=20, window_dev=2)
        df["bb_bandwidth"] = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg()

        # drop NaNs and select features
        df = df.dropna(subset=self.features)
        X = df[self.features]

        # predict next-bar direction
        preds = self.model.predict(X)
        # map {1: up, 0: down} → {1, -1}
        df["signal"] = pd.Series(preds, index=X.index).map({1: 1, 0: -1})

        df["exit_signal"] = 0
        return df
"""

os.makedirs("strategies", exist_ok=True)
with open("strategies/ml_signal.py", "w", encoding="utf-8") as f:
    f.write(ml_signal_code)

print("Created model_trainer.py and updated strategies/ml_signal.py")
