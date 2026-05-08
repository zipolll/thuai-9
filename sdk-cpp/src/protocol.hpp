#ifndef THUAI_PROTOCOL_HPP
#define THUAI_PROTOCOL_HPP
#include <optional>
#include <string>
#include <nlohmann/json.hpp>
#include "models.hpp"

namespace thuai {
namespace protocol {

using json = nlohmann::json;

inline json buildLimitBuyMessage(const std::string& token, long price, int quantity) {
    return {{"messageType", "LIMIT_BUY"}, {"token", token}, {"price", price}, {"quantity", quantity}};
}

inline json buildLimitSellMessage(const std::string& token, long price, int quantity) {
    return {{"messageType", "LIMIT_SELL"}, {"token", token}, {"price", price}, {"quantity", quantity}};
}

inline json buildCancelOrderMessage(const std::string& token, long orderId) {
    return {{"messageType", "CANCEL_ORDER"}, {"token", token}, {"orderId", orderId}};
}

inline json buildSubmitReportMessage(const std::string& token, int newsId, Prediction prediction) {
    return {{"messageType", "SUBMIT_REPORT"}, {"token", token}, {"newsId", newsId}, {"prediction", predictionToString(prediction)}};
}

inline json buildSelectStrategyMessage(const std::string& token, const std::string& cardName) {
    return {{"messageType", "SELECT_STRATEGY"}, {"token", token}, {"cardName", cardName}};
}

inline json buildActivateSkillMessage(
    const std::string& token,
    const std::string& skillName,
    const std::optional<std::string>& targetToken = std::nullopt,
    const std::optional<std::string>& variant = std::nullopt) {
    json msg = {{"messageType", "ACTIVATE_SKILL"}, {"token", token}, {"skillName", skillName}};
    if (targetToken.has_value()) {
        msg["targetToken"] = *targetToken;
    }
    if (variant.has_value()) {
        msg["variant"] = *variant;
    }
    return msg;
}

inline GameState parseGameState(const json& d) {
    GameState state;
    state.stage = d.value("stage", "");
    state.currentMonth = d.value("currentMonth", 0);
    state.currentDay = d.value("currentDay", 0);
    state.currentTick = d.value("currentTick", 0);
    state.totalTicks = d.value("totalTicks", 0);
    if (d.contains("scores") && d["scores"].is_array()) {
        for (const auto& s : d["scores"]) {
            PlayerScore ps;
            ps.token = s.value("token", "");
            ps.score = s.value("score", 0);
            state.scores.push_back(ps);
        }
    }
    return state;
}

inline MarketState parseMarketState(const json& d) {
    MarketState state;
    if (d.contains("bids") && d["bids"].is_array()) {
        for (const auto& b : d["bids"]) {
            PriceLevel pl;
            pl.price = b.value("price", 0L);
            pl.quantity = b.value("quantity", 0);
            state.bids.push_back(pl);
        }
    }
    if (d.contains("asks") && d["asks"].is_array()) {
        for (const auto& a : d["asks"]) {
            PriceLevel pl;
            pl.price = a.value("price", 0L);
            pl.quantity = a.value("quantity", 0);
            state.asks.push_back(pl);
        }
    }
    state.lastPrice = d.value("lastPrice", 0L);
    state.midPrice = d.value("midPrice", 0L);
    state.volume = d.value("volume", 0);
    state.tick = d.value("tick", 0);
    return state;
}

inline PlayerState parsePlayerState(const json& d) {
    PlayerState state;
    state.mora = d.value("mora", 0L);
    state.frozenMora = d.value("frozenMora", 0L);
    state.gold = d.value("gold", 0);
    state.frozenGold = d.value("frozenGold", 0);
    state.lockedGold = d.value("lockedGold", 0);
    state.nav = d.value("nav", 0L);
    state.networkDelay = d.value("networkDelay", 0);
    state.immediateOrdersUsedToday = d.value("immediateOrdersUsedToday", 0);
    state.restingOrdersUsedToday = d.value("restingOrdersUsedToday", 0);
    state.bonusImmediateOrdersToday = d.value("bonusImmediateOrdersToday", 0);
    state.monthlyTradeCount = d.value("monthlyTradeCount", 0);
    if (d.contains("activeCards") && d["activeCards"].is_array()) {
        for (const auto& c : d["activeCards"]) {
            if (c.is_string()) {
                state.activeCards.push_back(c.get<std::string>());
            }
        }
    }
    if (d.contains("pendingOrders") && d["pendingOrders"].is_array()) {
        for (const auto& o : d["pendingOrders"]) {
            OrderInfo oi;
            oi.orderId = o.value("orderId", 0L);
            oi.arrivalTick = o.value("arrivalTick", 0);
            oi.side = o.value("side", "");
            oi.price = o.value("price", 0L);
            oi.quantity = o.value("quantity", 0);
            oi.remainingQuantity = o.value("remainingQuantity", 0);
            oi.status = o.value("status", "");
            oi.intent = o.value("intent", "");
            state.pendingOrders.push_back(oi);
        }
    }
    return state;
}

inline News parseNews(const json& d) {
    News news;
    news.month = d.value("month", 0);
    news.day = d.value("day", 0);
    news.newsId = d.value("newsId", 0);
    news.content = d.value("content", "");
    news.publishTick = d.value("publishTick", 0);
    return news;
}

inline ReportResult parseReportResult(const json& d) {
    ReportResult result;
    result.newsId = d.value("newsId", 0);
    result.submissionRank = d.value("submissionRank", 0);
    result.submitTick = d.value("submitTick", 0);
    result.settlementTick = d.value("settlementTick", 0);
    result.prediction = d.value("prediction", "");
    result.isCorrect = d.value("isCorrect", false);
    result.reward = d.value("reward", 0L);
    result.actualChange = d.value("actualChange", 0L);
    return result;
}

inline StrategyOptions parseStrategyOptions(const json& d) {
    StrategyOptions opts;
    auto parseCard = [](const json& c) -> std::optional<CardOption> {
        if (c.is_null() || !c.is_object()) {
            return std::nullopt;
        }
        CardOption card;
        card.name = c.value("name", "");
        card.description = c.value("description", "");
        card.category = c.value("category", "");
        return card;
    };
    if (d.contains("infrastructure")) {
        opts.infrastructure = parseCard(d["infrastructure"]);
    }
    if (d.contains("riskControl")) {
        opts.riskControl = parseCard(d["riskControl"]);
    }
    if (d.contains("finTech")) {
        opts.finTech = parseCard(d["finTech"]);
    }
    return opts;
}

inline TradeNotification parseTrade(const json& d) {
    TradeNotification trade;
    trade.tradeId = d.value("tradeId", 0L);
    trade.orderId = d.value("orderId", 0L);
    trade.price = d.value("price", 0L);
    trade.quantity = d.value("quantity", 0);
    trade.side = d.value("side", "");
    trade.fee = d.value("fee", 0L);
    return trade;
}

inline SkillEffect parseSkillEffect(const json& d) {
    SkillEffect effect;
    effect.skillName = d.value("skillName", "");
    effect.sourcePlayer = d.value("sourcePlayer", "");
    if (d.contains("targetPlayer") && !d["targetPlayer"].is_null()) {
        effect.targetPlayer = d.value("targetPlayer", std::string(""));
    }
    effect.description = d.value("description", "");
    return effect;
}

} // namespace protocol
} // namespace thuai

#endif // THUAI_PROTOCOL_HPP
