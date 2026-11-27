import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../services/api", () => {
  const api = {
    get: vi.fn(() => Promise.resolve({ data: { results: [], count: 0 } })),
    getAll: vi.fn(() => Promise.resolve([])),
    post: vi.fn(() => Promise.resolve({ data: {} })),
    patch: vi.fn(() => Promise.resolve({ data: {} })),
    delete: vi.fn(() => Promise.resolve({ data: {} })),
  };
  return { default: api };
});

import ModuleManager from "../pages/ModuleManager";

const moduleKeys = [
  "departments",
  "students",
  "faculty",
  "academic-years",
  "courses",
  "semesters",
  "sections",
  "subjects",
  "attendance",
  "classrooms",
  "teaching-assignments",
  "faculty-availability",
  "exam-schedules",
  "notices",
  "events",
  "assignments",
  "fee-structures",
  "invoices",
  "payments",
  "books",
  "book-issues",
  "hostels",
  "hostel-rooms",
  "hostel-allocations",
  "transport-routes",
  "vehicles",
  "student-transport",
  "companies",
  "job-postings",
  "placement-applications",
];

describe("ModuleManager", () => {
  it.each(moduleKeys)("renders %s without crashing", async (moduleKey) => {
    const { unmount } = render(<ModuleManager moduleKey={moduleKey} canManage />);
    expect(await screen.findByText(/Campus records/i)).toBeInTheDocument();
    unmount();
  });
});
