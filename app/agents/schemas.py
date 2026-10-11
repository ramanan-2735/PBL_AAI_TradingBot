from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

class TradeActionProposal(BaseModel):
    """Strict structured output model for the autonomous trading agent.
    Ensures that LLM generated actions are completely type-safe and validated.
    """
    action: Literal["BUY", "SELL", "HOLD"] = Field(
        description="The chosen market action: BUY, SELL, or HOLD"
    )
    symbol: str = Field(
        description="Ticker symbol for the action, e.g., RELIANCE"
    )
    quantity: int = Field(
        default=0,
        description="Number of shares to buy or sell. Must be 0 for HOLD, > 0 for BUY or SELL."
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Agent subjective confidence score between 0.0 and 1.0"
    )
    decision_summary: str = Field(
        description="Concise, auditable one-to-two sentence explanation of the reasoning."
    )
    risk_summary: str = Field(
        description="Evaluation of portfolio exposure and downside protection consideration."
    )
    conditions_to_reconsider: List[str] = Field(
        default_factory=list,
        description="Key market events or indicators that would invalidate this decision."
    )

    @field_validator("symbol")
    @classmethod
    def clean_symbol(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("quantity")
    @classmethod
    def validate_quantity_bounds(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Quantity cannot be negative")
        return int(v)


class AgentState(BaseModel):
    """LangGraph agent state carrying strictly the context required for the current cycle."""
    symbol: str
    timestamp: str
    current_price: float
    market_snapshot: dict = Field(default_factory=dict)
    portfolio_summary: dict = Field(default_factory=dict)
    recent_decisions: List[dict] = Field(default_factory=list)
    recent_trades: List[dict] = Field(default_factory=list)
    
    # Reasoning & Output
    tool_outputs: dict = Field(default_factory=dict)
    decision: Optional[TradeActionProposal] = None
    risk_result: Optional[dict] = None
    execution_result: Optional[dict] = None
    cycle_status: str = "INITIALIZED"
    error_message: Optional[str] = None
