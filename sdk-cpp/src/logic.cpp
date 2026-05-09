#include "logic.hpp"

#include <memory>
#include <string>
#include <utility>

#include <spdlog/spdlog.h>

namespace {

class MyAgent final : public thuai::Agent {
public:
    using Agent::Agent;

    void onGameState(const thuai::GameState& state) override {
        spdlog::info(
            "Game update: stage={} month={} day={} tick={}/{} scoreEntries={}",
            state.stage,
            state.currentMonth,
            state.currentDay,
            state.currentTick,
            state.totalTicks,
            state.scores.size()
        );
    }

    void onMarketState(const thuai::MarketState& state) override {
        if (state.tick - lastOrderTick_ < kOrderCooldownTicks) {
            spdlog::debug(
                "Skipping market tick {} because cooldown has {} ticks remaining",
                state.tick,
                kOrderCooldownTicks - (state.tick - lastOrderTick_)
            );
            return;
        }

        if (!state.bids.empty() && playerState.gold > 0) {
            const auto& bestBid = state.bids.front();
            spdlog::info(
                "Selling into best bid price={} quantity=1 availableGold={} nav={}",
                bestBid.price,
                playerState.gold,
                playerState.nav
            );
            limitSell(bestBid.price, 1);
            lastOrderTick_ = state.tick;
            return;
        }

        if (!state.asks.empty() && playerState.mora >= state.asks.front().price) {
            const auto& bestAsk = state.asks.front();
            spdlog::info(
                "Buying from best ask price={} quantity=1 availableMora={} nav={}",
                bestAsk.price,
                playerState.mora,
                playerState.nav
            );
            limitBuy(bestAsk.price, 1);
            lastOrderTick_ = state.tick;
            return;
        }

        spdlog::debug(
            "No market action at tick {} bids={} asks={} availableGold={} availableMora={}",
            state.tick,
            state.bids.size(),
            state.asks.size(),
            playerState.gold,
            playerState.mora
        );
    }

    void onPlayerState(const thuai::PlayerState& state) override {
        spdlog::debug(
            "Portfolio update: mora={} frozenMora={} gold={} frozenGold={} lockedGold={} pendingOrders={}",
            state.mora,
            state.frozenMora,
            state.gold,
            state.frozenGold,
            state.lockedGold,
            state.pendingOrders.size()
        );
    }

    void onNews(const thuai::News& news) override {
        spdlog::info(
            "News [{}] month={} day={} content={}",
            news.newsId,
            news.month,
            news.day,
            news.content
        );
        spdlog::info("Submitting default Long report for news {}", news.newsId);
        submitReport(news.newsId, thuai::Prediction::Long);
    }

    void onReportResult(const thuai::ReportResult& result) override {
        spdlog::info(
            "Report result: newsId={} prediction={} correct={} reward={} change={} submitTick={} settlementTick={}",
            result.newsId,
            result.prediction,
            result.isCorrect,
            result.reward,
            result.actualChange,
            result.submitTick,
            result.settlementTick
        );
    }

    void onStrategyOptions(const thuai::StrategyOptions& options) override {
        if (options.infrastructure.has_value()) {
            spdlog::info("Selecting infrastructure card {}", options.infrastructure->name);
            selectStrategy(options.infrastructure->name);
            return;
        }

        if (options.riskControl.has_value()) {
            spdlog::info("Selecting risk-control card {}", options.riskControl->name);
            selectStrategy(options.riskControl->name);
            return;
        }

        if (options.finTech.has_value()) {
            spdlog::info("Selecting fin-tech card {}", options.finTech->name);
            selectStrategy(options.finTech->name);
            return;
        }

        spdlog::warn("Received strategy options message without any available cards");
    }

    void onTrade(const thuai::TradeNotification& trade) override {
        spdlog::info(
            "Trade notification: tradeId={} orderId={} side={} price={} quantity={} fee={}",
            trade.tradeId,
            trade.orderId,
            trade.side,
            trade.price,
            trade.quantity,
            trade.fee
        );
    }

    void onSkillEffect(const thuai::SkillEffect& effect) override {
        spdlog::info(
            "Skill effect: skill={} source={} target={} description={}",
            effect.skillName,
            effect.sourcePlayer,
            effect.targetPlayer.value_or("none"),
            effect.description
        );
    }

    void onError(int code, const std::string& message) override {
        spdlog::error("Server error code={} message={}", code, message);
    }

private:
    static constexpr int kOrderCooldownTicks = 25;
    int lastOrderTick_ = -999;
};

} // namespace

auto createAgent(std::string token, std::string serverUrl) -> std::unique_ptr<thuai::Agent> {
    return std::make_unique<MyAgent>(std::move(token), std::move(serverUrl));
}
