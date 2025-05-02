# utils/config.py

from pydantic import BaseModel, Field

class Config(BaseModel):
    symbol:            str
    timeframe:         str   = Field(..., pattern=r"^(5m|15m|1h|2h|4h)$")
    limit:             int   = 500
    poll_interval:     int   = 60
    initial_capital:   float = 1000.0
    leverage:          int   = 20
    risk_per_trade:    float = 1
    atr_window:        int   = 14
    atr_multiplier:    float = 1.5
    tp_multiplier:     float = 3.0
    trailing_atr_multiplier: float = 1.5
    adx_window:        int   = 14
    adx_threshold:     float = 25.0
    ma_period:         int   = 200
    max_holding_bars:  int   = 48
    taker_fee:         float = 0.0004
    paper_mode:        bool  = True
    trade_log_file:    str   = "data/trades.csv"



# # Then in your main startup:
# from utils.config import Config
# cfg = Config.parse_file("config.yaml")
