import pytest
from pydantic import ValidationError
from app.agents.schemas import TradeActionProposal

def test_trade_action_proposal_valid():
    proposal = TradeActionProposal(
        action="BUY",
        symbol="reliance",
        quantity=5,
        confidence=0.8,
        decision_summary="Bullish trend with MACD crossover.",
        risk_summary="Order is within 5% capital allocation.",
        conditions_to_reconsider=["Price breaks below support"]
    )
    assert proposal.symbol == "RELIANCE"
    assert proposal.action == "BUY"
    assert proposal.quantity == 5

def test_trade_action_proposal_rejects_negative_quantity():
    with pytest.raises(ValidationError):
        TradeActionProposal(
            action="BUY",
            symbol="INFY",
            quantity=-10,
            decision_summary="Test",
            risk_summary="Test"
        )

def test_trade_action_proposal_rejects_invalid_action():
    with pytest.raises(ValidationError):
        TradeActionProposal(
            action="SHORT_SELL",  # Invalid action
            symbol="INFY",
            quantity=5,
            decision_summary="Test",
            risk_summary="Test"
        )
