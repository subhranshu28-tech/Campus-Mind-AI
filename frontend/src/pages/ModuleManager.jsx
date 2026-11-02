import { useEffect, useMemo, useState } from "react";
import { ArrowDownUp, Plus, Search, Trash2, Pencil, X } from "lucide-react";
import api from "../services/api";

const modules = {
  departments: {
    title: "Departments", description: "Manage campus departments and their active status.",
    endpoint: "departments", orderingField: "name", filters: [{ name: "is_active", label: "Status", options: [["true", "Active"], ["false", "Inactive"]] }], columns: [["code", "Code"], ["name", "Department"], ["student_count", "Students"], ["is_active", "Status"]],
    fields: [
      { name: "name", label: "Department name", required: true },
      { name: "code", label: "Department code", required: true },
      { name: "head", label: "Department head", type: "select", endpoint: "faculty", optionLabel: "user_name", optionValue: "user.id", optional: true, numeric: true },
      { name: "is_active", label: "Active", type: "checkbox", defaultValue: true },
    ],
  },
  students: {
    title: "Students", description: "Create student profiles, campus accounts, and academic allocations.",
    endpoint: "students", orderingField: "student_id", filters: [{ name: "department", label: "Department", endpoint: "departments", optionLabel: "name" }, { name: "semester", label: "Semester", options: Array.from({ length: 12 }, (_, index) => [String(index + 1), `Semester ${index + 1}`]) }], columns: [["student_id", "Student ID"], ["user_name", "Student"], ["user.email", "Email"], ["department_name", "Department"], ["semester", "Semester"], ["section_name", "Section"]],
    fields: [
      { name: "user.username", label: "Account username", required: true },
      { name: "user.email", label: "Email address", type: "email", required: true },
      { name: "user.first_name", label: "First name", required: true },
      { name: "user.last_name", label: "Last name", required: true },
      { name: "user.password", label: "Initial password", type: "password", required: true, editOptional: true },
      { name: "student_id", label: "Student ID", required: true },
      { name: "department", label: "Department", type: "select", endpoint: "departments", optionLabel: "name", required: true, numeric: true },
      { name: "semester", label: "Semester number", type: "number", min: 1, max: 12, required: true },
      { name: "section", label: "Section", type: "select", endpoint: "sections", optionLabel: "semester_label", optional: true, numeric: true },
      { name: "enrolled_on", label: "Enrollment date", type: "date", required: true },
    ],
  },
  faculty: {
    title: "Faculty", description: "Manage faculty profiles and secure staff accounts.",
    endpoint: "faculty", orderingField: "employee_id", filters: [{ name: "department", label: "Department", endpoint: "departments", optionLabel: "name" }], columns: [["employee_id", "Employee ID"], ["user_name", "Faculty member"], ["user.email", "Email"], ["department_name", "Department"], ["qualification", "Qualification"], ["experience_years", "Experience"]],
    fields: [
      { name: "user.username", label: "Account username", required: true },
      { name: "user.email", label: "Email address", type: "email", required: true },
      { name: "user.first_name", label: "First name", required: true },
      { name: "user.last_name", label: "Last name", required: true },
      { name: "user.password", label: "Initial password", type: "password", required: true, editOptional: true },
      { name: "employee_id", label: "Employee ID", required: true },
      { name: "department", label: "Department", type: "select", endpoint: "departments", optionLabel: "name", required: true, numeric: true },
      { name: "qualification", label: "Qualification" },
      { name: "experience_years", label: "Experience (years)", type: "number", min: 0, required: true },
    ],
  },
  "academic-years": {
    title: "Academic years", description: "Set academic session date ranges and the current active year.",
    endpoint: "academic-years", orderingField: "starts_on", filters: [{ name: "is_active", label: "Status", options: [["true", "Active"], ["false", "Inactive"]] }], columns: [["name", "Academic year"], ["starts_on", "Starts"], ["ends_on", "Ends"], ["is_active", "Active"]],
    fields: [
      { name: "name", label: "Name", placeholder: "2026–2027", required: true },
      { name: "starts_on", label: "Start date", type: "date", required: true },
      { name: "ends_on", label: "End date", type: "date", required: true },
      { name: "is_active", label: "Active academic year", type: "checkbox" },
    ],
  },
  courses: {
    title: "Courses", description: "Configure programs of study under each department.",
    endpoint: "courses", orderingField: "code", filters: [{ name: "department", label: "Department", endpoint: "departments", optionLabel: "name" }], columns: [["code", "Code"], ["name", "Course"], ["department_name", "Department"], ["duration_years", "Duration"], ["is_active", "Active"]],
    fields: [
      { name: "department", label: "Department", type: "select", endpoint: "departments", optionLabel: "name", required: true, numeric: true },
      { name: "name", label: "Course name", required: true },
      { name: "code", label: "Course code", required: true },
      { name: "duration_years", label: "Duration (years)", type: "number", min: 1, max: 10, defaultValue: 4, required: true },
      { name: "is_active", label: "Active", type: "checkbox", defaultValue: true },
    ],
  },
  semesters: {
    title: "Semesters", description: "Link course semesters to academic years.",
    endpoint: "semesters", orderingField: "number", filters: [{ name: "course", label: "Course", endpoint: "courses", optionLabel: "name" }, { name: "academic_year", label: "Academic year", endpoint: "academic-years", optionLabel: "name" }], columns: [["course_name", "Course"], ["number", "Semester"], ["academic_year_name", "Academic year"]],
    fields: [
      { name: "course", label: "Course", type: "select", endpoint: "courses", optionLabel: "name", required: true, numeric: true },
      { name: "academic_year", label: "Academic year", type: "select", endpoint: "academic-years", optionLabel: "name", required: true, numeric: true },
      { name: "number", label: "Semester number", type: "number", min: 1, max: 12, required: true },
    ],
  },
  sections: {
    title: "Sections", description: "Create class sections and define their enrollment capacity.",
    endpoint: "sections", orderingField: "name", filters: [{ name: "semester", label: "Semester", endpoint: "semesters", optionLabel: "course_name" }], columns: [["semester_label", "Semester"], ["name", "Section"], ["capacity", "Capacity"]],
    fields: [
      { name: "semester", label: "Semester", type: "select", endpoint: "semesters", optionLabel: "course_name", required: true, numeric: true },
      { name: "name", label: "Section name", placeholder: "A", required: true },
      { name: "capacity", label: "Capacity", type: "number", min: 1, defaultValue: 60, required: true },
    ],
  },
  subjects: {
    title: "Subjects", description: "Define subjects, credits, and laboratory requirements.",
    endpoint: "subjects", orderingField: "code", filters: [{ name: "course", label: "Course", endpoint: "courses", optionLabel: "name" }], columns: [["code", "Code"], ["name", "Subject"], ["course_name", "Course"], ["semester_label", "Semester"], ["credits", "Credits"], ["is_lab", "Laboratory"]],
    fields: [
      { name: "course", label: "Course", type: "select", endpoint: "courses", optionLabel: "name", required: true, numeric: true },
      { name: "semester", label: "Semester", type: "select", endpoint: "semesters", optionLabel: "course_name", required: true, numeric: true },
      { name: "code", label: "Subject code", required: true },
      { name: "name", label: "Subject name", required: true },
      { name: "credits", label: "Credits", type: "number", min: 1, max: 30, defaultValue: 3, required: true },
      { name: "is_lab", label: "Laboratory subject", type: "checkbox" },
    ],
  },
  attendance: {
    title: "Attendance", description: "Record and correct daily student attendance.",
    endpoint: "attendance", orderingField: "date", filters: [{ name: "student__department", label: "Department", endpoint: "departments", optionLabel: "name" }, { name: "date", label: "Date", type: "date" }, { name: "is_present", label: "Attendance", options: [["true", "Present"], ["false", "Absent"]] }], columns: [["date", "Date"], ["student_id", "Student ID"], ["student_name", "Student"], ["is_present", "Status"], ["recorded_by", "Recorded by"]],
    fields: [
      { name: "student", label: "Student", type: "select", endpoint: "students", optionLabel: "student_id", required: true, numeric: true },
      { name: "date", label: "Attendance date", type: "date", required: true },
      { name: "is_present", label: "Present", type: "checkbox", defaultValue: true },
    ],
  },
  classrooms: {
    title: "Classrooms & labs", description: "Register teaching spaces with capacity and lab capability for smart room allocation.",
    endpoint: "classrooms", orderingField: "code", filters: [{ name: "is_lab", label: "Space type", options: [["true", "Laboratory"], ["false", "Classroom"]] }, { name: "is_active", label: "Status", options: [["true", "Active"], ["false", "Inactive"]] }], columns: [["code", "Room code"], ["name", "Room"], ["capacity", "Capacity"], ["is_lab", "Lab"], ["is_active", "Active"]],
    fields: [
      { name: "name", label: "Room name", required: true },
      { name: "code", label: "Room code", required: true },
      { name: "capacity", label: "Seat capacity", type: "number", min: 1, required: true },
      { name: "is_lab", label: "Laboratory", type: "checkbox" },
      { name: "is_active", label: "Active", type: "checkbox", defaultValue: true },
    ],
  },
  "teaching-assignments": {
    title: "Teaching assignments", description: "Assign each section subject to its qualified faculty member and weekly teaching load.",
    endpoint: "teaching-assignments", orderingField: "periods_per_week", filters: [{ name: "faculty", label: "Faculty", endpoint: "faculty", optionLabel: "user_name" }], columns: [["section_label", "Section"], ["subject_name", "Subject"], ["faculty_name", "Faculty"], ["periods_per_week", "Periods / week"]],
    fields: [
      { name: "section", label: "Class section", type: "select", endpoint: "sections", optionLabel: "semester_label", required: true, numeric: true },
      { name: "subject", label: "Subject", type: "select", endpoint: "subjects", optionLabel: "name", required: true, numeric: true },
      { name: "faculty", label: "Faculty", type: "select", endpoint: "faculty", optionLabel: "user_name", required: true, numeric: true },
      { name: "periods_per_week", label: "Periods each week", type: "number", min: 1, max: 25, defaultValue: 3, required: true },
    ],
  },
  "faculty-availability": {
    title: "Faculty availability", description: "Mark faculty available or unavailable for a weekday and class period. With no available slots marked, faculty are flexible except for blocked slots; once any slots are marked available, only those marked slots can be scheduled.",
    endpoint: "faculty-availability", orderingField: "weekday", filters: [{ name: "faculty", label: "Faculty", endpoint: "faculty", optionLabel: "user_name" }, { name: "weekday", label: "Weekday", options: [["0", "Monday"], ["1", "Tuesday"], ["2", "Wednesday"], ["3", "Thursday"], ["4", "Friday"]] }, { name: "is_available", label: "Availability", options: [["true", "Available"], ["false", "Unavailable"]] }], columns: [["faculty_name", "Faculty"], ["weekday_name", "Weekday"], ["period", "Period"], ["is_available", "Available"]],
    fields: [
      { name: "faculty", label: "Faculty", type: "select", endpoint: "faculty", optionLabel: "user_name", required: true, numeric: true },
      { name: "weekday", label: "Weekday", type: "select", options: [[0, "Monday"], [1, "Tuesday"], [2, "Wednesday"], [3, "Thursday"], [4, "Friday"]], required: true, numeric: true },
      { name: "period", label: "Period", type: "select", options: Array.from({ length: 8 }, (_, index) => [index + 1, `Period ${index + 1}`]), required: true, numeric: true },
      { name: "is_available", label: "Available at this time", type: "checkbox" },
    ],
  },
  "exam-schedules": {
    title: "Examination schedules", description: "Schedule exams with room-capacity, laboratory, invigilator, section, and time-overlap checks.",
    endpoint: "exam-schedules", orderingField: "date", filters: [{ name: "date", label: "Exam date", type: "date" }], columns: [["date", "Date"], ["subject_name", "Subject"], ["section_name", "Section"], ["room_code", "Room"], ["start_period", "Start period"], ["duration_periods", "Periods"], ["invigilator_name", "Invigilator"]],
    fields: [
      { name: "section", label: "Section", type: "select", endpoint: "sections", optionLabel: "semester_label", required: true, numeric: true },
      { name: "subject", label: "Subject", type: "select", endpoint: "subjects", optionLabel: "name", required: true, numeric: true },
      { name: "room", label: "Exam room", type: "select", endpoint: "classrooms", optionLabel: "code", required: true, numeric: true },
      { name: "invigilator", label: "Invigilator", type: "select", endpoint: "faculty", optionLabel: "user_name", optional: true, numeric: true },
      { name: "date", label: "Exam date", type: "date", required: true },
      { name: "start_period", label: "Start period (1–8)", type: "number", min: 1, max: 8, required: true },
      { name: "duration_periods", label: "Duration (periods)", type: "number", min: 1, max: 8, defaultValue: 1, required: true },
    ],
  },
};

function getValue(object, path) {
  return path.split(".").reduce((value, part) => value?.[part], object);
}

function setValue(object, path, value) {
  const parts = path.split(".");
  const last = parts.pop();
  const nested = parts.reduce((target, part) => {
    target[part] ??= {};
    return target[part];
  }, object);
  nested[last] = value;
}

function makeInitial(fields, record) {
  const values = {};
  for (const field of fields) {
    let value = record ? getValue(record, field.name) : field.defaultValue;
    if (field.type === "checkbox") value = Boolean(value);
    if (field.type === "date" && value) value = value.slice(0, 10);
    if (field.name === "user.password" && record) value = "";
    if (value !== undefined && value !== null) setValue(values, field.name, value);
  }
  return values;
}

function displayValue(value, path) {
  if (path === "is_active" || path === "is_present" || path === "is_lab") return value ? "Yes" : "No";
  if (path === "recorded_by") return value ? `#${value}` : "—";
  return value === null || value === undefined || value === "" ? "—" : String(value);
}

function getErrorMessage(error) {
  const data = error.response?.data;
  if (typeof data === "string") return data;
  if (data?.detail) return data.detail;
  if (data) return Object.entries(data).map(([field, messages]) =>
    `${field}: ${Array.isArray(messages) ? messages.join(", ") : JSON.stringify(messages)}`
  ).join(" · ");
  return "Could not connect to the campus API. Please try again.";
}

export default function ModuleManager({ moduleKey, canManage }) {
  const module = modules[moduleKey];
  const [rows, setRows] = useState([]);
  const [related, setRelated] = useState({});
  const [search, setSearch] = useState("");
  const [ordering, setOrdering] = useState("");
  const [filters, setFilters] = useState({});
  const [page, setPage] = useState(1);
  const [pageCount, setPageCount] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({});
  const [formOpen, setFormOpen] = useState(false);

  const relationEndpoints = useMemo(
    () => [...new Set([
      ...module.fields.filter((field) => field.endpoint).map((field) => field.endpoint),
      ...(module.filters || []).filter((filter) => filter.endpoint).map((filter) => filter.endpoint),
    ])],
    [module],
  );

  useEffect(() => {
    let active = true;
    Promise.all(relationEndpoints.map(async (endpoint) => {
      const { data } = await api.get(`/${endpoint}/`);
      return [endpoint, Array.isArray(data) ? data : data.results || []];
    })).then((entries) => {
      if (active) setRelated(Object.fromEntries(entries));
    }).catch((requestError) => {
      if (active) setError(getErrorMessage(requestError));
    });
    return () => { active = false; };
  }, [relationEndpoints]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    const timer = window.setTimeout(() => {
      api.get(`/${module.endpoint}/`, {
        params: { page, search: search || undefined, ordering: ordering || undefined, ...filters },
      }).then(({ data }) => {
        if (!active) return;
        setRows(Array.isArray(data) ? data : data.results || []);
        setPageCount(data.count ? Math.max(1, Math.ceil(data.count / 25)) : 1);
      }).catch((requestError) => {
        if (active) setError(getErrorMessage(requestError));
      }).finally(() => {
        if (active) setLoading(false);
      });
    }, search ? 250 : 0);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [module.endpoint, page, search, ordering, filters]);

  const beginCreate = () => {
    setEditing(null);
    setForm(makeInitial(module.fields));
    setFormOpen(true);
    setFormError("");
  };

  const beginEdit = (record) => {
    setEditing(record);
    setForm(makeInitial(module.fields, record));
    setFormOpen(true);
    setFormError("");
  };

  function updateField(field, rawValue) {
    const next = structuredClone(form);
    let value = rawValue;
    if (field.numeric && rawValue !== "") value = Number(rawValue);
    if (field.type === "number" && rawValue !== "") value = Number(rawValue);
    setValue(next, field.name, value);
    setForm(next);
  }

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    setFormError("");
    const payload = structuredClone(form);
    if (editing && payload.user?.password === "") delete payload.user.password;
    try {
      if (editing) await api.patch(`/${module.endpoint}/${editing.id}/`, payload);
      else await api.post(`/${module.endpoint}/`, payload);
      setEditing(null);
      setForm({});
      setFormOpen(false);
      setPage(1);
      const { data } = await api.get(`/${module.endpoint}/`, {
        params: { page: 1, search: search || undefined, ordering: ordering || undefined, ...filters },
      });
      setRows(Array.isArray(data) ? data : data.results || []);
      setPageCount(data.count ? Math.max(1, Math.ceil(data.count / 25)) : 1);
    } catch (requestError) {
      setFormError(getErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  async function remove(record) {
    if (!window.confirm(`Delete this ${module.title.toLowerCase()} record? This cannot be undone.`)) return;
    setError("");
    try {
      await api.delete(`/${module.endpoint}/${record.id}/`);
      setRows((current) => current.filter((row) => row.id !== record.id));
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    }
  }

  return (
    <section className="content-enter">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div><p className="text-sm font-medium text-blue-700">Campus records</p><h1 className="mt-1 text-2xl font-semibold tracking-tight">{module.title}</h1><p className="mt-1 text-sm text-slate-500">{module.description}</p></div>
        {canManage && <button onClick={beginCreate} className="glass-button inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"><Plus size={16} />Add {module.title.replace(/s$/, "")}</button>}
      </div>

      {error && <div role="alert" className="mb-4 flex items-start justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError("")}><X size={16} /></button></div>}

      {formOpen && (
        <form onSubmit={submit} className="panel mb-5">
          <div className="mb-5 flex items-center justify-between"><div><h2 className="font-semibold">{editing ? `Edit ${module.title.replace(/s$/, "")}` : `Add ${module.title.replace(/s$/, "")}`}</h2><p className="mt-1 text-xs text-slate-500">Fields marked required must be completed.</p></div><button type="button" aria-label="Close form" onClick={() => { setEditing(null); setForm({}); setFormOpen(false); }} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><X size={17} /></button></div>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {module.fields.map((field) => {
              const value = getValue(form, field.name);
              const inputId = `${moduleKey}-${field.name.replaceAll(".", "-")}`;
              const required = field.required && !(editing && field.editOptional);
              const disabled = Boolean(editing && field.name.startsWith("user.") && ["user.username", "user.email"].includes(field.name));
              if (field.type === "checkbox") return <label key={field.name} htmlFor={inputId} className="flex items-center gap-2 self-end pb-3 text-sm text-slate-700"><input id={inputId} type="checkbox" checked={Boolean(value)} onChange={(event) => updateField(field, event.target.checked)} className="h-4 w-4 rounded border-slate-300 text-blue-600" />{field.label}</label>;
              if (field.type === "select" && field.options) {
                return <label key={field.name} htmlFor={inputId} className="block text-sm font-medium text-slate-700">{field.label}<select id={inputId} required={required} value={value ?? ""} onChange={(event) => updateField(field, event.target.value)} className="field mt-1.5"><option value="">Select…</option>{field.options.map(([optionValue, label]) => <option key={optionValue} value={optionValue}>{label}</option>)}</select></label>;
              }
              if (field.type === "select") {
                const options = related[field.endpoint] || [];
                return <label key={field.name} htmlFor={inputId} className="block text-sm font-medium text-slate-700">{field.label}<select id={inputId} required={required} value={value ?? ""} onChange={(event) => updateField(field, event.target.value)} className="field mt-1.5" disabled={options.length === 0}><option value="">{field.optional ? "None" : "Select…"}</option>{options.map((option) => <option key={option.id} value={field.optionValue ? getValue(option, field.optionValue) : option.id}>{option[field.optionLabel] || option.name || option.code || option.id}{field.endpoint === "sections" ? ` · ${option.name}` : ""}{field.endpoint === "semesters" ? ` · Semester ${option.number}` : ""}</option>)}</select></label>;
              }
              return <label key={field.name} htmlFor={inputId} className="block text-sm font-medium text-slate-700">{field.label}<input id={inputId} type={field.type || "text"} required={required} min={field.min} max={field.max} step={field.type === "number" ? "1" : undefined} disabled={disabled} value={value ?? ""} onChange={(event) => updateField(field, event.target.value)} placeholder={field.placeholder || ""} className="field mt-1.5 disabled:bg-slate-50 disabled:text-slate-400" /></label>;
            })}
          </div>
          {formError && <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{formError}</p>}
          <div className="mt-5 flex justify-end gap-2"><button type="button" onClick={() => { setEditing(null); setForm({}); setFormOpen(false); }} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50">Cancel</button><button disabled={saving} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60">{saving ? "Saving…" : "Save record"}</button></div>
        </form>
      )}

      <div className="panel !p-0">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-4">
          <div className="relative min-w-[220px] flex-1 sm:max-w-sm"><Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" /><input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} className="h-10 w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm outline-none focus:border-blue-300 focus:bg-white" placeholder={`Search ${module.title.toLowerCase()}…`} /></div>
          <div className="flex flex-wrap items-center gap-2">{(module.filters || []).map((filter) => <select key={filter.name} aria-label={`Filter by ${filter.label}`} value={filters[filter.name] || ""} onChange={(event) => { setFilters((current) => ({ ...current, [filter.name]: event.target.value })); setPage(1); }} className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-xs text-slate-600 outline-none focus:border-blue-300"><option value="">All {filter.label.toLowerCase()}</option>{filter.options ? filter.options.map(([value, label]) => <option key={value} value={value}>{label}</option>) : (related[filter.endpoint] || []).map((option) => <option key={option.id} value={option.id}>{option[filter.optionLabel] || option.name}</option>)}</select>)}<button onClick={() => setOrdering((value) => value ? "" : `-${module.orderingField}`)} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50"><ArrowDownUp size={14} />{ordering ? "Descending" : "Sort"}</button></div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500"><tr>{module.columns.map(([, label]) => <th key={label} className="px-4 py-3">{label}</th>)}{canManage && <th className="px-4 py-3 text-right">Actions</th>}</tr></thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? <tr><td colSpan={module.columns.length + Number(canManage)} className="px-4 py-12 text-center text-sm text-slate-500">Loading records…</td></tr>
                : rows.length === 0 ? <tr><td colSpan={module.columns.length + Number(canManage)} className="px-4 py-12 text-center"><p className="font-medium text-slate-600">No records found</p><p className="mt-1 text-xs text-slate-400">{search ? "Try another search." : "Create the first record to get started."}</p></td></tr>
                  : rows.map((row) => <tr key={row.id} className="table-row">{module.columns.map(([path]) => <td key={path} className="max-w-64 truncate px-4 py-3.5 text-slate-700">{displayValue(getValue(row, path), path)}</td>)}{canManage && <td className="px-4 py-3 text-right"><div className="inline-flex gap-1"><button aria-label={`Edit ${module.title} record`} onClick={() => beginEdit(row)} className="rounded-md p-2 text-slate-500 hover:bg-blue-50 hover:text-blue-700"><Pencil size={15} /></button><button aria-label={`Delete ${module.title} record`} onClick={() => remove(row)} className="rounded-md p-2 text-slate-500 hover:bg-red-50 hover:text-red-600"><Trash2 size={15} /></button></div></td>}</tr>)}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-xs text-slate-500"><span>Page {page} of {pageCount}</span><div className="flex gap-2"><button disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)} className="rounded-md border border-slate-200 px-3 py-1.5 disabled:opacity-40">Previous</button><button disabled={page >= pageCount || loading} onClick={() => setPage((value) => value + 1)} className="rounded-md border border-slate-200 px-3 py-1.5 disabled:opacity-40">Next</button></div></div>
      </div>
    </section>
  );
}
