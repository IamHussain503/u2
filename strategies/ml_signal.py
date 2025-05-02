# strategies/ml_signal.py

import os
import yaml
import pickle
import pandas as pd
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange, BollingerBands

class MachineLearningSignalStrategy:
    def __init__(self):
        with open("config.yaml", "r") as f:
            cfg = yaml.safe_load(f)
        tf = cfg["timeframe"]
        model_dir = cfg.get("model_dir", "models")
        model_path = os.path.join(model_dir, f"model_{tf}.pkl")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"ML model for {tf} not found: {model_path}")
        with open(model_path, "rb") as f:
            self.model = pickle.load(f)
        self.features = [
            "ema_spread","rsi","atr","macd_hist",
            "vol_ratio","lag_return","bb_bandwidth"
        ]

    def generate_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["ema_spread"] = df["close"].ewm(span=9).mean() - df["close"].ewm(span=21).mean()
        df["rsi"]        = RSIIndicator(df["close"], window=14).rsi()
        df["atr"]        = AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range()
        macd            = MACD(df["close"], window_slow=26, window_fast=12, window_sign=9)
        df["macd_hist"] = macd.macd_diff()
        df["vol_ratio"] = df["volume"] / df["volume"].rolling(10).mean()
        df["lag_return"]= df["close"].pct_change()
        bb              = BollingerBands(df["close"], window=20, window_dev=2)
        df["bb_bandwidth"] = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg()

        df = df.dropna(subset=self.features)
        X = df[self.features]
        preds = self.model.predict(X)
        df["signal"] = pd.Series(preds, index=X.index).map({1:1, 0:-1})

        # **NEW EXIT**: when the next row’s signal ≠ current, exit
        df["exit_signal"] = df["signal"].shift(-1).fillna(0).astype(int)
        df.loc[df["exit_signal"] == df["signal"], "exit_signal"] = 0
        return df
