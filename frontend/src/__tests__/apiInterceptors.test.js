import { describe, it, expect, vi, beforeEach } from "vitest";

const captured = vi.hoisted(() => ({ request: null, response: null }));

vi.mock("axios", () => {
  const instance = vi.fn();
  instance.get = vi.fn();
  instance.post = vi.fn();
  instance.defaults = { baseURL: "/api" };
  instance.interceptors = {
    request: { use: vi.fn((handler) => { captured.request = handler; }) },
    response: { use: vi.fn((_success, errorHandler) => { captured.response = errorHandler; }) },
  };
  return { default: { create: vi.fn(() => instance), post: vi.fn() } };
});

import axios from "axios";
import api from "../services/api";

beforeEach(() => {
  sessionStorage.clear();
  vi.clearAllMocks();
});

describe("api interceptors", () => {
  it("attaches the stored access token to requests", () => {
    sessionStorage.setItem("campus.access", "access-1");
    const config = captured.request({ headers: {} });
    expect(config.headers.Authorization).toBe("Bearer access-1");
  });

  it("leaves anonymous requests untouched", () => {
    const config = captured.request({ headers: {} });
    expect(config.headers.Authorization).toBeUndefined();
  });

  it("refreshes the access token on 401 and retries once", async () => {
    sessionStorage.setItem("campus.access", "expired");
    sessionStorage.setItem("campus.refresh", "refresh-1");
    axios.post.mockResolvedValue({ data: { access: "access-2", refresh: "refresh-2" } });
    api.mockResolvedValue({ data: { ok: true } });

    const request = { url: "/students/", headers: {}, _retried: false };
    const result = await captured.response({ config: request, response: { status: 401 } });

    expect(axios.post).toHaveBeenCalledWith("/api/auth/token/refresh/", { refresh: "refresh-1" });
    expect(sessionStorage.getItem("campus.access")).toBe("access-2");
    expect(sessionStorage.getItem("campus.refresh")).toBe("refresh-2");
    expect(request._retried).toBe(true);
    expect(api).toHaveBeenCalledWith(request);
    expect(result).toEqual({ data: { ok: true } });
  });

  it("does not refresh when a request was already retried", async () => {
    sessionStorage.setItem("campus.refresh", "refresh-1");
    axios.post.mockResolvedValue({ data: { access: "access-2" } });
    const request = { url: "/students/", headers: {}, _retried: true };

    await expect(captured.response({ config: request, response: { status: 401 } })).rejects.toMatchObject({
      response: { status: 401 },
    });
    expect(axios.post).not.toHaveBeenCalled();
  });

  it("does not retry the token endpoint itself", async () => {
    sessionStorage.setItem("campus.refresh", "refresh-1");
    api.mockResolvedValue({ data: {} });
    const request = { url: "/auth/token/refresh/", headers: {} };

    await expect(captured.response({ config: request, response: { status: 401 } })).rejects.toMatchObject({
      response: { status: 401 },
    });
    expect(axios.post).not.toHaveBeenCalled();
  });

  it("clears the session and signals expiry when refresh fails", async () => {
    sessionStorage.setItem("campus.access", "expired");
    sessionStorage.setItem("campus.refresh", "refresh-1");
    axios.post.mockRejectedValue(new Error("refresh denied"));
    const expired = vi.fn();
    window.addEventListener("campus:session-expired", expired);

    const request = { url: "/students/", headers: {} };
    await expect(captured.response({ config: request, response: { status: 401 } })).rejects.toBeTruthy();

    expect(sessionStorage.getItem("campus.access")).toBeNull();
    expect(sessionStorage.getItem("campus.refresh")).toBeNull();
    expect(expired).toHaveBeenCalledTimes(1);
    window.removeEventListener("campus:session-expired", expired);
  });

  it("passes non-401 errors through unchanged", async () => {
    const error = { config: { url: "/x/", headers: {} }, response: { status: 403 } };
    await expect(captured.response(error)).rejects.toBe(error);
    expect(axios.post).not.toHaveBeenCalled();
  });
});
