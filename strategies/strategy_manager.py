class StrategyManager:
    def __init__(self):
        self.strategy_map = {
            "EMA Crossover": self.load_ema_crossover(),
            "RSI Divergence": self.load_rsi_divergence(),
            "Bollinger Breakout": self.load_bollinger_breakout(),
            "MACD Crossover":       self.load_macd_crossover(),
            "SMA Crossover":        self.load_sma_crossover(),
            "RSI+MACD Combo":       self.load_rsi_macd_combo(),
            "Donchian Breakout":    self.load_donchian_breakout(),
            "BB+RSI Combo":         self.load_bb_rsi_combo(),
    # … plus your existing EMA, RSI, BB strategies

        }

    def get_strategy(self, name):
        return self.strategy_map.get(name, None)

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
