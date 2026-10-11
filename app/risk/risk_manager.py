from datetime import datetime
from typing import Optional, Tuple
from pydantic import BaseModel
from app.simulation.portfolio import VirtualPortfolio
from app.config import config

class RiskEvaluationResult(BaseModel):
    is_approved: bool
    action: str
    symbol: str
    quantity: int
    reason: str
    portfolio_value: float
    current_cash: float
    current_exposure_pct: float
    timestamp: datetime


class RiskManager:
    """Deterministic safety controls and risk management.
    LLM decisions MUST pass through this gatekeeper before simulated execution.
    The LLM cannot override or bypass these rules.
    """

    def __init__(
        self,
        max_position_pct: float = 0.25,      # Max 25% of portfolio in single stock
        max_order_pct: float = 0.10,         # Max 10% of portfolio in single order
        daily_loss_limit_pct: float = 0.05,  # Stop trading if down 5% from peak
        allow_short: bool = False             # Long-only mode
    ):
        self.max_position_pct = max_position_pct
        self.max_order_pct = max_order_pct
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.allow_short = allow_short

    def evaluate_order(
        self,
        portfolio: VirtualPortfolio,
        symbol: str,
        action: str,
        quantity: int,
        market_price: float,
        timestamp: datetime
    ) -> RiskEvaluationResult:
        sym = symbol.upper().strip()
        act = action.upper().strip()
        port_val = portfolio.get_total_portfolio_value()
        curr_cash = portfolio.cash
        pos = portfolio.get_position(sym)
        current_pos_val = pos.market_value
        current_exposure_pct = round((portfolio.get_total_position_value() / max(port_val, 1.0)), 4)

        # 1. HOLD action is always safe and approved without state change
        if act == "HOLD":
            return RiskEvaluationResult(
                is_approved=True,
                action="HOLD",
                symbol=sym,
                quantity=0,
                reason="HOLD action approved (no risk change).",
                portfolio_value=port_val,
                current_cash=curr_cash,
                current_exposure_pct=current_exposure_pct,
                timestamp=timestamp
            )

        # 2. Basic sanitization checks
        if act not in ["BUY", "SELL"]:
            return RiskEvaluationResult(
                is_approved=False,
                action=act,
                symbol=sym,
                quantity=quantity,
                reason=f"Invalid action '{act}'. Allowed: BUY, SELL, HOLD.",
                portfolio_value=port_val,
                current_cash=curr_cash,
                current_exposure_pct=current_exposure_pct,
                timestamp=timestamp
            )

        if quantity <= 0:
            return RiskEvaluationResult(
                is_approved=False,
                action=act,
                symbol=sym,
                quantity=quantity,
                reason=f"Order quantity must be positive, got {quantity}.",
                portfolio_value=port_val,
                current_cash=curr_cash,
                current_exposure_pct=current_exposure_pct,
                timestamp=timestamp
            )

        order_val = quantity * market_price

        # 3. Cash check for BUY (immediate physical insolvency check)
        if act == "BUY":
            est_cost = order_val * 1.002
            if curr_cash < est_cost:
                return RiskEvaluationResult(
                    is_approved=False,
                    action=act,
                    symbol=sym,
                    quantity=quantity,
                    reason=f"Insufficient virtual cash. Needed: ₹{est_cost:.2f}, Available: ₹{curr_cash:.2f}.",
                    portfolio_value=port_val,
                    current_cash=curr_cash,
                    current_exposure_pct=current_exposure_pct,
                    timestamp=timestamp
                )

        # 4. Daily loss limit check (drawdown circuit breaker)
        if portfolio.initial_capital > 0:
            current_drawdown_pct = (portfolio.initial_capital - port_val) / portfolio.initial_capital
            if current_drawdown_pct >= self.daily_loss_limit_pct and act == "BUY":
                return RiskEvaluationResult(
                    is_approved=False,
                    action=act,
                    symbol=sym,
                    quantity=quantity,
                    reason=f"Drawdown circuit breaker triggered ({current_drawdown_pct*100:.2f}% >= {self.daily_loss_limit_pct*100:.1f}%). New BUY orders halted.",
                    portfolio_value=port_val,
                    current_cash=curr_cash,
                    current_exposure_pct=current_exposure_pct,
                    timestamp=timestamp
                )

        # 5. BUY Sizing & Concentration Validation
        if act == "BUY":

            # Max order size limit
            max_order_allowed = port_val * self.max_order_pct
            if order_val > max_order_allowed:
                return RiskEvaluationResult(
                    is_approved=False,
                    action=act,
                    symbol=sym,
                    quantity=quantity,
                    reason=f"Order value ₹{order_val:.2f} exceeds max order limit of ₹{max_order_allowed:.2f} ({self.max_order_pct*100:.1f}%).",
                    portfolio_value=port_val,
                    current_cash=curr_cash,
                    current_exposure_pct=current_exposure_pct,
                    timestamp=timestamp
                )

            # Max position concentration limit
            post_pos_val = current_pos_val + order_val
            max_pos_allowed = port_val * self.max_position_pct
            if post_pos_val > max_pos_allowed:
                return RiskEvaluationResult(
                    is_approved=False,
                    action=act,
                    symbol=sym,
                    quantity=quantity,
                    reason=f"Post-trade position value ₹{post_pos_val:.2f} exceeds concentration limit of ₹{max_pos_allowed:.2f} ({self.max_position_pct*100:.1f}%).",
                    portfolio_value=port_val,
                    current_cash=curr_cash,
                    current_exposure_pct=current_exposure_pct,
                    timestamp=timestamp
                )

            return RiskEvaluationResult(
                is_approved=True,
                action=act,
                symbol=sym,
                quantity=quantity,
                reason="BUY order passed all risk checks (cash, order size, concentration).",
                portfolio_value=port_val,
                current_cash=curr_cash,
                current_exposure_pct=current_exposure_pct,
                timestamp=timestamp
            )

        # 5. SELL Validation
        if act == "SELL":
            if not self.allow_short and pos.quantity < quantity:
                return RiskEvaluationResult(
                    is_approved=False,
                    action=act,
                    symbol=sym,
                    quantity=quantity,
                    reason=f"Cannot SELL {quantity} shares of {sym}. Virtual holdings available: {pos.quantity}.",
                    portfolio_value=port_val,
                    current_cash=curr_cash,
                    current_exposure_pct=current_exposure_pct,
                    timestamp=timestamp
                )

            return RiskEvaluationResult(
                is_approved=True,
                action=act,
                symbol=sym,
                quantity=quantity,
                reason=f"SELL order approved. Selling {quantity} of {pos.quantity} held shares.",
                portfolio_value=port_val,
                current_cash=curr_cash,
                current_exposure_pct=current_exposure_pct,
                timestamp=timestamp
            )

        return RiskEvaluationResult(
            is_approved=False,
            action=act,
            symbol=sym,
            quantity=quantity,
            reason="Order rejected by default safety gate.",
            portfolio_value=port_val,
            current_cash=curr_cash,
            current_exposure_pct=current_exposure_pct,
            timestamp=timestamp
        )
