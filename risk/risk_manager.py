class RiskManager:
    def calculate_position_size(self, balance, price, stop_loss_distance, leverage=10, risk_percent=0.01):
        risk_amount = balance * risk_percent
        position_size = risk_amount / (stop_loss_distance * price) * price * leverage
        return position_size