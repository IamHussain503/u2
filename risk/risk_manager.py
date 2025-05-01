class RiskManager:
    """
    Manages risk parameters and calculates position sizes based on stop-loss distance.
    """
    def calculate_position_size(self, balance, price, stop_loss, leverage=10, risk_percent=0.01):
        """
        Calculate the contract size such that if price moves against us by `stop_loss`,
        we risk at most `risk_percent` of `balance`, then apply leverage.

        Parameters:
        - balance (float): Total account balance (or paper capital).
        - price (float): Current entry price for the trade.
        - stop_loss (float): Absolute distance (in price units) from entry to stop loss.
        - leverage (int): Leverage multiplier (default 10).
        - risk_percent (float): Fraction of balance to risk per trade (default 0.01 for 1%).

        Returns:
        - position_size (float): Number of contracts to trade.
        """
        # Maximum dollar amount we're willing to lose
        risk_amount = balance * risk_percent

        # Position size before leverage: risk_amount / stop_loss
        base_size = risk_amount / stop_loss

        # Apply leverage
        position_size = base_size * leverage
        return position_size
