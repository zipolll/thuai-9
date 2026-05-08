"""High-level asynchronous client for the THUAI websocket protocol."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any, TypeAlias

from websockets import connect

from .models import (
    CardOption,
    GameState,
    MarketState,
    News,
    OrderInfo,
    PlayerScore,
    PlayerState,
    Prediction,
    PriceLevel,
    ReportResult,
    SkillEffect,
    StrategyOptions,
    TradeNotification,
)

JsonObject: TypeAlias = Mapping[str, Any]
OutgoingMessage: TypeAlias = dict[str, Any]

logger = logging.getLogger("thuai")


class Agent:  # pylint: disable=too-many-instance-attributes
    """Stateful websocket agent that sends actions and tracks server snapshots."""

    def __init__(self, token: str, server_url: str = "ws://localhost:14514") -> None:
        self.token = token
        self.server_url = server_url
        self._ws: Any | None = None

        # Current state is refreshed automatically as snapshots arrive.
        self.game_state = GameState()
        self.market_state = MarketState()
        self.player_state = PlayerState()
        self.latest_news: News | None = None
        self.strategy_options: StrategyOptions | None = None

    async def connect(self) -> None:
        """Open the websocket connection and register with a sentinel cancel."""

        self._ws = await connect(self.server_url)
        logger.info("Connected to %s", self.server_url)
        await self.cancel_order(-1)

    async def disconnect(self) -> None:
        """Close the websocket connection if it is currently open."""

        if self._ws:
            await self._ws.close()

    # --- Actions ---

    async def limit_buy(self, price: int, quantity: int) -> None:
        """Submit a limit buy order."""

        await self._send(
            {
                "messageType": "LIMIT_BUY",
                "token": self.token,
                "price": price,
                "quantity": quantity,
            }
        )

    async def limit_sell(self, price: int, quantity: int) -> None:
        """Submit a limit sell order."""

        await self._send(
            {
                "messageType": "LIMIT_SELL",
                "token": self.token,
                "price": price,
                "quantity": quantity,
            }
        )

    async def cancel_order(self, order_id: int) -> None:
        """Cancel an existing order by identifier."""

        await self._send(
            {
                "messageType": "CANCEL_ORDER",
                "token": self.token,
                "orderId": order_id,
            }
        )

    async def submit_report(self, news_id: int, prediction: Prediction) -> None:
        """Submit a research report for a published news item."""

        await self._send(
            {
                "messageType": "SUBMIT_REPORT",
                "token": self.token,
                "newsId": news_id,
                "prediction": prediction.value,
            }
        )

    async def select_strategy(self, card_name: str) -> None:
        """Choose a strategy card during the strategy-selection stage."""

        await self._send(
            {
                "messageType": "SELECT_STRATEGY",
                "token": self.token,
                "cardName": card_name,
            }
        )

    async def activate_skill(
        self,
        skill_name: str,
        target_token: str | None = None,
        variant: str | None = None,
    ) -> None:
        """Activate a skill, optionally targeting a player or variant."""

        msg: OutgoingMessage = {
            "messageType": "ACTIVATE_SKILL",
            "token": self.token,
            "skillName": skill_name,
        }
        if target_token:
            msg["targetToken"] = target_token
        if variant:
            msg["variant"] = variant
        await self._send(msg)

    # --- Event Loop ---

    async def run(self) -> None:
        """Connect, consume server messages, and dispatch callbacks."""

        await self.connect()
        try:
            async for raw in self._ws:
                try:
                    data = json.loads(raw)
                    msg_type = data.get("messageType", "")
                    self._update_state(msg_type, data)
                    await self._dispatch(msg_type, data)
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON: %s", raw)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.error("Error handling message: %s", exc)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("Connection error: %s", exc)
        finally:
            await self.disconnect()

    # --- Override these in your agent ---

    async def on_game_state(self, state: GameState) -> None:
        """Handle a new game-state snapshot."""

    async def on_market_state(self, state: MarketState) -> None:
        """Handle a new market-state snapshot."""

    async def on_player_state(self, state: PlayerState) -> None:
        """Handle a new player-state snapshot."""

    async def on_news(self, news: News) -> None:
        """Handle a newly published news item."""

    async def on_report_result(self, result: ReportResult) -> None:
        """Handle the settlement result of a submitted report."""

    async def on_strategy_options(self, options: StrategyOptions) -> None:
        """Handle the current strategy card choices."""

    async def on_trade(self, trade: TradeNotification) -> None:
        """Handle a trade execution notification."""

    async def on_skill_effect(self, effect: SkillEffect) -> None:
        """Handle a skill effect broadcast."""

    async def on_error(self, code: int, message: str) -> None:
        """Handle an error message from the server."""

    # --- Internal ---

    async def _send(self, data: OutgoingMessage) -> None:
        """Serialize and send a client action payload."""

        if self._ws:
            await self._ws.send(json.dumps(data))

    def _update_state(self, msg_type: str, data: JsonObject) -> None:
        """Refresh cached state from an inbound snapshot message."""

        if msg_type == "GAME_STATE":
            self.game_state = _parse_game_state(data)
        elif msg_type == "MARKET_STATE":
            self.market_state = _parse_market_state(data)
        elif msg_type == "PLAYER_STATE":
            self.player_state = _parse_player_state(data)
        elif msg_type == "NEWS_BROADCAST":
            self.latest_news = _parse_news(data)
        elif msg_type == "STRATEGY_OPTIONS":
            self.strategy_options = _parse_strategy_options(data)

    async def _dispatch(self, msg_type: str, data: JsonObject) -> None:
        """Invoke the public callback that matches an inbound message type."""

        if msg_type == "GAME_STATE":
            await self.on_game_state(self.game_state)
        elif msg_type == "MARKET_STATE":
            await self.on_market_state(self.market_state)
        elif msg_type == "PLAYER_STATE":
            await self.on_player_state(self.player_state)
        elif msg_type == "NEWS_BROADCAST":
            await self.on_news(self.latest_news)
        elif msg_type == "REPORT_RESULT":
            await self.on_report_result(_parse_report_result(data))
        elif msg_type == "STRATEGY_OPTIONS":
            await self.on_strategy_options(self.strategy_options)
        elif msg_type == "TRADE_NOTIFICATION":
            await self.on_trade(_parse_trade(data))
        elif msg_type == "SKILL_EFFECT":
            await self.on_skill_effect(_parse_skill_effect(data))
        elif msg_type == "ERROR":
            await self.on_error(data.get("errorCode", 0), data.get("message", ""))


# --- Parsers ---


def _parse_game_state(data: JsonObject) -> GameState:
    """Convert a wire-format game-state payload into a SDK model."""

    scores = [
        PlayerScore(score["token"], score["score"])
        for score in data.get("scores", []) or []
    ]
    return GameState(
        stage=data.get("stage", ""),
        current_month=data.get("currentMonth", 0),
        current_day=data.get("currentDay", 0),
        current_tick=data.get("currentTick", 0),
        total_ticks=data.get("totalTicks", 0),
        scores=scores,
    )


def _parse_market_state(data: JsonObject) -> MarketState:
    """Convert a wire-format market-state payload into a SDK model."""

    bids = [
        PriceLevel(level["price"], level["quantity"])
        for level in data.get("bids", []) or []
    ]
    asks = [
        PriceLevel(level["price"], level["quantity"])
        for level in data.get("asks", []) or []
    ]
    return MarketState(
        bids=bids,
        asks=asks,
        last_price=data.get("lastPrice", 0),
        mid_price=data.get("midPrice", 0),
        volume=data.get("volume", 0),
        tick=data.get("tick", 0),
    )


def _parse_player_state(data: JsonObject) -> PlayerState:
    """Convert a wire-format player-state payload into a SDK model."""

    orders = [
        OrderInfo(
            order["orderId"],
            order.get("arrivalTick", 0),
            order["side"],
            order["price"],
            order["quantity"],
            order["remainingQuantity"],
            order["status"],
            order.get("intent", ""),
        )
        for order in data.get("pendingOrders", []) or []
    ]
    return PlayerState(
        mora=data.get("mora", 0),
        frozen_mora=data.get("frozenMora", 0),
        gold=data.get("gold", 0),
        frozen_gold=data.get("frozenGold", 0),
        locked_gold=data.get("lockedGold", 0),
        nav=data.get("nav", 0),
        network_delay=data.get("networkDelay", 0),
        immediate_orders_used_today=data.get("immediateOrdersUsedToday", 0),
        resting_orders_used_today=data.get("restingOrdersUsedToday", 0),
        bonus_immediate_orders_today=data.get("bonusImmediateOrdersToday", 0),
        monthly_trade_count=data.get("monthlyTradeCount", 0),
        active_cards=data.get("activeCards", []) or [],
        pending_orders=orders,
    )


def _parse_news(data: JsonObject) -> News:
    """Convert a wire-format news payload into a SDK model."""

    return News(
        data.get("month", 0),
        data.get("day", 0),
        data.get("newsId", 0),
        data.get("content", ""),
        data.get("publishTick", 0),
    )


def _parse_report_result(data: JsonObject) -> ReportResult:
    """Convert a wire-format report-result payload into a SDK model."""

    return ReportResult(
        data.get("newsId", 0),
        data.get("submissionRank", 0),
        data.get("submitTick", 0),
        data.get("settlementTick", 0),
        data.get("prediction", ""),
        data.get("isCorrect", False),
        data.get("reward", 0),
        data.get("actualChange", 0),
    )


def _parse_strategy_options(data: JsonObject) -> StrategyOptions:
    """Convert a wire-format strategy-options payload into a SDK model."""

    def parse_card(card: JsonObject | None) -> CardOption | None:
        """Parse a single card entry if it is present."""

        if not card:
            return None
        return CardOption(
            card.get("name", ""),
            card.get("description", ""),
            card.get("category", ""),
        )

    return StrategyOptions(
        parse_card(data.get("infrastructure")),
        parse_card(data.get("riskControl")),
        parse_card(data.get("finTech")),
    )


def _parse_trade(data: JsonObject) -> TradeNotification:
    """Convert a wire-format trade-notification payload into a SDK model."""

    return TradeNotification(
        data.get("tradeId", 0),
        data.get("orderId", 0),
        data.get("price", 0),
        data.get("quantity", 0),
        data.get("side", ""),
        data.get("fee", 0),
    )


def _parse_skill_effect(data: JsonObject) -> SkillEffect:
    """Convert a wire-format skill-effect payload into a SDK model."""

    return SkillEffect(
        data.get("skillName", ""),
        data.get("sourcePlayer", ""),
        data.get("targetPlayer"),
        data.get("description", ""),
    )
