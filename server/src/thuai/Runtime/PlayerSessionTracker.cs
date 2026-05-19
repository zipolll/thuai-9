namespace Thuai.Runtime;

public record PlayerSessionSnapshot(
    string Token,
    bool IsConnected,
    bool RemovedFromGame,
    int ConnectionCount,
    int DisconnectCount,
    int? LastConnectedTick,
    int? LastDisconnectedTick,
    int? LastRemovedTick,
    int DisconnectedForTicks);

public sealed class PlayerSessionTracker
{
    private readonly object _lock = new();
    private readonly Dictionary<string, PlayerSessionState> _states = new();
    private readonly int _disconnectRetentionTicks;

    public PlayerSessionTracker(int disconnectRetentionTicks)
    {
        _disconnectRetentionTicks = Math.Max(0, disconnectRetentionTicks);
    }

    public void MarkConnected(string token, int currentTick)
    {
        if (string.IsNullOrWhiteSpace(token))
            return;

        lock (_lock)
        {
            var state = GetOrCreateState(token);
            state.IsConnected = true;
            state.RemovedFromGame = false;
            state.ConnectionCount++;
            state.LastConnectedTick = currentTick;
        }
    }

    public void SeedDisconnected(string token, int currentTick)
    {
        if (string.IsNullOrWhiteSpace(token))
            return;

        lock (_lock)
        {
            var state = GetOrCreateState(token);
            state.IsConnected = false;
            state.RemovedFromGame = false;
            state.LastDisconnectedTick = currentTick;
        }
    }

    public void MarkDisconnected(string token, int currentTick)
    {
        if (string.IsNullOrWhiteSpace(token))
            return;

        lock (_lock)
        {
            var state = GetOrCreateState(token);
            state.IsConnected = false;
            state.DisconnectCount++;
            state.LastDisconnectedTick = currentTick;
        }
    }

    public List<string> CollectExpiredTokens(int currentTick)
    {
        if (_disconnectRetentionTicks <= 0)
            return [];

        lock (_lock)
        {
            var expired = new List<string>();
            foreach (var (token, state) in _states)
            {
                if (state.IsConnected || state.RemovedFromGame || !state.LastDisconnectedTick.HasValue)
                    continue;

                if (currentTick - state.LastDisconnectedTick.Value < _disconnectRetentionTicks)
                    continue;

                state.RemovedFromGame = true;
                state.LastRemovedTick = currentTick;
                expired.Add(token);
            }

            return expired;
        }
    }

    public IReadOnlyList<PlayerSessionSnapshot> GetSnapshots(int currentTick)
    {
        lock (_lock)
        {
            return _states
                .Select(entry =>
                {
                    var state = entry.Value;
                    int disconnectedForTicks = !state.IsConnected && state.LastDisconnectedTick.HasValue
                        ? Math.Max(0, currentTick - state.LastDisconnectedTick.Value)
                        : 0;

                    return new PlayerSessionSnapshot(
                        entry.Key,
                        state.IsConnected,
                        state.RemovedFromGame,
                        state.ConnectionCount,
                        state.DisconnectCount,
                        state.LastConnectedTick,
                        state.LastDisconnectedTick,
                        state.LastRemovedTick,
                        disconnectedForTicks);
                })
                .OrderBy(snapshot => snapshot.Token, StringComparer.Ordinal)
                .ToList();
        }
    }

    private PlayerSessionState GetOrCreateState(string token)
    {
        if (_states.TryGetValue(token, out var state))
            return state;

        state = new PlayerSessionState();
        _states[token] = state;
        return state;
    }

    private sealed class PlayerSessionState
    {
        public bool IsConnected { get; set; }
        public bool RemovedFromGame { get; set; }
        public int ConnectionCount { get; set; }
        public int DisconnectCount { get; set; }
        public int? LastConnectedTick { get; set; }
        public int? LastDisconnectedTick { get; set; }
        public int? LastRemovedTick { get; set; }
    }
}
