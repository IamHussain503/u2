# strategies/strategy_manager.py

class StrategyManager:
    def __init__(self):
        # map human-readable names to instantiated strategy objects
        self.strategy_map = {
            "EMA Crossover":              self.load_ema_crossover(),
            "RSI Divergence":             self.load_rsi_divergence(),
            "Bollinger Breakout":         self.load_bollinger_breakout(),
            "MACD Crossover":             self.load_macd_crossover(),
            "SMA Crossover":              self.load_sma_crossover(),
            "RSI+MACD Combo":             self.load_rsi_macd_combo(),
            "Donchian Breakout":          self.load_donchian_breakout(),
            "BB+RSI Combo":               self.load_bb_rsi_combo(),
            "MultiEMA Stochastic":        self.load_multi_ema_stochastic(),
            "VWAP Reversion":             self.load_vwap_reversion(),
            "Ichimoku Breakout":          self.load_ichimoku_breakout(),
            "Supertrend RSI":             self.load_supertrend_rsi(),
            "MACD Volume Surge":          self.load_macd_volume_surge(),
            "Keltner CCI Mean Reversion": self.load_keltner_cci_mean_reversion(),
            "Turtle Three Screen":        self.load_turtle_three_screen(),
            "Pivot Point Breakout":       self.load_pivot_point_breakout(),
            "ADX Bollinger Squeeze":      self.load_adx_bollinger_squeeze(),
            "RSI MA Envelope":            self.load_rsi_ma_envelope(),
            "Machine Learning Signal":    self.load_machine_learning_signal(),
            "Pairs Trading":              self.load_pairs_trading(),
        }

    def get_strategy(self, name: str):
        """
        Return an instance of the requested strategy, or None if not found.
        """
        return self.strategy_map.get(name)

    # ───────────── existing loaders ─────────────

    def load_ema_crossover(self):
        from strategies.ema_crossover import EMACrossoverStrategy
        return EMACrossoverStrategy()

    def load_rsi_divergence(self):
        from strategies.rsi_divergence import RSIDivergenceStrategy
        return RSIDivergenceStrategy()

    def load_bollinger_breakout(self):
        from strategies.bollinger_breakout import BollingerBreakoutStrategy
        return BollingerBreakoutStrategy()

    def load_macd_crossover(self):
        from strategies.macd_crossover import MACDCrossoverStrategy
        return MACDCrossoverStrategy()

    def load_sma_crossover(self):
        from strategies.sma_crossover import SMACrossoverStrategy
        return SMACrossoverStrategy()

    def load_rsi_macd_combo(self):
        from strategies.rsi_macd_combo import RSIMACDComboStrategy
        return RSIMACDComboStrategy()

    def load_donchian_breakout(self):
        from strategies.donchian_breakout import DonchianBreakoutStrategy
        return DonchianBreakoutStrategy()

    def load_bb_rsi_combo(self):
        from strategies.bb_rsi_combo import BBRSIComboStrategy
        return BBRSIComboStrategy()

    # ───────────── new loader methods ─────────────

    def load_multi_ema_stochastic(self):
        from strategies.multi_ema_stochastic import MultiEMAStochasticStrategy
        return MultiEMAStochasticStrategy()

    def load_vwap_reversion(self):
        from strategies.vwap_reversion import VWAPReversionStrategy
        return VWAPReversionStrategy()

    def load_ichimoku_breakout(self):
        from strategies.ichimoku_breakout import IchimokuBreakoutStrategy
        return IchimokuBreakoutStrategy()

    def load_supertrend_rsi(self):
        from strategies.supertrend_rsi import SupertrendRSIStrategy
        return SupertrendRSIStrategy()

    def load_macd_volume_surge(self):
        from strategies.macd_volume_surge import MACDVolumeSurgeStrategy
        return MACDVolumeSurgeStrategy()

    def load_keltner_cci_mean_reversion(self):
        from strategies.keltner_cci_mean_reversion import KeltnerCCIMeanReversionStrategy
        return KeltnerCCIMeanReversionStrategy()

    def load_turtle_three_screen(self):
        from strategies.turtle_three_screen import TurtleThreeScreenStrategy
        return TurtleThreeScreenStrategy()

    def load_pivot_point_breakout(self):
        from strategies.pivot_point_breakout import PivotPointBreakoutStrategy
        return PivotPointBreakoutStrategy()

    def load_adx_bollinger_squeeze(self):
        from strategies.adx_bollinger_squeeze import ADXBollingerSqueezeStrategy
        return ADXBollingerSqueezeStrategy()

    def load_rsi_ma_envelope(self):
        from strategies.rsi_ma_envelope import RSIMovingAverageEnvelopeStrategy
        return RSIMovingAverageEnvelopeStrategy()

    def load_machine_learning_signal(self):
        from strategies.ml_signal import MachineLearningSignalStrategy
        return MachineLearningSignalStrategy()

    def load_pairs_trading(self):
        from strategies.pairs_trading import PairsTradingStrategy
        return PairsTradingStrategy()
