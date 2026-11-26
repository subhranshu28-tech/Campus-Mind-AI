import { useEffect, useState } from "react";
import { BookOpen, Briefcase, CalendarDays, CheckCircle2, Clock3, FileText, GraduationCap, Upload, XCircle } from "lucide-react";
import api from "../services/api";
import SubjectNotes from "./SubjectNotes";

function PortalCard({ icon: Icon, label, value, detail, tone = "blue" }) {
  const tones = {
    blue: "bg-blue-50 text-blue-700",
    green: "bg-emerald-50 text-emerald-700",
    amber: "bg-amber-50 text-amber-700",
    violet: "bg-violet-50 text-violet-700",
  };
  return <article className="panel metric-card flex items-start justify-between"><div><p className="text-sm font-medium text-slate-500">{label}</p><p className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">{value}</p><p className="mt-2 text-xs text-slate-500">{detail}</p></div><span className={`metric-icon grid h-10 w-10 place-items-center rounded-xl ${tones[tone]}`}><Icon size={19} /></span></article>;
}

const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function StudentPortal() {
  const [portal, setPortal] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busyAssignment, setBusyAssignment] = useState(null);
  const [busyJob, setBusyJob] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState({});

  const loadPortal = () => {
    api.get("/student/portal/")
      .then(({ data }) => { setPortal(data); setError(""); })
      .catch((requestError) => { setError(requestError.response?.data?.detail || "Your student information could not be loaded."); });
  };

  useEffect(() => {
    let active = true;
    api.get("/student/portal/")
      .then(({ data }) => { if (active) setPortal(data); })
      .catch((requestError) => { if (active) setError(requestError.response?.data?.detail || "Your student information could not be loaded."); });
    return () => { active = false; };
  }, []);

  const submitAssignment = async (assignmentId) => {
    setBusyAssignment(assignmentId);
    setMessage("");
    try {
      const file = selectedFiles[assignmentId];
      if (file) {
        const formData = new FormData();
        formData.append("assignment", assignmentId);
        formData.append("file", file);
        await api.post("/submissions/", formData, { headers: { "Content-Type": "multipart/form-data" } });
      } else {
        await api.post("/submissions/", { assignment: assignmentId });
      }
      setMessage("Assignment submitted successfully.");
      setSelectedFiles((current) => ({ ...current, [assignmentId]: null }));
      loadPortal();
    } catch (requestError) {
      setMessage(requestError.response?.data?.detail || "Could not submit the assignment.");
    } finally {
      setBusyAssignment(null);
    }
  };

  const applyToJob = async (jobId) => {
    setBusyJob(jobId);
    setMessage("");
    try {
      await api.post("/placement-applications/", { job: jobId });
      setMessage("Application submitted successfully.");
      loadPortal();
    } catch (requestError) {
      setMessage(requestError.response?.data?.detail || "Could not submit the application.");
    } finally {
      setBusyJob(null);
    }
  };

  if (error) return <div role="alert" className="content-enter rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>;
  if (!portal) return <div className="panel py-12 text-center text-sm text-slate-500">Loading your student workspace…</div>;

  const { student, attendance, subjects, timetable, exams, assignments = [], jobs = [] } = portal;
  const rate = attendance.percentage === null ? "—" : `${attendance.percentage}%`;
  const schedule = [...timetable].sort((a, b) => a.weekday - b.weekday || a.period - b.period);

  return <div className="content-enter">
    <div className="mb-7 flex flex-wrap items-end justify-between gap-3"><div><p className="text-sm font-medium text-blue-700">Student workspace</p><h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-[28px]">Welcome, {student.name.split(" ")[0]}</h1><p className="mt-1 text-sm text-slate-500">{student.course || student.department} · Semester {student.semester}{student.section ? ` · Section ${student.section}` : ""}{student.academic_year ? ` · ${student.academic_year}` : ""}</p></div><span className="glass-badge flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium text-slate-600"><GraduationCap size={15} className="text-blue-600" />{student.student_id}</span></div>
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <PortalCard icon={CalendarDays} label="Attendance" value={rate} detail={`${attendance.present_sessions} of ${attendance.total_sessions} recorded sessions`} tone="blue" />
      <PortalCard icon={CheckCircle2} label="Present" value={attendance.present_sessions} detail="Sessions marked present" tone="green" />
      <PortalCard icon={XCircle} label="Absent" value={attendance.absent_sessions} detail="Sessions marked absent" tone="amber" />
      <PortalCard icon={BookOpen} label="My subjects" value={subjects.length} detail="Subjects assigned to your section" tone="violet" />
    </section>
    <section className="mt-5 grid gap-5 xl:grid-cols-2">
      <article className="panel"><div className="mb-5 flex items-center justify-between"><div><h2 className="text-base font-semibold">Attendance history</h2><p className="mt-1 text-sm text-slate-500">Your latest recorded sessions</p></div><CalendarDays className="text-blue-600" size={19} /></div>
        {attendance.records.length ? <div className="max-h-80 overflow-y-auto">{attendance.records.map((record) => <div key={record.id} className="flex items-center justify-between gap-3 border-b border-slate-100 py-3 last:border-0"><div><p className="text-sm font-medium text-slate-700">{new Date(`${record.date}T00:00:00`).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric" })}</p><p className="mt-1 text-xs text-slate-400">Recorded by {record.recorded_by_name || "campus staff"}</p></div><span className={`rounded-full px-2.5 py-1 text-xs font-medium ${record.is_present ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"}`}>{record.is_present ? "Present" : "Absent"}</span></div>)}</div> : <div className="grid min-h-40 place-items-center text-center"><div><CalendarDays className="mx-auto text-slate-300" size={28} /><p className="mt-3 text-sm font-medium text-slate-600">No attendance recorded yet</p><p className="mt-1 text-xs text-slate-400">Attendance will appear here when it is recorded.</p></div></div>}
      </article>
      <article className="panel"><div className="mb-5 flex items-center justify-between"><div><h2 className="text-base font-semibold">My subjects</h2><p className="mt-1 text-sm text-slate-500">Courses and assigned faculty</p></div><BookOpen className="text-blue-600" size={19} /></div>
        {subjects.length ? <div className="space-y-3">{subjects.map((subject) => <div key={subject.id} className="flex items-start justify-between gap-3 rounded-xl border border-slate-100 bg-white/50 p-3"><div><span className="text-xs font-semibold text-blue-700">{subject.code}</span><h3 className="mt-1 text-sm font-medium text-slate-800">{subject.name}</h3><p className="mt-1 text-xs text-slate-500">{subject.faculty || "Faculty not assigned"} · {subject.credits} credits</p></div><span className="whitespace-nowrap rounded-lg bg-slate-50 px-2 py-1 text-xs text-slate-500">{subject.periods_per_week} periods/wk</span></div>)}</div> : <div className="grid min-h-40 place-items-center text-center"><div><BookOpen className="mx-auto text-slate-300" size={28} /><p className="mt-3 text-sm font-medium text-slate-600">Subjects are not assigned yet</p><p className="mt-1 text-xs text-slate-400">Check back after your section timetable is set up.</p></div></div>}
      </article>
    </section>
    <section className="mt-5 grid gap-5 xl:grid-cols-2">
      <article className="panel"><div className="mb-5 flex items-center justify-between"><div><h2 className="text-base font-semibold">Weekly timetable</h2><p className="mt-1 text-sm text-slate-500">Classes scheduled for your section</p></div><Clock3 className="text-blue-600" size={19} /></div>
        {schedule.length ? <div className="space-y-2">{schedule.map((entry) => <div key={entry.id} className="flex items-center gap-3 rounded-xl bg-white/50 p-3"><span className="w-20 shrink-0 text-xs font-semibold text-slate-600">{weekdays[entry.weekday]}</span><span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-blue-50 text-xs font-semibold text-blue-700">P{entry.period}</span><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium text-slate-800">{entry.subject_name}</p><p className="mt-1 text-xs text-slate-500">{entry.faculty_name} · Room {entry.room_code}</p></div></div>)}</div> : <div className="grid min-h-40 place-items-center text-center"><div><Clock3 className="mx-auto text-slate-300" size={28} /><p className="mt-3 text-sm font-medium text-slate-600">No timetable published</p><p className="mt-1 text-xs text-slate-400">Your class schedule will show here when available.</p></div></div>}
      </article>
      <article className="panel"><div className="mb-5 flex items-center justify-between"><div><h2 className="text-base font-semibold">Upcoming exams</h2><p className="mt-1 text-sm text-slate-500">Scheduled examinations for your section</p></div><FileText className="text-blue-600" size={19} /></div>
        {exams.length ? <div className="space-y-3">{exams.map((exam) => <div key={exam.id} className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 bg-white/50 p-3"><div><p className="text-sm font-medium text-slate-800">{exam.subject_name}</p><p className="mt-1 text-xs text-slate-500">{new Date(`${exam.date}T00:00:00`).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric" })} · Period {exam.start_period}</p></div><span className="rounded-lg bg-violet-50 px-2.5 py-1 text-xs font-medium text-violet-700">{exam.room_code}</span></div>)}</div> : <div className="grid min-h-40 place-items-center text-center"><div><CalendarDays className="mx-auto text-slate-300" size={28} /><p className="mt-3 text-sm font-medium text-slate-600">No upcoming exams</p><p className="mt-1 text-xs text-slate-400">Scheduled exams will appear here.</p></div></div>}
      </article>
    </section>
    {message ? <div role="status" className="mt-5 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700">{message}</div> : null}
    <section className="mt-5 grid gap-5 xl:grid-cols-1">
      <article className="panel"><div className="mb-5 flex items-center justify-between"><div><h2 className="text-base font-semibold">Assignments & submissions</h2><p className="mt-1 text-sm text-slate-500">Submit your work before the due date</p></div><FileText className="text-blue-600" size={19} /></div>
        {assignments.length ? <div className="space-y-3">{assignments.map((assignment) => <div key={assignment.id} className="rounded-xl border border-slate-100 bg-white/50 p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-slate-800">{assignment.title}</p>
              <p className="mt-1 text-xs text-slate-500">{assignment.subject_code} · {assignment.subject} · {assignment.faculty}</p>
              <p className="mt-1 text-xs text-slate-500">Due {new Date(assignment.due_at).toLocaleString()} · Max {assignment.max_marks} marks</p>
              {assignment.description ? <p className="mt-2 text-xs text-slate-600">{assignment.description}</p> : null}
            </div>
            {assignment.submission ? <span className="rounded-lg bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">Submitted{assignment.submission.marks !== null ? ` · ${assignment.submission.marks}/${assignment.max_marks}` : ""}</span> : <span className="rounded-lg bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">Pending</span>}
          </div>
          {!assignment.submission ? <div className="mt-3 flex flex-wrap items-center gap-2">
            <input type="file" className="text-xs text-slate-500" onChange={(event) => setSelectedFiles((current) => ({ ...current, [assignment.id]: event.target.files?.[0] || null }))} />
            <button type="button" disabled={busyAssignment === assignment.id} onClick={() => submitAssignment(assignment.id)} className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-60">{busyAssignment === assignment.id ? "Submitting…" : "Submit"}</button>
          </div> : (assignment.submission.feedback ? <p className="mt-3 text-xs text-slate-600">Feedback: {assignment.submission.feedback}</p> : null)}
        </div>)}</div> : <div className="grid min-h-24 place-items-center text-center"><div><FileText className="mx-auto text-slate-300" size={24} /><p className="mt-2 text-sm font-medium text-slate-600">No assignments published</p></div></div>}
      </article>
    </section>
    <section className="mt-5 grid gap-5 xl:grid-cols-1">
      <article className="panel"><div className="mb-5 flex items-center justify-between"><div><h2 className="text-base font-semibold">Placement opportunities</h2><p className="mt-1 text-sm text-slate-500">Apply before the deadline</p></div><Briefcase className="text-blue-600" size={19} /></div>
        {jobs.length ? <div className="space-y-3">{jobs.map((job) => <div key={job.id} className="rounded-xl border border-slate-100 bg-white/50 p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-slate-800">{job.title}</p>
              <p className="mt-1 text-xs text-slate-500">{job.company}{job.package ? ` · ${job.package}` : ""}</p>
              {job.deadline ? <p className="mt-1 text-xs text-slate-500">Deadline {new Date(`${job.deadline}T00:00:00`).toLocaleDateString()}</p> : null}
              {job.description ? <p className="mt-2 text-xs text-slate-600">{job.description}</p> : null}
              {job.eligibility ? <p className="mt-2 text-xs text-slate-500">Eligibility: {job.eligibility}</p> : null}
            </div>
            {job.application ? <span className="rounded-lg bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">{job.application.status}</span> : <button type="button" disabled={busyJob === job.id} onClick={() => applyToJob(job.id)} className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-60">{busyJob === job.id ? "Applying…" : "Apply"}</button>}
          </div>
          {job.application?.remarks ? <p className="mt-3 text-xs text-slate-600">Remarks: {job.application.remarks}</p> : null}
        </div>)}</div> : <div className="grid min-h-24 place-items-center text-center"><div><Briefcase className="mx-auto text-slate-300" size={24} /><p className="mt-2 text-sm font-medium text-slate-600">No open positions</p></div></div>}
      </article>
    </section>
  </div>;
}
