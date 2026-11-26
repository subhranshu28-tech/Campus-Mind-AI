import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ErrorBoundary from "../components/ErrorBoundary";

function Boom() {
  throw new Error("kaboom");
}

describe("ErrorBoundary", () => {
  it("renders a recovery screen when a child throws", () => {
    // React logs the error to console; silence it for clean output.
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    expect(screen.getByText(/kaboom/i)).toBeInTheDocument();
    spy.mockRestore();
  });
});
