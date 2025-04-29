class StrategyManager:
    def __init__(self):
        self.strategy_map = {
            "EMA Crossover": self.load_ema_crossover(),
            "RSI Divergence": self.load_rsi_divergence(),
            "Bollinger Breakout": self.load_bollinger_breakout()
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