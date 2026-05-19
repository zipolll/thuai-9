import assert from "node:assert/strict";
import {
  DEFAULT_LOCALHOST_PORT,
  DEFAULT_SERVER_URL,
  REMOTE_SERVER_URL,
  buildServerUrl,
  normalizeLocalhostPort,
  normalizeServerUrl,
  openWebSocket,
  parseServerChoice,
} from "../src/connection.js";
import { routeFromLocation } from "../src/store.js";

testDefaultServerUrl();
testNormalizeLocalhostPort();
testParseServerChoiceSupportsOnlyRemoteOrLocalhost();
testBuildServerUrlRestrictsHosts();
testNormalizeServerUrlRestrictsHosts();
testOpenWebSocketUsesNormalizedServerUrl();
testRouteFromLocationPreservesSupportedServerChoices();
testRouteFromLocationPreservesLocalhostPort();
testRouteFromLocationRejectsUnsupportedHosts();

function testDefaultServerUrl() {
  assert.equal(DEFAULT_LOCALHOST_PORT, "14514");
  assert.equal(DEFAULT_SERVER_URL, "ws://localhost:14514");
  assert.equal(REMOTE_SERVER_URL, "ws://59.66.135.18:14514");
}

function testNormalizeLocalhostPort() {
  assert.equal(normalizeLocalhostPort("12345"), "12345");
  assert.equal(normalizeLocalhostPort("0"), DEFAULT_LOCALHOST_PORT);
  assert.equal(normalizeLocalhostPort("70000"), DEFAULT_LOCALHOST_PORT);
  assert.equal(normalizeLocalhostPort("abc"), DEFAULT_LOCALHOST_PORT);
}

function testParseServerChoiceSupportsOnlyRemoteOrLocalhost() {
  assert.deepEqual(parseServerChoice("59.66.135.18:14514"), {
    mode: "remote",
    localhostPort: DEFAULT_LOCALHOST_PORT,
  });
  assert.deepEqual(parseServerChoice(REMOTE_SERVER_URL), {
    mode: "remote",
    localhostPort: DEFAULT_LOCALHOST_PORT,
  });
  assert.deepEqual(parseServerChoice("localhost:23456"), {
    mode: "localhost",
    localhostPort: "23456",
  });
  assert.deepEqual(parseServerChoice("23456"), {
    mode: "localhost",
    localhostPort: "23456",
  });
}

function testBuildServerUrlRestrictsHosts() {
  assert.equal(buildServerUrl("localhost", "23456"), "ws://localhost:23456");
  assert.equal(buildServerUrl("remote", "23456"), REMOTE_SERVER_URL);
}

function testNormalizeServerUrlRestrictsHosts() {
  assert.equal(normalizeServerUrl(DEFAULT_SERVER_URL), DEFAULT_SERVER_URL);
  assert.equal(normalizeServerUrl(REMOTE_SERVER_URL), REMOTE_SERVER_URL);
  assert.equal(normalizeServerUrl("59.66.135.18:14514"), REMOTE_SERVER_URL);
  assert.equal(normalizeServerUrl("localhost:23456"), "ws://localhost:23456");
  assert.equal(normalizeServerUrl("example.com:14514"), DEFAULT_SERVER_URL);
  assert.equal(normalizeServerUrl("wss://example.com/socket"), DEFAULT_SERVER_URL);
  assert.equal(normalizeServerUrl(""), DEFAULT_SERVER_URL);
}

function testOpenWebSocketUsesNormalizedServerUrl() {
  class FakeWebSocket {
    constructor(url) {
      this.url = url;
    }
  }

  const localSocket = openWebSocket("localhost:14514", FakeWebSocket);
  const remoteSocket = openWebSocket("59.66.135.18:14514", FakeWebSocket);

  assert.equal(localSocket.url, DEFAULT_SERVER_URL);
  assert.equal(remoteSocket.url, REMOTE_SERVER_URL);
}

function testRouteFromLocationPreservesSupportedServerChoices() {
  const route = routeFromLocation({
    search: `?mode=observer&server=${encodeURIComponent(REMOTE_SERVER_URL)}`,
    pathname: "/",
  });

  assert.equal(route.role, "observer");
  assert.equal(route.server, REMOTE_SERVER_URL);
  assert.equal(route.localhostPort, DEFAULT_LOCALHOST_PORT);
}

function testRouteFromLocationPreservesLocalhostPort() {
  const route = routeFromLocation({
    search: `?mode=observer&server=${encodeURIComponent("ws://localhost:23456")}`,
    pathname: "/",
  });

  assert.equal(route.server, "ws://localhost:23456");
  assert.equal(route.localhostPort, "23456");
}

function testRouteFromLocationRejectsUnsupportedHosts() {
  const route = routeFromLocation({
    search: `?mode=observer&server=${encodeURIComponent("ws://example.com:14514")}`,
    pathname: "/",
  });

  assert.equal(route.server, DEFAULT_SERVER_URL);
  assert.equal(route.localhostPort, DEFAULT_LOCALHOST_PORT);
}
