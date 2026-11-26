import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("../services/api", () => {
  const api = {
    get: vi.fn(),
    getAll: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  };
  return { default: api };
});

import api from "../services/api";
import ModuleManager from "../pages/ModuleManager";

const departments = [
  { id: 1, code: "CSE", name: "Computer Science", student_count: 3, is_active: true },
  { id: 2, code: "ECE", name: "Electronics", student_count: 0, is_active: false },
];

beforeEach(() => {
  vi.clearAllMocks();
  api.getAll.mockResolvedValue([]);
  api.get.mockResolvedValue({ data: { results: departments, count: 2 } });
});

describe("ModuleManager", () => {
  it("renders module metadata and rows from the API", async () => {
    render(<ModuleManager moduleKey="departments" canManage />);

    expect(screen.getByRole("heading", { name: "Departments" })).toBeInTheDocument();
    expect(await screen.findByText("Computer Science")).toBeInTheDocument();
    expect(screen.getByText("CSE")).toBeInTheDocument();
    expect(screen.getByText("Page 1 of 1")).toBeInTheDocument();
  });

  it("hides create and row actions without manage permission", async () => {
    render(<ModuleManager moduleKey="departments" canManage={false} />);

    await screen.findByText("Computer Science");
    expect(screen.queryByRole("button", { name: /add department/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /edit departments record/i })).not.toBeInTheDocument();
  });

  it("opens the create form with the module fields", async () => {
    const user = userEvent.setup();
    render(<ModuleManager moduleKey="departments" canManage />);

    await user.click(await screen.findByRole("button", { name: /add department/i }));

    expect(screen.getByLabelText("Department name")).toBeInTheDocument();
    expect(screen.getByLabelText("Department code")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save record/i })).toBeInTheDocument();
  });

  it("creates a record and reloads the table", async () => {
    const user = userEvent.setup();
    api.post.mockResolvedValue({ data: { id: 3 } });
    render(<ModuleManager moduleKey="departments" canManage />);

    await user.click(await screen.findByRole("button", { name: /add department/i }));
    await user.type(screen.getByLabelText("Department name"), "Mechanical");
    await user.type(screen.getByLabelText("Department code"), "MECH");
    await user.click(screen.getByRole("button", { name: /save record/i }));

    expect(api.post).toHaveBeenCalledWith(
      "/departments/",
      expect.objectContaining({ name: "Mechanical", code: "MECH" }),
    );
    expect(screen.queryByLabelText("Department name")).not.toBeInTheDocument();
  });

  it("surfaces a server validation error inside the form", async () => {
    const user = userEvent.setup();
    api.post.mockRejectedValue({ response: { data: { code: ["This code already exists."] } } });
    render(<ModuleManager moduleKey="departments" canManage />);

    await user.click(await screen.findByRole("button", { name: /add department/i }));
    await user.type(screen.getByLabelText("Department name"), "Duplicate");
    await user.type(screen.getByLabelText("Department code"), "CSE");
    await user.click(screen.getByRole("button", { name: /save record/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("code: This code already exists.");
  });

  it("deletes a record after confirmation", async () => {
    const user = userEvent.setup();
    api.delete.mockResolvedValue({});
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<ModuleManager moduleKey="departments" canManage />);

    const deleteButtons = await screen.findAllByRole("button", { name: /delete departments record/i });
    await user.click(deleteButtons[0]);

    expect(confirm).toHaveBeenCalled();
    expect(api.delete).toHaveBeenCalledWith("/departments/1/");
    expect(screen.queryByText("Computer Science")).not.toBeInTheDocument();
    confirm.mockRestore();
  });
});
