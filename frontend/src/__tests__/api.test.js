import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("axios", () => {
  const instance = {
    get: vi.fn(),
    post: vi.fn(),
    defaults: { baseURL: "/api" },
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  };
  return { default: { create: () => instance, post: vi.fn() } };
});

describe("api.getAll", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("aggregates every page of a paginated endpoint", async () => {
    const { default: api } = await import("../services/api");
    api.get
      .mockResolvedValueOnce({ data: { results: [{ id: 1 }, { id: 2 }], next: "page2" } })
      .mockResolvedValueOnce({ data: { results: [{ id: 3 }], next: null } });
    const rows = await api.getAll("/items/");
    expect(rows).toEqual([{ id: 1 }, { id: 2 }, { id: 3 }]);
    expect(api.get).toHaveBeenCalledTimes(2);
  });

  it("returns a bare array response unchanged", async () => {
    const { default: api } = await import("../services/api");
    api.get.mockResolvedValueOnce({ data: [{ id: 9 }] });
    expect(await api.getAll("/items/")).toEqual([{ id: 9 }]);
  });
});
