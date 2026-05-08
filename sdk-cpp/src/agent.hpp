#pragma once
#include <string>
#include <functional>
#include <iostream>
#include <thread>
#include <chrono>
#include <atomic>
#include <nlohmann/json.hpp>
#include <ixwebsocket/IXWebSocket.h>
#include "models.hpp"
#include "protocol.hpp"

namespace thuai {

using json = nlohmann::json;

class Agent {
public:
    Agent(const std::string& token, const std::string& serverUrl = "ws://localhost:14514")
        : token_(token), serverUrl_(serverUrl) {}

    virtual ~Agent() = default;

    // --- Actions ---
    void limitBuy(long price, int quantity) {
        send(protocol::buildLimitBuyMessage(token_, price, quantity));
    }

    void limitSell(long price, int quantity) {
        send(protocol::buildLimitSellMessage(token_, price, quantity));
    }

    void cancelOrder(long orderId) {
        send(protocol::buildCancelOrderMessage(token_, orderId));
    }

    void submitReport(int newsId, Prediction prediction) {
        send(protocol::buildSubmitReportMessage(token_, newsId, prediction));
    }

    void selectStrategy(const std::string& cardName) {
        send(protocol::buildSelectStrategyMessage(token_, cardName));
    }

    void activateSkill(
        const std::string& skillName,
        const std::string& targetToken = "",
        const std::string& variant = "") {
        send(protocol::buildActivateSkillMessage(
            token_,
            skillName,
            targetToken.empty() ? std::nullopt : std::make_optional(targetToken),
            variant.empty() ? std::nullopt : std::make_optional(variant)));
    }

    // --- State ---
    GameState gameState;
    MarketState marketState;
    PlayerState playerState;
    std::optional<News> latestNews;
    std::optional<StrategyOptions> strategyOptions;

    // --- Event Handlers (override these) ---
    virtual void onGameState(const GameState&) {}
    virtual void onMarketState(const MarketState&) {}
    virtual void onPlayerState(const PlayerState&) {}
    virtual void onNews(const News&) {}
    virtual void onReportResult(const ReportResult&) {}
    virtual void onStrategyOptions(const StrategyOptions&) {}
    virtual void onTrade(const TradeNotification&) {}
    virtual void onSkillEffect(const SkillEffect&) {}
    virtual void onError(int code, const std::string& message) {}

    // --- Run ---
    void run() {
        std::atomic_bool closed{false};

        ws_.setUrl(serverUrl_);
        ws_.setOnMessageCallback([this, &closed](const ix::WebSocketMessagePtr& msg) {
            if (msg->type == ix::WebSocketMessageType::Message) {
                handleMessage(msg->str);
            } else if (msg->type == ix::WebSocketMessageType::Open) {
                std::cout << "[Agent] Connected to " << serverUrl_ << std::endl;
                cancelOrder(-1);
            } else if (msg->type == ix::WebSocketMessageType::Close) {
                std::cout << "[Agent] Disconnected" << std::endl;
                closed = true;
            } else if (msg->type == ix::WebSocketMessageType::Error) {
                std::cerr << "[Agent] Error: " << msg->errorInfo.reason << std::endl;
                closed = true;
            }
        });
        ws_.start();

        // Block until disconnected or game ends
        while (!closed) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            if (gameState.stage == "Finished") break;
        }
        ws_.stop();
    }

private:
    std::string token_;
    std::string serverUrl_;
    ix::WebSocket ws_;

    void send(const json& data) {
        ws_.send(data.dump());
    }

    void handleMessage(const std::string& raw) {
        try {
            auto data = json::parse(raw);
            std::string msgType = data.value("messageType", "");

            if (msgType == "GAME_STATE") {
                gameState = protocol::parseGameState(data);
                onGameState(gameState);
            } else if (msgType == "MARKET_STATE") {
                marketState = protocol::parseMarketState(data);
                onMarketState(marketState);
            } else if (msgType == "PLAYER_STATE") {
                playerState = protocol::parsePlayerState(data);
                onPlayerState(playerState);
            } else if (msgType == "NEWS_BROADCAST") {
                latestNews = protocol::parseNews(data);
                onNews(*latestNews);
            } else if (msgType == "REPORT_RESULT") {
                onReportResult(protocol::parseReportResult(data));
            } else if (msgType == "STRATEGY_OPTIONS") {
                strategyOptions = protocol::parseStrategyOptions(data);
                onStrategyOptions(*strategyOptions);
            } else if (msgType == "TRADE_NOTIFICATION") {
                onTrade(protocol::parseTrade(data));
            } else if (msgType == "SKILL_EFFECT") {
                onSkillEffect(protocol::parseSkillEffect(data));
            } else if (msgType == "ERROR") {
                onError(data.value("errorCode", 0), data.value("message", std::string("")));
            }
        } catch (const std::exception& e) {
            std::cerr << "[Agent] Parse error: " << e.what() << std::endl;
        }
    }
};

} // namespace thuai
