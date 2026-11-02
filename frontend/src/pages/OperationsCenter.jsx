import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AlertTriangle, CheckCircle2, Download, Info, Loader2, Play, UserCheck } from "lucide-react";
import api from "../services/api";

const tabs = [
  { id: "analytics", label: "Analytics" },
  { id: "cover", label: "Leave & substitutes" },
  { id: "exams", label: "Exam planner" },
  { id: "audit", label: "Audit trail" },
];
const items = (data) => data?.results ?? data ?? [];
const errorText = (error) => {
  const data = error?.response?.data;
  if (!data) return "Request failed. Please try again.";
  if (typeof data === "string") return data;
  return data.detail || Object.values(data).flat().join(" ") || "Request failed.";
};
const severityStyle = {
  critical: "border-red-200 bg-red-50 text-red-800",
  warning: "border-amber-200 bg-amber-50 text-amber-800",
  info: "border-blue-200 bg-blue-50 text-blue-800",
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
};

function Stat({ label, value, tone = "" }) {
  return <article className="panel"><p className="text-xs font-medium text-slate-500">{label}</p><p className={`mt-2 text-2xl font-semibold ${tone}`}>{value ?? "—"}</p></article>;
}

function Analytics() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [lists, setLists] = useState({ sections: [], faculty: [], rooms: [] });
  const [scope, setScope] = useState("section");
  const [target, setTarget] = useState("");

  useEffect(() => {
    api.get("/analytics/overview/").then(({ data: body }) => setData(body)).catch((e) => setError(errorText(e)));
    Promise.all([api.get("/sections/"), api.get("/faculty/"), api.get("/classrooms/")])
      .then(([s, f, r]) => setLists({ sections: items(s.data), faculty: items(f.data), rooms: items(r.data) })).catch(() => {});
  }, []);

  const options = scope === "section" ? lists.sections.map((x) => [x.id, `${x.semester_label} · ${x.name}`])
    : scope === "faculty" ? lists.faculty.map((x) => [x.id, x.user_name || x.employee_id]) : lists.rooms.map((x) => [x.id, `${x.code} · ${x.name}`]);

  const download = async () => {
    try {
      const { data: blob } = await api.get("/exports/timetable/", { params: { scope, id: target }, responseType: "blob" });
      const url = URL.createObjectURL(blob);
      const link = Object.assign(document.createElement("a"), { href: url, download: `timetable-${scope}-${target}.xlsx` });
      link.click();
      URL.revokeObjectURL(url);
    } catch (e) { setError("Export failed. Generate a timetable first."); }
  };

  if (error && !data) return <p className="panel text-sm text-red-700">{error}</p>;
  if (!data) return <p className="panel flex items-center gap-2 text-sm text-slate-500"><Loader2 className="animate-spin" size={16} />Analysing campus resources…</p>;
  const { summary, rooms, heatmap, days, faculty, insights } = data;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Room utilisation" value={`${summary.overall_utilization}%`} tone="text-blue-700" />
        <Stat label="Idle room-slots / week" value={summary.idle_room_slots} />
        <Stat label="Scheduling conflicts" value={summary.conflicts} tone={summary.conflicts ? "text-red-600" : "text-emerald-600"} />
        <Stat label="Overloaded faculty" value={summary.overloaded_faculty} tone={summary.overloaded_faculty ? "text-amber-600" : ""} />
        <Stat label="Pending leave requests" value={summary.pending_leaves} />
        <Stat label="Upcoming cover classes" value={summary.upcoming_cover} />
        <Stat label="Classes without cover" value={summary.unresolved_cover} tone={summary.unresolved_cover ? "text-red-600" : ""} />
        <Stat label="Exams scheduled" value={summary.exams_scheduled} />
      </div>
      <section className="panel"><h2 className="text-base font-semibold">Insights</h2><div className="mt-3 space-y-2">{insights.map((item, index) => <p key={index} className={`flex gap-2 rounded-lg border px-3 py-2 text-sm ${severityStyle[item.severity]}`}>{item.severity === "success" ? <CheckCircle2 size={16} className="mt-0.5 shrink-0" /> : item.severity === "info" ? <Info size={16} className="mt-0.5 shrink-0" /> : <AlertTriangle size={16} className="mt-0.5 shrink-0" />}{item.text}</p>)}</div></section>
      <section className="panel"><h2 className="text-base font-semibold">Room & lab utilisation</h2><p className="text-xs text-slate-500">Share of the 40 weekly periods each room is in use</p>
        <div className="mt-4 h-64"><ResponsiveContainer width="100%" height="100%"><BarChart data={rooms}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="code" fontSize={12} /><YAxis unit="%" domain={[0, 100]} fontSize={12} /><Tooltip /><Bar dataKey="utilization" name="Utilisation %" fill="#2563eb" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div></section>
      <section className="panel overflow-x-auto"><h2 className="text-base font-semibold">Demand heatmap</h2><p className="text-xs text-slate-500">Percentage of rooms occupied in each period - spot peak hours and free capacity</p>
        <table className="mt-3 min-w-[520px] text-center text-xs"><thead><tr><th className="p-1" />{Array.from({ length: 8 }, (_, i) => <th key={i} className="p-1 text-slate-500">P{i + 1}</th>)}</tr></thead>
          <tbody>{heatmap.map((row, d) => <tr key={d}><th className="p-1 pr-2 text-left text-slate-500">{days[d].slice(0, 3)}</th>{row.map((value, p) => <td key={p} className="p-0.5"><div className="rounded-md py-2 font-medium" style={{ background: `rgba(37,99,235,${Math.min(value, 100) / 100 * 0.85 + 0.05})`, color: value > 45 ? "#fff" : "#1e3a8a" }}>{value}%</div></td>)}</tr>)}</tbody></table></section>
      <section className="panel"><h2 className="text-base font-semibold">Faculty workload</h2><div className="mt-3 divide-y divide-slate-100">{faculty.slice(0, 8).map((person) => <div key={person.faculty} className="flex items-center justify-between py-2 text-sm"><span>{person.name}</span><span className={person.overloaded ? "font-semibold text-amber-600" : "text-slate-600"}>{person.weekly_periods} periods/week{person.peak_day ? ` · peak ${person.peak_day.slice(0, 3)} (${person.peak_day_periods})` : ""}</span></div>)}</div></section>
      <section className="panel"><h2 className="text-base font-semibold">Export timetable (Excel)</h2>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <label className="text-sm font-medium text-slate-700">View<select className="field mt-1.5" value={scope} onChange={(e) => { setScope(e.target.value); setTarget(""); }}><option value="section">Section</option><option value="faculty">Faculty</option><option value="room">Room / lab</option></select></label>
          <label className="min-w-48 flex-1 text-sm font-medium text-slate-700">Select<select className="field mt-1.5" value={target} onChange={(e) => setTarget(e.target.value)}><option value="">Choose…</option>{options.map(([id, text]) => <option key={id} value={id}>{text}</option>)}</select></label>
          <button disabled={!target} onClick={download} className="inline-flex h-10 items-center gap-2 rounded-xl bg-blue-600 px-4 text-sm font-semibold text-white disabled:opacity-50"><Download size={16} />Download</button>
        </div>{error && <p className="mt-2 text-sm text-red-700">{error}</p>}</section>
    </div>
  );
}

function Cover({ canManage }) {
  const [leaves, setLeaves] = useState([]);
  const [faculty, setFaculty] = useState([]);
  const [covers, setCovers] = useState([]);
  const [form, setForm] = useState({ faculty: "", start_date: "", end_date: "", reason: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [uncovered, setUncovered] = useState({});

  const load = () => {
    api.get("/leaves/").then(({ data }) => setLeaves(items(data))).catch((e) => setError(errorText(e)));
    api.get("/substitutions/", { params: { upcoming: 1 } }).then(({ data }) => setCovers(items(data))).catch(() => {});
  };
  useEffect(() => { load(); if (canManage) api.get("/faculty/").then(({ data }) => setFaculty(items(data))).catch(() => {}); }, [canManage]);

  const run = async (task, success) => {
    setBusy(true); setError(""); setMessage("");
    try { const result = await task(); setMessage(success(result)); load(); } catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  };
  const submit = (event) => {
    event.preventDefault();
    const payload = { start_date: form.start_date, end_date: form.end_date, reason: form.reason };
    if (canManage) payload.faculty = form.faculty;
    run(() => api.post("/leaves/", payload), () => "Leave request submitted.");
    setForm({ ...form, reason: "" });
  };
  const approve = (leave) => run(() => api.post(`/leaves/${leave.id}/approve/`), ({ data }) => `Approved. ${data.assigned.length} class(es) covered automatically${data.unresolved.length ? `, ${data.unresolved.length} need manual cover` : ""}.`);
  const reject = (leave) => run(() => api.post(`/leaves/${leave.id}/reject/`), () => "Leave rejected.");
  const showUncovered = async (leave) => { const { data } = await api.get(`/leaves/${leave.id}/uncovered/`); setUncovered((current) => ({ ...current, [leave.id]: data })); };
  const assign = (leave, row, facultyId) => run(() => api.post(`/leaves/${leave.id}/assign-cover/`, { timetable_entry: row.timetable_entry, date: row.date, faculty: facultyId }), () => "Cover assigned and everyone notified.").then(() => showUncovered(leave));

  return (
    <div className="space-y-5">
      {(message || error) && <p className={`rounded-lg border px-3 py-2 text-sm ${error ? "border-red-200 bg-red-50 text-red-800" : "border-emerald-200 bg-emerald-50 text-emerald-800"}`}>{error || message}</p>}
      <form onSubmit={submit} className="panel grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {canManage && <label className="text-sm font-medium text-slate-700">Faculty<select required className="field mt-1.5" value={form.faculty} onChange={(e) => setForm({ ...form, faculty: e.target.value })}><option value="">Select…</option>{faculty.map((f) => <option key={f.id} value={f.id}>{f.user_name || f.employee_id}</option>)}</select></label>}
        <label className="text-sm font-medium text-slate-700">From<input required type="date" className="field mt-1.5" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></label>
        <label className="text-sm font-medium text-slate-700">To<input required type="date" className="field mt-1.5" value={form.end_date} min={form.start_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} /></label>
        <label className="text-sm font-medium text-slate-700">Reason<input className="field mt-1.5" value={form.reason} maxLength={240} onChange={(e) => setForm({ ...form, reason: e.target.value })} /></label>
        <button disabled={busy} className="mt-auto h-10 rounded-xl bg-blue-600 px-4 text-sm font-semibold text-white disabled:opacity-60">Request leave</button>
      </form>
      <section className="panel"><h2 className="text-base font-semibold">Leave requests</h2><div className="mt-3 divide-y divide-slate-100">
        {leaves.length === 0 && <p className="py-4 text-sm text-slate-500">No leave requests yet.</p>}
        {leaves.map((leave) => <div key={leave.id} className="py-3 text-sm"><div className="flex flex-wrap items-center justify-between gap-2"><div><p className="font-medium">{leave.faculty_name}</p><p className="text-xs text-slate-500">{leave.start_date} → {leave.end_date}{leave.reason ? ` · ${leave.reason}` : ""}</p></div>
          <div className="flex items-center gap-2"><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium capitalize">{leave.status}{leave.status === "approved" ? ` · ${leave.covered} covered` : ""}</span>
            {canManage && leave.status === "pending" && <><button disabled={busy} onClick={() => approve(leave)} className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white">Approve & auto-assign</button><button disabled={busy} onClick={() => reject(leave)} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold">Reject</button></>}
            {canManage && leave.status === "approved" && <button onClick={() => showUncovered(leave)} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold">Check uncovered</button>}</div></div>
          {uncovered[leave.id] && (uncovered[leave.id].length === 0 ? <p className="mt-2 text-xs text-emerald-700">Every affected class has cover.</p> : <div className="mt-2 space-y-2">{uncovered[leave.id].map((row) => <div key={`${row.timetable_entry}-${row.date}`} className="rounded-lg bg-amber-50 p-2 text-xs"><p className="font-medium text-amber-900">{row.subject} · {row.section} · {row.date} P{row.period}</p>{row.candidates.length === 0 ? <p className="text-amber-800">No qualified, free substitute - reschedule or cancel this class.</p> : <div className="mt-1 flex flex-wrap gap-1.5">{row.candidates.map((c) => <button key={c.faculty} onClick={() => assign(leave, row, c.faculty)} title={c.reason} className="inline-flex items-center gap-1 rounded-md bg-white px-2 py-1 font-medium text-blue-700 shadow-sm"><UserCheck size={12} />{c.name}</button>)}</div>}</div>)}</div>)}
        </div>)}</div></section>
      <section className="panel"><h2 className="text-base font-semibold">Upcoming cover classes</h2><div className="mt-3 divide-y divide-slate-100">{covers.length === 0 && <p className="py-4 text-sm text-slate-500">No substitutions scheduled.</p>}
        {covers.map((c) => <p key={c.id} className="py-2 text-sm"><span className="font-medium">{c.date} P{c.period}</span> · {c.subject_code} · {c.section_name} · room {c.room_code} — <span className="text-slate-500">{c.original_name} → </span><span className="font-medium text-blue-700">{c.substitute_name}</span></p>)}</div></section>
    </div>
  );
}

function Exams() {
  const [semesters, setSemesters] = useState([]);
  const [form, setForm] = useState({ semester: "", start_date: "", end_date: "", avoid_class_clashes: false, replace_existing: true });
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get("/semesters/").then(({ data }) => setSemesters(items(data))).catch(() => {}); }, []);

  const run = async (preview) => {
    setBusy(true); setError("");
    try { const { data } = await api.post("/exams/auto-schedule/", { ...form, preview }); setResult(data); } catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  };
  const byDate = useMemo(() => (result?.scheduled || []).slice().sort((a, b) => `${a.date}${a.start_period}`.localeCompare(`${b.date}${b.start_period}`)), [result]);
  return (
    <div className="space-y-5">
      <section className="panel grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-sm font-medium text-slate-700 lg:col-span-2">Semester<select className="field mt-1.5" value={form.semester} onChange={(e) => setForm({ ...form, semester: e.target.value })}><option value="">Select…</option>{semesters.map((s) => <option key={s.id} value={s.id}>{s.course_name} · Semester {s.number} · {s.academic_year_name}</option>)}</select></label>
        <label className="text-sm font-medium text-slate-700">Window starts<input type="date" className="field mt-1.5" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></label>
        <label className="text-sm font-medium text-slate-700">Window ends<input type="date" className="field mt-1.5" min={form.start_date} value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} /></label>
        <label className="flex items-center gap-2 text-sm text-slate-700 lg:col-span-2"><input type="checkbox" checked={form.avoid_class_clashes} onChange={(e) => setForm({ ...form, avoid_class_clashes: e.target.checked })} />Avoid clashes with regular classes (turn off for a dedicated exam week)</label>
        <label className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={form.replace_existing} onChange={(e) => setForm({ ...form, replace_existing: e.target.checked })} />Replace existing exams</label>
        <div className="flex gap-2 lg:justify-end"><button disabled={busy || !form.semester || !form.start_date || !form.end_date} onClick={() => run(true)} className="inline-flex h-10 items-center gap-2 rounded-xl border border-blue-200 px-4 text-sm font-semibold text-blue-700 disabled:opacity-50">{busy ? <Loader2 className="animate-spin" size={16} /> : <Play size={16} />}Preview</button>
          <button disabled={busy || !result?.preview || !result.scheduled.length} onClick={() => run(false)} className="h-10 rounded-xl bg-blue-600 px-4 text-sm font-semibold text-white disabled:opacity-50">Publish</button></div>
      </section>
      {error && <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
      {result && <section className="panel overflow-x-auto"><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-base font-semibold">{result.preview ? "Preview" : "Published"} · {result.stats.exams} exams over {result.stats.days_used} days</h2>{result.stats.unscheduled > 0 && <span className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-medium text-red-700">{result.stats.unscheduled} could not be placed</span>}</div>
        <table className="mt-3 w-full min-w-[640px] text-left text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="py-2">Date</th><th>Session</th><th>Subject</th><th>Section</th><th>Room</th><th>Invigilator</th></tr></thead>
          <tbody className="divide-y divide-slate-100">{byDate.map((row, i) => <tr key={i}><td className="py-2">{row.date}</td><td>{row.session} (P{row.start_period}-{row.start_period + row.duration_periods - 1})</td><td className="font-medium">{row.subject}</td><td>{row.section}</td><td>{row.room}</td><td>{row.invigilator || <span className="text-amber-600">unassigned</span>}</td></tr>)}</tbody></table>
        {result.unscheduled.map((row, i) => <p key={i} className="mt-2 text-xs text-red-700">{row.subject} · {row.section}: {row.reason}</p>)}</section>}
    </div>
  );
}

function Audit() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/audit-logs/").then(({ data }) => setRows(items(data))).catch(() => {}); }, []);
  return <section className="panel"><h2 className="text-base font-semibold">Recent changes</h2><div className="mt-3 divide-y divide-slate-100">{rows.length === 0 && <p className="py-4 text-sm text-slate-500">No activity recorded yet.</p>}{rows.map((row) => <p key={row.id} className="py-2 text-sm"><span className="font-medium">{row.actor_name}</span> · {row.action} <span className="text-slate-500">{row.entity} {row.entity_id}</span><span className="float-right text-xs text-slate-400">{new Date(row.created_at).toLocaleString()}</span></p>)}</div></section>;
}

export default function OperationsCenter({ canManage }) {
  const [tab, setTab] = useState("analytics");
  const visible = canManage ? tabs : tabs.filter((t) => t.id === "analytics" || t.id === "cover");
  return (
    <div>
      <div className="mb-5"><p className="text-sm font-medium text-blue-700">Academic operations</p><h1 className="mt-1 text-2xl font-semibold tracking-tight">Operations center</h1><p className="mt-1 text-sm text-slate-500">Resource analytics, faculty substitutions, automatic exam planning and a full audit trail.</p></div>
      <div className="mb-5 flex gap-1 overflow-x-auto rounded-xl bg-slate-100/70 p-1">{visible.map((item) => <button key={item.id} onClick={() => setTab(item.id)} className={`whitespace-nowrap rounded-lg px-3.5 py-2 text-sm font-medium ${tab === item.id ? "bg-white text-blue-700 shadow-sm" : "text-slate-600"}`}>{item.label}</button>)}</div>
      {tab === "analytics" && <Analytics />}{tab === "cover" && <Cover canManage={canManage} />}{tab === "exams" && canManage && <Exams />}{tab === "audit" && canManage && <Audit />}
    </div>
  );
}
