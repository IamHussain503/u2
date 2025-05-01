# risk/risk_manager.py

import math

class RiskManager:
    def calculate_position_size(self,
                                balance: float,
                                price:   float,
                                stop_loss: float,
                                leverage:    int = 10,
                                risk_percent: float = 0.01) -> float:
        """
        Returns how many contracts/units to trade given:
         - balance (account equity),
         - current price,
         - absolute price-distance to your stop (stop_loss),
         - leverage,
         - risk_percent of balance to risk.
        """

        # 1) guard against zero/negative/NaN stops or prices
        if not math.isfinite(stop_loss) or stop_loss <= 0:
            # can't size a position if your stop distance is zero or invalid
            return 0.0
        if not math.isfinite(price) or price <= 0:
            return 0.0

        # 2) compute risk amount and raw contract count
        risk_amount   = balance * risk_percent
        contracts     = risk_amount / (stop_loss * price)

        # 3) apply leverage
        position_size = contracts * leverage

        return position_size
