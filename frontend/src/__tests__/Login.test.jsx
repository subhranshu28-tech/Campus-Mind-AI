import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

const auth = vi.hoisted(() => ({ login: vi.fn() }));

vi.mock("../context/AuthContext", () => ({ useAuth: () => auth }));

import Login from "../pages/Login";

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Login", () => {
  it("submits the entered credentials", async () => {
    auth.login.mockResolvedValue();
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText("Username"), "faculty1");
    await user.type(screen.getByLabelText("Password"), "Demo-pass-123");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(auth.login).toHaveBeenCalledWith("faculty1", "Demo-pass-123");
  });

  it("shows the server error when sign-in fails", async () => {
    auth.login.mockRejectedValue({ response: { data: { detail: "Invalid credentials." } } });
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText("Username"), "faculty1");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid credentials.");
  });

  it("disables the button while signing in", async () => {
    let resolveLogin;
    auth.login.mockReturnValue(new Promise((resolve) => { resolveLogin = resolve; }));
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText("Username"), "faculty1");
    await user.type(screen.getByLabelText("Password"), "Demo-pass-123");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(screen.getByRole("button", { name: /signing in/i })).toBeDisabled();
    resolveLogin();
    expect(await screen.findByRole("button", { name: /^sign in$/i })).toBeEnabled();
  });
});
