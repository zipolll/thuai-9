"""Typed protocol models used by the THUAI Python SDK."""

from dataclasses import dataclass, field
from enum import Enum


class GameStage(Enum):
    """Lifecycle stages broadcast by the game server."""

    WAITING = "Waiting"
    PREPARING = "PreparingGame"
    STRATEGY = "StrategySelection"
    TRADING = "TradingDay"
    SETTLEMENT = "Settlement"
    FINISHED = "Finished"


class Prediction(Enum):
    """Valid directions for report submissions."""

    LONG = "Long"
    SHORT = "Short"
    HOLD = "Hold"


@dataclass
class PriceLevel:
    """Visible quantity available at a single price level."""

    price: int
    quantity: int


@dataclass
class OrderInfo:  # pylint: disable=too-many-instance-attributes
    """A pending order owned by the current player."""

    order_id: int
    arrival_tick: int
    side: str
    price: int
    quantity: int
    remaining_quantity: int
    status: str
    intent: str = ""


@dataclass
class CardOption:
    """A strategy card that may be chosen during setup."""

    name: str
    description: str
    category: str


@dataclass
class PlayerScore:
    """Scoreboard entry for a single player."""

    token: str
    score: int


@dataclass
class GameState:
    """Top-level game progress snapshot."""

    stage: str = ""
    current_month: int = 0
    current_day: int = 0
    current_tick: int = 0
    total_ticks: int = 0
    scores: list[PlayerScore] = field(default_factory=list)


@dataclass
class MarketState:
    """Public order book and price summary snapshot."""

    bids: list[PriceLevel] = field(default_factory=list)
    asks: list[PriceLevel] = field(default_factory=list)
    last_price: int = 0
    mid_price: int = 0
    volume: int = 0
    tick: int = 0


@dataclass
class PlayerState:  # pylint: disable=too-many-instance-attributes
    """Private portfolio and quota snapshot for the current player."""

    mora: int = 0
    frozen_mora: int = 0
    gold: int = 0
    frozen_gold: int = 0
    locked_gold: int = 0
    nav: int = 0
    network_delay: int = 0
    immediate_orders_used_today: int = 0
    resting_orders_used_today: int = 0
    bonus_immediate_orders_today: int = 0
    monthly_trade_count: int = 0
    active_cards: list[str] = field(default_factory=list)
    pending_orders: list[OrderInfo] = field(default_factory=list)


@dataclass
class News:
    """Published news item available for research reports."""

    month: int = 0
    day: int = 0
    news_id: int = 0
    content: str = ""
    publish_tick: int = 0


@dataclass
class ReportResult:  # pylint: disable=too-many-instance-attributes
    """Outcome of a previously submitted report."""

    news_id: int = 0
    submission_rank: int = 0
    submit_tick: int = 0
    settlement_tick: int = 0
    prediction: str = ""
    is_correct: bool = False
    reward: int = 0
    actual_change: int = 0


@dataclass
class StrategyOptions:
    """Available strategy choices grouped by category."""

    infrastructure: CardOption | None = None
    risk_control: CardOption | None = None
    fin_tech: CardOption | None = None


@dataclass
class TradeNotification:
    """Trade execution details for one matched order."""

    trade_id: int = 0
    order_id: int = 0
    price: int = 0
    quantity: int = 0
    side: str = ""
    fee: int = 0


@dataclass
class SkillEffect:
    """Broadcast description of a resolved skill effect."""

    skill_name: str = ""
    source_player: str = ""
    target_player: str | None = None
    description: str = ""
