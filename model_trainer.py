import os
import threading
import time
import yaml
import pandas as pd
import pickle
import xgboost as xgb
from datetime import datetime, timedelta
from exchange.binance_connector import BinanceFuturesConnector
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange, BollingerBands
from sklearn.model_selection import train_test_split

class ModelTrainer:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)

        self.symbol     = cfg["symbol"]
        self.timeframes = ["5m", "15m", "1h", "4h"]
        self.tf_limits  = {
            "5m": 100000,
            "15m": 100000,
            "1h": 10000,
            "4h": 500,
        }
        self.model_dir  = cfg.get("model_dir", "models")
        os.makedirs(self.model_dir, exist_ok=True)
        self.connector  = BinanceFuturesConnector()

    def fetch_data(self, tf):
        limit = self.tf_limits.get(tf, 500)
        df = self.connector.fetch_ohlcv(
            symbol=self.symbol,
            timeframe=tf,
            limit=limit
        )
        df.columns = ["timestamp","open","high","low","close","volume"]
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df

    def prepare_features(self, df):
        df["ema_spread"] = df["close"].ewm(span=9).mean() - df["close"].ewm(span=21).mean()
        df["rsi"]        = RSIIndicator(df["close"], window=14).rsi()
        df["atr"]        = AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range()
        macd            = MACD(df["close"], window_slow=26, window_fast=12, window_sign=9)
        df["macd_hist"] = macd.macd_diff()
        df["vol_ratio"] = df["volume"] / df["volume"].rolling(10).mean()
        df["lag_return"]= df["close"].pct_change()
        bb              = BollingerBands(df["close"], window=20, window_dev=2)
        df["bb_bandwidth"] = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg()

        feature_cols = ["ema_spread","rsi","atr","macd_hist","vol_ratio","lag_return","bb_bandwidth"]
        df = df.dropna(subset=feature_cols + ["close"])
        X = df[feature_cols]
        df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
        return X.iloc[:-1], df["target"].iloc[:-1]

    def train_timeframe(self, tf):
        df = self.fetch_data(tf)
        X, y = self.prepare_features(df)
        if len(y) < 50:
            print(f"[SKIP] Not enough data for {tf}: {len(y)} rows")
            return
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            use_label_encoder=False,
            eval_metric="logloss"
        )
        model.fit(
            X_train, y_train,
            # eval_set=[(X_test, y_test)],
            # early_stopping_rounds=10,
            verbose=False
        )
        path = os.path.join(self.model_dir, f"model_{tf}.pkl")
        with open(path, "wb") as f:
            pickle.dump(model, f)
        print(f"[SAVE] Model for {tf} → {path}")

    def run_all(self):
        for tf in self.timeframes:
            try:
                self.train_timeframe(tf)
            except Exception as e:
                print(f"[ERROR] {tf}: {e}")

    def schedule_hourly(self):
        self.run_all()
        while True:
            now = datetime.now()
            next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            time.sleep((next_hour - now).total_seconds())
            self.run_all()

def start_background_training():
    trainer = ModelTrainer()
    # **run first training pass now, in main thread**
    trainer.run_all()
    # then schedule the hourly retrains in a daemon thread
    t = threading.Thread(target=trainer.schedule_hourly, daemon=True)
    t.start()

if __name__ == "__main__":
    start_background_training()
    # keep process alive if run standalone
    while True:
        time.sleep(3600)