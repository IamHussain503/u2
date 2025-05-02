# risk/risk_manager.py

import math

class RiskManager:
    def calculate_position_size(
        self,
        balance: float,
        price: float,
        stop_loss: float,
        leverage: int = 1,
        risk_percent: float = 0.01
    ) -> float:
        """
        balance         : account equity in quote currency (e.g. USDT)
        price           : current symbol price
        stop_loss       : absolute price distance to stop (e.g. ATR * multiplier)
        leverage        : contract leverage
        risk_percent    : fraction of balance to risk (e.g. 0.01 → 1%)
        """
        # 1) sanity checks
        if stop_loss <= 0 or price <= 0 or not math.isfinite(stop_loss) or not math.isfinite(price):
            return 0.0

        # 2) $ amount you risk if stop is hit
        risk_amount = balance * risk_percent

        # 3) contracts = risk_amount / (stop_loss * price) 
        contracts = risk_amount / (stop_loss * price)

        # 4) apply leverage
        return contracts * leverage
