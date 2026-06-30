import assert from "node:assert/strict";
import test from "node:test";

import { isAllowedBackendHost, resolveBackendUrl } from "./backendClient";

const backendOrigin = "https://api.noirtools.example";

test("resolveBackendUrl allows relative backend paths", () => {
  const url = resolveBackendUrl("/api/data", backendOrigin);

  assert.equal(url.toString(), `${backendOrigin}/api/data`);
});

test("resolveBackendUrl accepts absolute URLs matching backend origin", () => {
  const url = resolveBackendUrl(`${backendOrigin}/status`, backendOrigin);

  assert.equal(url.toString(), `${backendOrigin}/status`);
});

test("resolveBackendUrl rejects absolute URLs pointing to a foreign origin", () => {
  assert.throws(
    () => resolveBackendUrl("https://malicious.example/api/data", backendOrigin),
    /must target the backend origin/,
  );
});

test("resolveBackendUrl rejects protocol-relative URLs", () => {
  assert.throws(() => resolveBackendUrl("//malicious.example/api/data", backendOrigin));
});

test("host validation fails for lookalike domains", () => {
  const backendUrl = new URL(backendOrigin);
  const malicious = new URL("https://api.noirtools.example.attacker.com/steal");

  assert.equal(isAllowedBackendHost(malicious, backendUrl), false);
});
