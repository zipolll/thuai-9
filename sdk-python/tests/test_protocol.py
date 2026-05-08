"""Protocol contract tests for the Python SDK."""

from __future__ import annotations

import unittest
from typing import TypeAlias

from sdk_python.agent import (
    Agent,
    _parse_game_state,
    _parse_news,
    _parse_player_state,
    _parse_report_result,
    _parse_skill_effect,
    _parse_strategy_options,
)
from sdk_python.models import Prediction

ProtocolMessage: TypeAlias = dict[str, object]


class CapturingAgent(Agent):
    """Agent subclass that records outgoing payloads for assertion."""

    def __init__(self) -> None:
        super().__init__("player-1")
        self.sent_messages: list[ProtocolMessage] = []

    async def _send(self, data: ProtocolMessage) -> None:
        self.sent_messages.append(data)


class ProtocolParserTests(unittest.TestCase):
    """Parser coverage for the Python SDK wire snapshots."""

    def test_parse_game_state_matches_wire_fields(self) -> None:
        """Game-state parsing should preserve the documented wire fields."""

        state = _parse_game_state(
            {
                "stage": "TradingDay",
                "currentMonth": 4,
                "currentDay": 2,
                "currentTick": 73,
                "totalTicks": 300,
                "scores": [
                    {"token": "alpha", "score": 12},
                    {"token": "beta", "score": 8},
                ],
            }
        )

        self.assertEqual("TradingDay", state.stage)
        self.assertEqual(4, state.current_month)
        self.assertEqual(2, state.current_day)
        self.assertEqual(73, state.current_tick)
        self.assertEqual(300, state.total_ticks)
        self.assertEqual(
            [("alpha", 12), ("beta", 8)],
            [(score.token, score.score) for score in state.scores],
        )

    def test_parse_player_state_reads_nested_orders(self) -> None:
        """Player-state parsing should preserve nested orders and quotas."""

        state = _parse_player_state(
            {
                "mora": 1200,
                "frozenMora": 150,
                "gold": 7,
                "frozenGold": 2,
                "lockedGold": 1,
                "nav": 1330,
                "networkDelay": 45,
                "immediateOrdersUsedToday": 3,
                "restingOrdersUsedToday": 5,
                "bonusImmediateOrdersToday": 1,
                "monthlyTradeCount": 14,
                "activeCards": ["Bridge", "Firewall"],
                "pendingOrders": [
                    {
                        "orderId": 88,
                        "arrivalTick": 19,
                        "side": "Sell",
                        "price": 1030,
                        "quantity": 4,
                        "remainingQuantity": 1,
                        "status": "PartiallyFilled",
                        "intent": "Resting",
                    }
                ],
            }
        )

        self.assertEqual(1200, state.mora)
        self.assertEqual(150, state.frozen_mora)
        self.assertEqual(14, state.monthly_trade_count)
        self.assertEqual(["Bridge", "Firewall"], state.active_cards)
        self.assertEqual(1, len(state.pending_orders))

        order = state.pending_orders[0]
        self.assertEqual(88, order.order_id)
        self.assertEqual(19, order.arrival_tick)
        self.assertEqual("Sell", order.side)
        self.assertEqual(1030, order.price)
        self.assertEqual(4, order.quantity)
        self.assertEqual(1, order.remaining_quantity)
        self.assertEqual("PartiallyFilled", order.status)
        self.assertEqual("Resting", order.intent)

    def test_parse_optional_protocol_messages(self) -> None:
        """Optional broadcast payloads should map into the expected SDK models."""

        news = _parse_news(
            {
                "month": 5,
                "day": 1,
                "newsId": 9,
                "content": "Macro outlook improved",
                "publishTick": 101,
            }
        )
        self.assertEqual(
            (5, 1, 9, "Macro outlook improved", 101),
            (news.month, news.day, news.news_id, news.content, news.publish_tick),
        )

        report = _parse_report_result(
            {
                "newsId": 9,
                "submissionRank": 2,
                "submitTick": 104,
                "settlementTick": 180,
                "prediction": "Long",
                "isCorrect": True,
                "reward": 240,
                "actualChange": 60,
            }
        )
        self.assertEqual(2, report.submission_rank)
        self.assertTrue(report.is_correct)
        self.assertEqual(240, report.reward)

        effect = _parse_skill_effect(
            {
                "skillName": "Hedge",
                "sourcePlayer": "alpha",
                "description": "Protected against one loss",
            }
        )
        self.assertEqual("Hedge", effect.skill_name)
        self.assertEqual("alpha", effect.source_player)
        self.assertIsNone(effect.target_player)

        options = _parse_strategy_options(
            {
                "infrastructure": {
                    "name": "Bridge",
                    "description": "Boosts capacity",
                    "category": "Infrastructure",
                },
                "riskControl": None,
                "finTech": {
                    "name": "Flash",
                    "description": "Extra order quota",
                    "category": "FinTech",
                },
            }
        )
        self.assertEqual("Bridge", options.infrastructure.name)
        self.assertIsNone(options.risk_control)
        self.assertEqual("Flash", options.fin_tech.name)

    def test_update_state_tracks_latest_protocol_snapshots(self) -> None:
        """State caches should update when snapshot messages are received."""

        agent = Agent("player-1")

        agent._update_state(  # pylint: disable=protected-access
            "GAME_STATE",
            {
                "stage": "TradingDay",
                "currentMonth": 6,
                "currentDay": 3,
                "currentTick": 150,
                "totalTicks": 300,
                "scores": [{"token": "alpha", "score": 16}],
            },
        )
        agent._update_state(  # pylint: disable=protected-access
            "NEWS_BROADCAST",
            {
                "month": 6,
                "day": 3,
                "newsId": 15,
                "content": "Demand fell",
                "publishTick": 151,
            },
        )
        agent._update_state(  # pylint: disable=protected-access
            "STRATEGY_OPTIONS",
            {
                "infrastructure": {
                    "name": "Tunnel",
                    "description": "Reduces latency",
                    "category": "Infrastructure",
                }
            },
        )

        self.assertEqual(6, agent.game_state.current_month)
        self.assertEqual("Demand fell", agent.latest_news.content)
        self.assertEqual("Tunnel", agent.strategy_options.infrastructure.name)


class ProtocolActionTests(unittest.IsolatedAsyncioTestCase):
    """Outbound action coverage for the Python SDK."""

    async def test_limit_buy_sends_documented_payload(self) -> None:
        """Limit buys should serialize to the documented wire payload."""

        agent = CapturingAgent()

        await agent.limit_buy(1050, 3)

        self.assertEqual(
            [
                {
                    "messageType": "LIMIT_BUY",
                    "token": "player-1",
                    "price": 1050,
                    "quantity": 3,
                }
            ],
            agent.sent_messages,
        )

    async def test_submit_report_serializes_prediction_value(self) -> None:
        """Report submissions should serialize the enum's wire value."""

        agent = CapturingAgent()

        await agent.submit_report(7, Prediction.SHORT)

        self.assertEqual(
            [
                {
                    "messageType": "SUBMIT_REPORT",
                    "token": "player-1",
                    "newsId": 7,
                    "prediction": "Short",
                }
            ],
            agent.sent_messages,
        )

    async def test_activate_skill_omits_empty_optional_fields(self) -> None:
        """Skill payloads should omit unset optional fields."""

        agent = CapturingAgent()

        await agent.activate_skill("MarketRadar")

        self.assertEqual(
            [
                {
                    "messageType": "ACTIVATE_SKILL",
                    "token": "player-1",
                    "skillName": "MarketRadar",
                }
            ],
            agent.sent_messages,
        )

    async def test_activate_skill_includes_target_and_variant(self) -> None:
        """Skill payloads should include populated optional fields."""

        agent = CapturingAgent()

        await agent.activate_skill(
            "Freeze",
            target_token="player-2",
            variant="intense",
        )

        self.assertEqual(
            [
                {
                    "messageType": "ACTIVATE_SKILL",
                    "token": "player-1",
                    "skillName": "Freeze",
                    "targetToken": "player-2",
                    "variant": "intense",
                }
            ],
            agent.sent_messages,
        )


if __name__ == "__main__":
    unittest.main()
