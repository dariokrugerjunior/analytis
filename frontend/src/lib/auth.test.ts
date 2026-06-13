import { beforeEach, describe, expect, it } from "vitest";
import { clearApiKey, getApiKey, setApiKey } from "./auth";

beforeEach(() => {
  localStorage.clear();
});

describe("auth", () => {
  it("stores and reads api key", () => {
    setApiKey("abc-123");
    expect(getApiKey()).toBe("abc-123");
  });
  it("clear removes key", () => {
    setApiKey("x");
    clearApiKey();
    expect(getApiKey()).toBeNull();
  });
  it("returns null when nothing stored", () => {
    expect(getApiKey()).toBeNull();
  });
});
