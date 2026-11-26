import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("../services/api", () => {
  const api = {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  };
  return { default: api };
});

import api from "../services/api";
import StudentPortal from "../pages/StudentPortal";

const portal = {
  student: { name: "Ari Student", student_id: "STU-001", department: "Computing", semester: 1, section: "A", course: "Computer Science", academic_year: "2026-2027" },
  attendance: { percentage: 100, present_sessions: 2, total_sessions: 2, absent_sessions: 0, records: [] },
  subjects: [],
  timetable: [],
  exams: [],
  assignments: [
    { id: 7, title: "Lab record", description: "Write up", subject: "Programming", subject_code: "CS101", faculty: "Dr Rao", due_at: "2026-12-01T10:00:00Z", max_marks: 25, submission: null },
    { id: 8, title: "Graded task", subject: "Programming", subject_code: "CS101", faculty: "Dr Rao", due_at: "2026-12-02T10:00:00Z", max_marks: 10, submission: { id: 99, submitted_at: "2026-11-20T10:00:00Z", marks: 8, feedback: "Good" } },
  ],
  jobs: [
    { id: 5, title: "Engineer", company: "Acme", description: "Build things", eligibility: "Final year", package: "10 LPA", deadline: "2026-12-15", application: null },
    { id: 6, title: "Analyst", company: "Globex", package: "8 LPA", deadline: null, application: { id: 77, status: "shortlisted", applied_on: "2026-11-21T10:00:00Z", remarks: "Strong" } },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  api.get.mockResolvedValue({ data: portal });
  api.post.mockResolvedValue({ data: { id: 1 } });
});

describe("StudentPortal", () => {
  it("renders assignments and placement opportunities", async () => {
    render(<StudentPortal />);

    expect(await screen.findByText("Lab record")).toBeInTheDocument();
    expect(screen.getByText("Graded task")).toBeInTheDocument();
    expect(screen.getByText("Engineer")).toBeInTheDocument();
    expect(screen.getByText("Analyst")).toBeInTheDocument();
    expect(screen.getByText(/Submitted/)).toBeInTheDocument();
    expect(screen.getByText(/shortlisted/)).toBeInTheDocument();
  });

  it("submits an assignment without a file", async () => {
    const user = userEvent.setup();
    render(<StudentPortal />);

    await screen.findByText("Lab record");
    const submitButtons = screen.getAllByRole("button", { name: /^submit$/i });
    await user.click(submitButtons[0]);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/submissions/", { assignment: 7 });
    });
    expect(await screen.findByText(/Assignment submitted successfully/i)).toBeInTheDocument();
  });

  it("applies to a job posting", async () => {
    const user = userEvent.setup();
    render(<StudentPortal />);

    await screen.findByText("Engineer");
    const applyButtons = screen.getAllByRole("button", { name: /^apply$/i });
    await user.click(applyButtons[0]);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/placement-applications/", { job: 5 });
    });
    expect(await screen.findByText(/Application submitted successfully/i)).toBeInTheDocument();
  });

  it("shows an error when submission fails", async () => {
    api.post.mockRejectedValueOnce({ response: { data: { detail: "Already submitted" } } });
    const user = userEvent.setup();
    render(<StudentPortal />);

    await screen.findByText("Lab record");
    const submitButtons = screen.getAllByRole("button", { name: /^submit$/i });
    await user.click(submitButtons[0]);

    expect(await screen.findByText("Already submitted")).toBeInTheDocument();
  });

  it("shows an error when application fails", async () => {
    api.post.mockRejectedValueOnce({ response: { data: { detail: "Deadline passed" } } });
    const user = userEvent.setup();
    render(<StudentPortal />);

    await screen.findByText("Engineer");
    const applyButtons = screen.getAllByRole("button", { name: /^apply$/i });
    await user.click(applyButtons[0]);

    expect(await screen.findByText("Deadline passed")).toBeInTheDocument();
  });
});