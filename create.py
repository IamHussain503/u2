import os

# Define the 12 new strategy file paths and their skeleton code
strategies = {
    "strategies/multi_ema_stochastic.py": """from ta.trend import EMAIndicator
from ta.momentum import StochasticOscillator

class MultiEMAStochasticStrategy:
    def generate_signal(self, df):
        df = df.copy()
        # EMA Trend
        df['ema_short'] = EMAIndicator(df['close'], window=20).ema_indicator()
        df['ema_long']  = EMAIndicator(df['close'], window=50).ema_indicator()
        # Stochastic Oscillator
        stoch = StochasticOscillator(df['high'], df['low'], df['close'], window=14, smooth_window=3)
        df['stoch'] = stoch.stoch()
        
        # Entry: EMAs bullish and Stoch oversold
        df['signal'] = 0
        df.loc[(df['ema_short'] > df['ema_long']) & (df['stoch'] < 20), 'signal'] = 1
        df.loc[(df['ema_short'] < df['ema_long']) & (df['stoch'] > 80), 'signal'] = -1
        
        # Exit: EMA cross or Stoch mid-cross
        df['exit_signal'] = 0
        df.loc[(df['signal'].shift(1) == 1) & (df['stoch'] > 50), 'exit_signal'] = 1
        df.loc[(df['signal'].shift(1) == -1) & (df['stoch'] < 50), 'exit_signal'] = -1
        
        return df
""",
    "strategies/vwap_reversion.py": """from ta.volume import VolumeWeightedAveragePrice

class VWAPReversionStrategy:
    def generate_signal(self, df):
        df = df.copy()
        vwap = VolumeWeightedAveragePrice(df['high'], df['low'], df['close'], df['volume'], window=14)
        df['vwap'] = vwap.volume_weighted_average_price()
        df['deviation'] = (df['close'] - df['vwap']).abs()
        
        # Entry: price deviates > 1 ATR from VWAP
        df['atr'] = df['deviation'].rolling(14).mean()
        df['signal'] = 0
        df.loc[df['close'] > df['vwap'] + df['atr'], 'signal'] = -1
        df.loc[df['close'] < df['vwap'] - df['atr'], 'signal'] = 1
        
        df['exit_signal'] = 0
        df.loc[(df['signal'].shift(1) == 1) & (df['close'] >= df['vwap']), 'exit_signal'] = 1
        df.loc[(df['signal'].shift(1) == -1) & (df['close'] <= df['vwap']), 'exit_signal'] = -1
        
        return df
""",
    "strategies/ichimoku_breakout.py": """from ta.trend import IchimokuIndicator

class IchimokuBreakoutStrategy:
    def generate_signal(self, df):
        df = df.copy()
        ich = IchimokuIndicator(high=df['high'], low=df['low'], window1=9, window2=26, window3=52)
        df['conversion'] = ich.ichimoku_conversion_line()
        df['base']       = ich.ichimoku_base_line()
        
        # Entry: price above cloud and conversion > base
        df['signal'] = 0
        df.loc[(df['close'] > ich.ichimoku_a()) & (df['conversion'] > df['base']), 'signal'] = 1
        df.loc[(df['close'] < ich.ichimoku_b()) & (df['conversion'] < df['base']), 'signal'] = -1
        
        df['exit_signal'] = 0
        df.loc[(df['signal'].shift(1) == 1) & (df['conversion'] < df['base']), 'exit_signal'] = 1
        df.loc[(df['signal'].shift(1) == -1) & (df['conversion'] > df['base']), 'exit_signal'] = -1
        
        return df
""",
    "strategies/supertrend_rsi.py": """from ta.trend import Supertrend
from ta.momentum import RSIIndicator

class SupertrendRSIStrategy:
    def generate_signal(self, df):
        df = df.copy()
        st = Supertrend(high=df['high'], low=df['low'], close=df['close'], window=10, multiplier=3)
        df['supertrend'] = st.supertrend()
        df['rsi'] = RSIIndicator(df['close'], window=14).rsi()
        
        df['signal'] = 0
        df.loc[(df['supertrend'] == True) & (df['rsi'] < 60), 'signal'] = 1
        df.loc[(df['supertrend'] == False) & (df['rsi'] > 40), 'signal'] = -1
        
        df['exit_signal'] = 0
        df.loc[(df['signal'].shift(1) == 1) & (df['rsi'] > 70), 'exit_signal'] = 1
        df.loc[(df['signal'].shift(1) == -1) & (df['rsi'] < 30), 'exit_signal'] = -1
        
        return df
""",
    "strategies/macd_volume_surge.py": """from ta.trend import MACD
from ta.volume import VolumeWeightedAveragePrice

class MACDVolumeSurgeStrategy:
    def generate_signal(self, df):
        df = df.copy()
        macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
        df['macd_hist'] = macd.macd_diff()
        df['vwap'] = VolumeWeightedAveragePrice(df['high'], df['low'], df['close'], df['volume'], window=20).volume_weighted_average_price()
        
        df['signal'] = 0
        df.loc[(df['macd_hist'] > 0) & (df['volume'] > df['volume'].rolling(20).mean()*2), 'signal'] = 1
        df.loc[(df['macd_hist'] < 0) & (df['volume'] > df['volume'].rolling(20).mean()*2), 'signal'] = -1
        
        df['exit_signal'] = 0
        df.loc[(df['signal'].shift(1) == 1) & (df['macd_hist'] < 0), 'exit_signal'] = 1
        df.loc[(df['signal'].shift(1) == -1) & (df['macd_hist'] > 0), 'exit_signal'] = -1
        
        return df
""",
    "strategies/keltner_cci_mean_reversion.py": """from ta.trend import KeltnerChannel
from ta.trend import CCIIndicator

class KeltnerCCIMeanReversionStrategy:
    def generate_signal(self, df):
        df = df.copy()
        kc = KeltnerChannel(high=df['high'], low=df['low'], close=df['close'], window=20, window_atr=10)
        df['kc_lower'] = kc.keltner_channel_lband()
        df['kc_upper'] = kc.keltner_channel_hband()
        df['cci'] = CCIIndicator(high=df['high'], low=df['low'], close=df['close'], window=20).cci()
        
        df['signal'] = 0
        df.loc[(df['close'] < df['kc_lower']) & (df['cci'] < -100), 'signal'] = 1
        df.loc[(df['close'] > df['kc_upper']) & (df['cci'] > 100), 'signal'] = -1
        
        df['exit_signal'] = 0
        df.loc[(df['signal'].shift(1) == 1) & (df['cci'] > 0), 'exit_signal'] = 1
        df.loc[(df['signal'].shift(1) == -1) & (df['cci'] < 0), 'exit_signal'] = -1
        
        return df
""",
    "strategies/turtle_three_screen.py": """from ta.volatility import DonchianChannel

class TurtleThreeScreenStrategy:
    def generate_signal(self, df):
        df = df.copy()
        dc20 = DonchianChannel(high=df['high'], low=df['low'], window=20)
        dc55 = DonchianChannel(high=df['high'], low=df['low'], window=55)
        df['breakout20'] = df['close'] > dc20.donchian_channel_hband()
        df['trend55'] = df['close'] > dc55.donchian_channel_hband()
        
        df['signal'] = 0
        df.loc[(df['breakout20']) & (df['trend55']), 'signal'] = 1
        df.loc[(~df['breakout20']) & (~df['trend55']), 'signal'] = -1
        
        df['exit_signal'] = 0
        df.loc[(df['signal'].shift(1) == 1) & (~df['trend55']), 'exit_signal'] = 1
        df.loc[(df['signal'].shift(1) == -1) & (df['trend55']), 'exit_signal'] = -1
        
        return df
""",
    "strategies/pivot_point_breakout.py": """# Requires pivot point calculation library or custom implementation
import pandas as pd

def calculate_pivots(df):
    # Basic pivot point calculation
    df['pp'] = (df['high'] + df['low'] + df['close']) / 3
    df['r1'] = 2 * df['pp'] - df['low']
    df['s1'] = 2 * df['pp'] - df['high']
    return df

class PivotPointBreakoutStrategy:
    def generate_signal(self, df):
        df = calculate_pivots(df.copy())
        df['signal'] = 0
        df.loc[df['close'] > df['r1'], 'signal'] = 1
        df.loc[df['close'] < df['s1'], 'signal'] = -1
        
        df['exit_signal'] = 0
        df.loc[(df['signal'].shift(1) == 1) & (df['close'] < df['pp']), 'exit_signal'] = 1
        df.loc[(df['signal'].shift(1) == -1) & (df['close'] > df['pp']), 'exit_signal'] = -1
        
        return df
""",
    "strategies/adx_bollinger_squeeze.py": """from ta.volatility import BollingerBands
from ta.trend import ADXIndicator

class ADXBollingerSqueezeStrategy:
    def generate_signal(self, df):
        df = df.copy()
        bb = BollingerBands(df['close'], window=20, window_dev=2)
        df['bandwidth'] = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg()
        df['adx'] = ADXIndicator(df['high'], df['low'], df['close'], window=14).adx()
        
        df['signal'] = 0
        df.loc[(df['bandwidth'] < 0.05) & (df['adx'] > 25), 'signal'] = 1
        df.loc[(df['bandwidth'] < 0.05) & (df['adx'] > 25), 'signal'] = -1  # adapt for short if needed
        
        df['exit_signal'] = 0
        df.loc[df['adx'] < 20, 'exit_signal'] = df['signal'].shift(1)
        
        return df
""",
    "strategies/rsi_ma_envelope.py": """from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator

class RSIMovingAverageEnvelopeStrategy:
    def generate_signal(self, df):
        df = df.copy()
        df['sma'] = SMAIndicator(df['close'], window=20).sma_indicator()
        df['upper_env'] = df['sma'] * 1.05
        df['lower_env'] = df['sma'] * 0.95
        df['rsi'] = RSIIndicator(df['close'], window=14).rsi()
        
        df['signal'] = 0
        df.loc[(df['close'] > df['upper_env']) & (df['rsi'] < 50), 'signal'] = -1
        df.loc[(df['close'] < df['lower_env']) & (df['rsi'] > 50), 'signal'] = 1
        
        df['exit_signal'] = 0
        df.loc[(df['signal'].shift(1) == 1) & (df['close'] >= df['sma']), 'exit_signal'] = 1
        df.loc[(df['signal'].shift(1) == -1) & (df['close'] <= df['sma']), 'exit_signal'] = -1
        
        return df
""",
    "strategies/ml_signal.py": """# Placeholder for a machine-learning based signal
import pandas as pd

class MachineLearningSignalStrategy:
    def generate_signal(self, df):
        df = df.copy()
        # TODO: load your trained ML model and generate predictions
        df['signal'] = 0
        # Example: df['signal'] = model.predict(df[features])
        df['exit_signal'] = 0
        return df
""",
    "strategies/pairs_trading.py": """import pandas as pd

class PairsTradingStrategy:
    def generate_signal(self, df):
        df = df.copy()
        # TODO: implement cointegration test & z-score of spread
        df['signal'] = 0
        df['exit_signal'] = 0
        return df
"""
}

def main():
    # Create strategy files
    for path, content in strategies.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    print("Created the following strategy files:")
    for p in strategies:
        print(" -", p)
    
    # Print instructions for updating strategy_manager.py
    print("\nAdd these lines to your `strategies/strategy_manager.py`:\n")
    print("    # Auto-generated strategies")
    for filename in strategies:
        class_name = os.path.splitext(os.path.basename(filename))[0]
        # Convert file name to Strategy class names and loader names
        loader_name = f"load_{class_name}"
        strategy_name = class_name.replace('_', ' ').title()
        print(f'        "{strategy_name}": self.{loader_name}(),')
    print("\nAnd append these loader methods to the StrategyManager class:\n")
    for filename in strategies:
        class_name = os.path.splitext(os.path.basename(filename))[0]
        loader_name = f"load_{class_name}"
        class_title = class_name.replace('_', ' ').title().replace(' ', '')
        print(f"    def {loader_name}(self):")
        print(f"        from strategies.{class_name} import {class_title}Strategy")
        print(f"        return {class_title}Strategy()")
        print()

if __name__ == "__main__":
    main()

