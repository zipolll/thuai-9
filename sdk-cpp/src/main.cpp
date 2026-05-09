#include "logic.hpp"

#include <cstdlib>
#include <optional>
#include <string>

#include <cxxopts.hpp>
#include <spdlog/cfg/env.h>
#include <spdlog/spdlog.h>

namespace {

// NOLINTBEGIN(concurrency-mt-unsafe)
auto envValue(const char* key) -> std::optional<std::string> {
    if (const char* value = std::getenv(key); value != nullptr) {
        return std::string(value);
    }
    return std::nullopt;
}
// NOLINTEND(concurrency-mt-unsafe)

struct RuntimeConfig {
    std::string token = "player1";
    std::string serverUrl = "ws://localhost:14514";
};

auto resolveConfig(int argc, char** argv) -> std::optional<RuntimeConfig> {
    RuntimeConfig config;
    bool hasTokenEnv = false;
    bool hasServerEnv = false;

    if (const auto token = envValue("TOKEN"); token.has_value()) {
        config.token = *token;
        hasTokenEnv = true;
    }
    if (const auto server = envValue("SERVER"); server.has_value()) {
        config.serverUrl = *server;
        hasServerEnv = true;
    }

    if (hasTokenEnv && hasServerEnv) {
        return config;
    }

    cxxopts::Options options("agent", "THUAI-9 C++ agent");
    options.add_options()
        ("token", "Agent token", cxxopts::value<std::string>())
        ("server", "WebSocket server URL", cxxopts::value<std::string>())
        ("h,help", "Show help");

    const auto result = options.parse(argc, argv);
    if (result.contains("help")) {
        spdlog::info("{}", options.help());
        return std::nullopt;
    }

    if (!hasTokenEnv && result.contains("token")) {
        config.token = result["token"].as<std::string>();
    }
    if (!hasServerEnv && result.contains("server")) {
        config.serverUrl = result["server"].as<std::string>();
    }

    return config;
}

auto maskToken(const std::string& token) -> std::string {
    if (token.size() <= 4U) {
        return std::string(token.size(), '*');
    }
    return token.substr(0, 2) + "***" + token.substr(token.size() - 2);
}

void configureLogging() {
    spdlog::set_pattern("[%Y-%m-%d %H:%M:%S.%e] [%^%l%$] [%n] %v");
    spdlog::set_level(spdlog::level::info);
    spdlog::cfg::load_env_levels();
}

} // namespace

auto main(int argc, char** argv) -> int {
    configureLogging();

    const auto config = resolveConfig(argc, argv);
    if (!config.has_value()) {
        return 0;
    }

    spdlog::info(
        "Starting THUAI agent for token={} server={}",
        maskToken(config->token),
        config->serverUrl
    );

    auto agent = createAgent(config->token, config->serverUrl);
    agent->run();
    return 0;
}
