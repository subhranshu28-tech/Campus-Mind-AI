import { useEffect, useState } from "react";
import { Activity, Bell, BookOpen, Building2, CalendarDays, ChevronDown, GraduationCap, LayoutDashboard, LogOut, Menu, Search, Users, X, Sparkles, ClipboardList, Moon, Sun, FileText } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAuth } from "../context/AuthContext";
import api from "../services/api";
import ModuleManager from "./ModuleManager";
import TimetableManager from "./TimetableManager";
import StudentPortal from "./StudentPortal";
import SubjectNotes from "./SubjectNotes";
import OperationsCenter from "./OperationsCenter";
import NotificationBell from "./NotificationBell";

const navigation = [
  { label: "Overview", icon: LayoutDashboard, module: "overview" },
  { label: "Students", icon: GraduationCap, module: "students" },
  { label: "Faculty", icon: Users, module: "faculty" },
  { label: "Departments", icon: Building2, module: "departments" },
  { label: "Attendance", icon: CalendarDays, module: "attendance" },
  { label: "Academic years", icon: CalendarDays, module: "academic-years" },
  { label: "Courses", icon: BookOpen, module: "courses" },
  { label: "Semesters", icon: BookOpen, module: "semesters" },
  { label: "Sections", icon: Users, module: "sections" },
  { label: "Subjects", icon: BookOpen, module: "subjects" },
  { label: "Classrooms & labs", icon: Building2, module: "classrooms" },
  { label: "Teaching assignments", icon: Users, module: "teaching-assignments" },
  { label: "Faculty availability", icon: CalendarDays, module: "faculty-availability" },
  { label: "Exam schedules", icon: ClipboardList, module: "exam-schedules" },
  { label: "AI smart timetable", icon: Sparkles, module: "timetable" },
  { label: "Operations center", icon: Activity, module: "operations" },
  { label: "Subject notes", icon: FileText, module: "subject-notes" },
  { label: "Previous question papers", icon: ClipboardList, module: "question-papers" },
];
const studentNavigation = [
  { label: "My dashboard", icon: LayoutDashboard, module: "overview" },
  { label: "Subject notes", icon: FileText, module: "subject-notes" },
  { label: "Previous question papers", icon: ClipboardList, module: "question-papers" },
];

function Metric({ icon: Icon, label, value, note, color }) {
  return <article className="panel metric-card flex items-start justify-between"><div><p className="text-sm font-medium text-slate-500">{label}</p><p className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">{value}</p><p className="mt-2 text-xs text-slate-500">{note}</p></div><span className={`metric-icon grid h-10 w-10 place-items-center rounded-xl ${color}`}><Icon size={19} /></span></article>;
}

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [activeModule, setActiveModule] = useState("overview");
  const [theme, setTheme] = useState(() => localStorage.getItem("campus.theme") || "light");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("campus.theme", theme);
  }, [theme]);

  useEffect(() => {
    if (activeModule !== "overview" || user?.role === "student") return undefined;
    let active = true;
    api.get("/dashboard/summary/")
      .then(({ data }) => {
        if (active) setSummary(data);
      })
      .catch(() => {
        if (active) setError("Dashboard data could not be loaded. Please refresh or contact your administrator.");
      });
    return () => { active = false; };
  }, [activeModule, user?.role]);

  const displayName = user?.full_name || user?.username || "Campus user";
  const initials = displayName.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
  const chartData = summary ? [
    { name: "Students", total: summary.students },
    { name: "Faculty", total: summary.faculty },
    { name: "Departments", total: summary.departments },
  ] : [];
  const roleLabel = user?.role?.replaceAll("_", " ");
  const canManage = user?.is_staff || ["super_admin", "college_admin", "hod"].includes(user?.role);
  const canViewCampusRecords = user?.is_staff || ["super_admin", "college_admin", "hod", "faculty"].includes(user?.role);
  const isStudent = user?.role === "student";
  const visibleNavigation = isStudent ? studentNavigation : canViewCampusRecords ? navigation : navigation.slice(0, 1);
  const activeTitle = [...navigation, ...studentNavigation].find((item) => item.module === activeModule)?.label || "Overview";

  return (
    <div className="app-shell min-h-screen text-slate-900">
      <div aria-hidden="true" className="ambient-orb ambient-orb--blue" />
      <div aria-hidden="true" className="ambient-orb ambient-orb--violet" />
      {mobileOpen && <button aria-label="Close navigation" onClick={() => setMobileOpen(false)} className="fixed inset-0 z-30 bg-slate-950/40 backdrop-blur-sm lg:hidden" />}
      <aside className={`glass-sidebar fixed inset-y-0 left-0 z-40 flex w-[248px] flex-col transition-transform duration-300 lg:translate-x-0 ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="sidebar-brand flex h-[72px] items-center justify-between border-b px-5"><div className="flex items-center gap-3"><span className="sidebar-brand-mark grid h-9 w-9 place-items-center rounded-xl text-white"><GraduationCap size={20} /></span><span className="text-sm font-bold tracking-tight">CampusMind AI<span className="block text-[9px] font-medium tracking-[.2em] text-slate-400">CAMPUS WORKSPACE</span></span></div><button aria-label="Close navigation" onClick={() => setMobileOpen(false)} className="rounded-lg p-2 text-slate-300 transition hover:bg-white/10 hover:text-white lg:hidden"><X size={18} /></button></div>
        <div className="flex-1 overflow-y-auto px-3 pt-6"><p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[.2em] text-slate-400">Workspace</p>{visibleNavigation.map(({ label, icon: Icon, module }) => <button key={module} onClick={() => { setActiveModule(module); setMobileOpen(false); }} className={`sidebar-nav-item ${activeModule === module ? "sidebar-nav-item--active" : ""} mb-1 flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm`}><Icon size={17} />{label}</button>)}</div>
        <div className="sidebar-account mt-auto p-4"><div className="sidebar-account-card flex items-center gap-3 rounded-xl p-3"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-blue-400/20 text-xs font-semibold text-blue-100 ring-1 ring-white/15">{initials}</span><div className="min-w-0"><p className="truncate text-sm font-medium text-white">{displayName}</p><p className="truncate text-xs capitalize text-slate-400">{roleLabel}</p></div></div></div>
      </aside>
      <div className="lg:pl-[248px]">
        <header className="glass-topbar sticky top-3 z-20 mx-3 flex h-[64px] items-center justify-between rounded-2xl px-3 sm:mx-5 sm:px-5 lg:mx-7">
          <div className="flex items-center gap-3"><button aria-label="Open navigation" onClick={() => setMobileOpen(true)} className="rounded-xl p-2 text-slate-600 transition hover:bg-slate-100 lg:hidden"><Menu size={19} /></button><div className="relative hidden sm:block"><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} /><input className="glass-search h-10 w-64 rounded-xl pl-9 pr-3 text-sm outline-none placeholder:text-slate-400" placeholder="Search your campus…" /></div><p className="text-sm font-semibold sm:hidden">{activeTitle}</p></div>
          <div className="flex items-center gap-2 sm:gap-3"><button aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`} title={`Switch to ${theme === "light" ? "dark" : "light"} mode`} onClick={() => setTheme((current) => current === "light" ? "dark" : "light")} className="rounded-xl border border-slate-200/70 bg-white/40 p-2 text-slate-600 transition hover:bg-white/75 hover:text-blue-700"><span className="block transition-transform duration-300 hover:rotate-12">{theme === "light" ? <Moon size={17} /> : <Sun size={17} />}</span></button><NotificationBell /><div className="relative"><button onClick={() => setProfileOpen(!profileOpen)} className="flex items-center gap-2 rounded-xl p-1.5 transition hover:bg-slate-100/70"><span className="grid h-8 w-8 place-items-center rounded-full bg-blue-100 text-xs font-semibold text-blue-700">{initials}</span><span className="hidden max-w-32 truncate text-sm font-medium sm:block">{displayName}</span><ChevronDown size={14} className="hidden text-slate-400 sm:block" /></button>{profileOpen && <div className="absolute right-0 mt-2 w-52 rounded-xl border border-slate-200 bg-white p-2 shadow-lg"><p className="truncate px-2 py-2 text-xs text-slate-500">{user?.email}</p><button onClick={logout} className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"><LogOut size={15} />Sign out</button></div>}</div></div>
        </header>
        <main className="relative mx-auto max-w-[1500px] p-4 pt-7 sm:p-7 sm:pt-9">
          {activeModule === "subject-notes" || activeModule === "question-papers" ? <SubjectNotes kind={activeModule === "question-papers" ? "papers" : "notes"} user={user} canUpload={!isStudent && (user?.role === "faculty" || canManage)} /> : isStudent ? <StudentPortal /> : activeModule === "operations" ? <OperationsCenter canManage={canManage} /> : activeModule === "timetable" ? <TimetableManager /> : activeModule !== "overview" ? <ModuleManager key={activeModule} moduleKey={activeModule} canManage={canManage} /> : <>
          <div className="content-enter mb-7 flex flex-wrap items-end justify-between gap-3"><div><p className="text-sm font-medium text-blue-700">Campus operations</p><h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-[28px]">Good to see you, {displayName.split(" ")[0]}</h1><p className="mt-1 text-sm text-slate-500">Here’s your campus at a glance.</p></div><div className="glass-badge flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium text-slate-600"><CalendarDays size={15} className="text-blue-600" />Live overview</div></div>
          {error && <div role="alert" className="mb-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Metric icon={GraduationCap} label="Total students" value={summary?.students ?? "—"} note="Registered student records" color="bg-blue-50 text-blue-700" />
            <Metric icon={Users} label="Faculty members" value={summary?.faculty ?? "—"} note="Active faculty records" color="bg-violet-50 text-violet-700" />
            <Metric icon={Building2} label="Departments" value={summary?.departments ?? "—"} note="Active departments" color="bg-amber-50 text-amber-700" />
            <Metric icon={Activity} label="Attendance rate" value={summary ? `${summary.attendance_rate}%` : "—"} note={summary ? `${summary.attendance_records} recorded sessions` : "Based on recorded attendance"} color="bg-emerald-50 text-emerald-700" />
          </section>
          <section className="content-enter mt-5 grid gap-5 xl:grid-cols-[1.4fr_0.85fr]">
            <article className="panel min-h-[330px]"><div className="mb-6"><h2 className="text-base font-semibold">Campus snapshot</h2><p className="mt-1 text-sm text-slate-500">Current records across core campus areas</p></div>{summary && (summary.students + summary.faculty + summary.departments > 0) ? <div className="h-[235px]"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartData} margin={{ top: 5, right: 12, left: -20, bottom: 0 }}><CartesianGrid vertical={false} stroke="#eef1f6" /><XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#64748b" }} /><YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#94a3b8" }} /><Tooltip cursor={{ fill: "#f8fafc" }} /><Bar dataKey="total" fill="#3977ed" radius={[5, 5, 0, 0]} maxBarSize={54} /></BarChart></ResponsiveContainer></div> : <div className="grid h-[225px] place-items-center rounded-xl border border-dashed border-slate-200 text-center"><div><Building2 className="mx-auto text-slate-300" size={30} /><p className="mt-3 text-sm font-medium text-slate-600">{summary ? "Your campus workspace is ready" : "Loading campus records…"}</p><p className="mt-1 text-xs text-slate-400">{summary ? "Add departments, students, and faculty to see your snapshot." : "Fetching current data from your campus."}</p></div></div>}</article>
            <article className="panel"><div className="flex items-center justify-between"><div><h2 className="text-base font-semibold">Quick overview</h2><p className="mt-1 text-sm text-slate-500">Operational status</p></div><span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">Connected</span></div><div className="mt-5 divide-y divide-slate-100">{[{label:"Campus departments", value:summary?.departments}, {label:"Student records", value:summary?.students}, {label:"Faculty records", value:summary?.faculty}, {label:"Attendance entries", value:summary?.attendance_records}].map((item) => <div key={item.label} className="flex items-center justify-between py-4"><span className="text-sm text-slate-600">{item.label}</span><span className="text-sm font-semibold">{item.value ?? "—"}</span></div>)}</div><div className="mt-2 rounded-lg bg-blue-50 p-3 text-xs leading-5 text-blue-800">Use the workspace navigation to manage campus people, academics, departments, and attendance.</div></article>
          </section>
          </>}
          <footer className="mt-7 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400"><span>CampusMind AI · Campus operations workspace</span><span>Secure session · {user?.role?.replaceAll("_", " ")}</span></footer>
        </main>
      </div>
    </div>
  );
}
