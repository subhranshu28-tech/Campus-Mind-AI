import { useEffect, useMemo, useState } from "react";
import { CalendarDays, Lightbulb, RefreshCw, Sparkles } from "lucide-react";
import api from "../services/api";

const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

function messageFrom(error) {
  const detail = error.response?.data?.detail;
  return Array.isArray(detail) ? detail.join(", ") : detail || "The request failed. Review the timetable setup and try again.";
}

export default function TimetableManager() {
  const [semesters, setSemesters] = useState([]);
  const [sections, setSections] = useState([]);
  const [entries, setEntries] = useState([]);
  const [semesterId, setSemesterId] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [suggestions, setSuggestions] = useState(null);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([api.get("/semesters/"), api.get("/sections/")])
      .then(([semesterResponse, sectionResponse]) => {
        if (!active) return;
        const semesterRows = Array.isArray(semesterResponse.data)
          ? semesterResponse.data : semesterResponse.data.results || [];
        const sectionRows = Array.isArray(sectionResponse.data)
          ? sectionResponse.data : sectionResponse.data.results || [];
        setSemesters(semesterRows);
        setSections(sectionRows);
        setSemesterId((current) => current || String(semesterRows[0]?.id || ""));
      })
      .catch((requestError) => {
        if (active) setError(messageFrom(requestError));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    if (!semesterId) {
      setEntries([]);
      return () => { active = false; };
    }
    api.get("/timetable/entries/", { params: { "section__semester": semesterId } })
      .then(({ data }) => {
        if (active) setEntries(Array.isArray(data) ? data : data.results || []);
      })
      .catch((requestError) => {
        if (active) setError(messageFrom(requestError));
      });
    return () => { active = false; };
  }, [semesterId]);

  const semesterSections = useMemo(
    () => sections.filter((section) => String(section.semester) === String(semesterId)),
    [sections, semesterId],
  );
  const shownEntries = useMemo(
    () => sectionId ? entries.filter((entry) => String(entry.section) === String(sectionId)) : entries,
    [entries, sectionId],
  );
  const activeSemester = semesters.find((semester) => String(semester.id) === String(semesterId));

  async function generate() {
    if (!semesterId) {
      setError("Create an academic year, course, and semester before generating a timetable.");
      return;
    }
    if (!window.confirm("Generate a conflict-free timetable for this semester? This replaces its current timetable.")) return;
    setGenerating(true);
    setError("");
    setNotice("");
    try {
      const { data } = await api.post("/timetable/generate/", { semester: Number(semesterId) });
      setEntries(data.entries);
      setNotice(`Generated ${data.entry_count} class sessions for ${data.semester_label}. Existing timetables for other semesters were preserved.`);
    } catch (requestError) {
      setError(messageFrom(requestError));
    } finally {
      setGenerating(false);
    }
  }

  async function showSubstitutions(entry) {
    setSuggestions({ loading: true, entry });
    setLoadingSuggestions(true);
    try {
      const { data } = await api.get(`/timetable/entries/${entry.id}/substitutions/`);
      setSuggestions({ ...data, entry });
    } catch (requestError) {
      setSuggestions({ entry, error: messageFrom(requestError) });
    } finally {
      setLoadingSuggestions(false);
    }
  }

  const cells = useMemo(() => {
    const bySlot = new Map();
    for (const entry of shownEntries) {
      const key = `${entry.weekday}:${entry.period}`;
      if (!bySlot.has(key)) bySlot.set(key, []);
      bySlot.get(key).push(entry);
    }
    return bySlot;
  }, [shownEntries]);

  return (
    <section className="content-enter">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div><p className="text-sm font-medium text-blue-700">Academic operations</p><h1 className="mt-1 text-2xl font-semibold tracking-tight">AI smart timetable</h1><p className="mt-1 text-sm text-slate-500">Build a conflict-free weekly schedule around teaching loads, faculty availability, room capacity, and lab requirements.</p></div>
        <button onClick={generate} disabled={generating || loading || !semesterId} className="glass-button inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"><Sparkles size={16} />{generating ? "Optimizing…" : "Generate timetable"}</button>
      </div>

      {error && <div role="alert" className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {notice && <div role="status" className="mb-4 flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"><Sparkles size={16} className="mt-0.5 shrink-0" />{notice}</div>}

      <div className="panel mb-5">
        <div className="grid gap-4 sm:grid-cols-[minmax(220px,1fr)_minmax(200px,1fr)_auto] sm:items-end">
          <label className="text-sm font-medium text-slate-700">Semester<select value={semesterId} onChange={(event) => { setSemesterId(event.target.value); setSectionId(""); setError(""); setNotice(""); }} className="field mt-1.5" disabled={loading || semesters.length === 0}><option value="">{loading ? "Loading…" : "Select a semester"}</option>{semesters.map((semester) => <option key={semester.id} value={semester.id}>{semester.course_name} · Semester {semester.number} · {semester.academic_year_name}</option>)}</select></label>
          <label className="text-sm font-medium text-slate-700">Section view<select value={sectionId} onChange={(event) => setSectionId(event.target.value)} className="field mt-1.5" disabled={!semesterId}><option value="">All sections</option>{semesterSections.map((section) => <option key={section.id} value={section.id}>{section.name}</option>)}</select></label>
          <div className="inline-flex items-center gap-2 pb-2 text-xs text-slate-500"><CalendarDays size={15} />{shownEntries.length} scheduled sessions</div>
        </div>
      </div>

      {!loading && semesters.length === 0 && <div className="panel mb-5 text-sm text-slate-600">First create an academic year, course, semester, section, subject, faculty member, and teaching assignment. Then add active rooms and faculty availability constraints.</div>}

      <div className="panel overflow-hidden !p-0">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 p-4"><div><h2 className="font-semibold">{activeSemester ? `${activeSemester.course_name} · Semester ${activeSemester.number}` : "Weekly schedule"}</h2><p className="mt-1 text-xs text-slate-500">Periods 1–8 · Monday–Friday</p></div><span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700"><Lightbulb size={13} />OR-Tools CP-SAT</span></div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[850px] table-fixed border-collapse text-left">
            <thead><tr className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500"><th className="w-20 border-b border-r border-slate-100 px-3 py-3">Period</th>{weekdays.map((day) => <th key={day} className="border-b border-r border-slate-100 px-3 py-3 last:border-r-0">{day}</th>)}</tr></thead>
            <tbody>{Array.from({ length: 8 }, (_, index) => index + 1).map((period) => <tr key={period}><th className="border-b border-r border-slate-100 bg-slate-50/60 px-3 py-3 text-xs font-semibold text-slate-500">Period {period}</th>{weekdays.map((day, weekday) => <td key={day} className="h-24 border-b border-r border-slate-100 p-1.5 align-top last:border-r-0">{(cells.get(`${weekday}:${period}`) || []).map((entry) => <article key={entry.id} className="mb-1 rounded-md border border-blue-100 bg-blue-50 p-2 text-[11px] leading-4 text-slate-700"><p className="font-semibold text-blue-800">{entry.subject_code} · {entry.section_name}</p><p className="truncate">{entry.faculty_name}</p><p className="font-medium">{entry.room_code}</p><button onClick={() => showSubstitutions(entry)} className="mt-1 inline-flex items-center gap-1 text-[10px] font-semibold text-blue-700 hover:text-blue-900"><RefreshCw size={10} />Substitutes</button></article>)}</td>)}</tr>)}</tbody>
          </table>
        </div>
        {entries.length === 0 && <div className="border-t border-slate-100 px-5 py-10 text-center"><p className="text-sm font-medium text-slate-600">{semesterId ? "No timetable generated for this semester yet." : "Select a semester to view its timetable."}</p><p className="mt-1 text-xs text-slate-400">Create teaching assignments and room resources, then run the optimizer.</p></div>}
      </div>

      {suggestions && <div role="dialog" aria-modal="true" aria-labelledby="substitution-title" className="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) setSuggestions(null); }}><div className="w-full max-w-lg rounded-2xl bg-white p-5 shadow-xl"><div className="flex items-start justify-between gap-4"><div><h2 id="substitution-title" className="font-semibold">Faculty substitution suggestions</h2><p className="mt-1 text-sm text-slate-500">{suggestions.entry.subject_code} · {weekdays[suggestions.entry.weekday]} · Period {suggestions.entry.period}</p></div><button onClick={() => setSuggestions(null)} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" aria-label="Close suggestions">×</button></div>{loadingSuggestions ? <p className="py-8 text-center text-sm text-slate-500">Checking subject expertise, availability, timetable conflicts, and teaching load…</p> : suggestions.error ? <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{suggestions.error}</p> : suggestions.suggestions?.length ? <ul className="mt-4 divide-y divide-slate-100">{suggestions.suggestions.map((candidate) => <li key={candidate.faculty} className="flex items-center justify-between gap-3 py-3"><div><p className="text-sm font-medium">{candidate.name}</p><p className="text-xs text-slate-500">{candidate.employee_id} · {candidate.weekly_assigned_periods} assigned periods / week</p></div><span className="rounded-full bg-emerald-50 px-2 py-1 text-[11px] font-medium text-emerald-700">Available</span></li>)}</ul> : <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">No eligible substitute is available for this subject and time. Assign another faculty member to this subject and update availability to expand suggestions.</p>}<div className="mt-4 flex justify-end"><button onClick={() => setSuggestions(null)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600">Close</button></div></div></div>}
    </section>
  );
}
