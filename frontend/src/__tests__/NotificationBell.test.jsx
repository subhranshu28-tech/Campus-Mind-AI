import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("../services/api", () => {
  const api = { get: vi.fn(), post: vi.fn() };
  return { default: api };
});

import api from "../services/api";
import NotificationBell from "../pages/NotificationBell";

const notifications = [
  { id: 1, title: "Timetable published", message: "The new timetable is live.", is_read: false, created_at: "2026-11-26T09:00:00Z" },
  { id: 2, title: "Fee reminder", message: "Fees are due Friday.", is_read: true, created_at: "2026-11-25T09:00:00Z" },
];

beforeEach(() => {
  vi.clearAllMocks();
  api.get.mockResolvedValue({ data: { results: notifications, unread: 2 } });
  api.post.mockResolvedValue({ data: {} });
});

describe("NotificationBell", () => {
  it("shows the unread badge and notification list", async () => {
    const user = userEvent.setup();
    render(<NotificationBell />);

    await screen.findByText("2");
    await user.click(screen.getByRole("button", { name: "Notifications" }));

    expect(screen.getByText("Timetable published")).toBeInTheDocument();
    expect(screen.getByText("Fee reminder")).toBeInTheDocument();
  });

  it("marks all notifications read and reloads", async () => {
    const user = userEvent.setup();
    render(<NotificationBell />);

    await screen.findByText("2");
    await user.click(screen.getByRole("button", { name: "Notifications" }));
    await user.click(screen.getByRole("button", { name: /mark all read/i }));

    expect(api.post).toHaveBeenCalledWith("/notifications/read-all/");
    // Mount load, open-panel load, and the reload after marking read.
    expect(api.get).toHaveBeenCalledTimes(3);
  });

  it("shows an empty state when nothing is unread", async () => {
    api.get.mockResolvedValue({ data: { results: [], unread: 0 } });
    const user = userEvent.setup();
    render(<NotificationBell />);

    await user.click(screen.getByRole("button", { name: "Notifications" }));
    expect(screen.getByText("You're all caught up.")).toBeInTheDocument();
  });

  it("swallows API failures so the header keeps rendering", async () => {
    api.get.mockRejectedValue(new Error("network"));
    render(<NotificationBell />);

    expect(screen.getByRole("button", { name: "Notifications" })).toBeInTheDocument();
  });
});
