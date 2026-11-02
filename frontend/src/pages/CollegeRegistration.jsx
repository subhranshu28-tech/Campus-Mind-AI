import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Building2, CheckCircle2 } from "lucide-react";
import api from "../services/api";

export default function CollegeRegistration() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ college_name: "", college_code: "", admin_name: "", username: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState(null);
  function update(event) { setForm((old) => ({ ...old, [event.target.name]: event.target.value })); }
  async function submit(event) {
    event.preventDefault(); setError(""); setBusy(true);
    try { const { data } = await api.post("/auth/register-college/", form); setCreated(data); }
    catch (err) {
      const detail = err.response?.data;
      setError(typeof detail === "string" ? detail : Object.entries(detail || {}).map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : value}`).join(" · ") || "Unable to register this college.");
    } finally { setBusy(false); }
  }
  if (created) return <main className="app-shell grid min-h-screen place-items-center p-5"><section className="login-glass-card w-full max-w-lg p-8 text-center"><CheckCircle2 className="mx-auto mb-4 text-emerald-600" size={42}/><h1 className="text-2xl font-semibold">Workspace created</h1><p className="mt-3 text-sm text-slate-600">{created.college.name} is registered. Your college administrator username is <strong>{created.user.username}</strong>.</p><button onClick={() => navigate("/login")} className="glass-button mt-6 w-full rounded-xl bg-blue-600 px-4 py-3 font-semibold text-white">Continue to sign in</button></section></main>;
  return <main className="app-shell grid min-h-screen place-items-center px-5 py-10"><form onSubmit={submit} className="login-glass-card w-full max-w-xl p-7 sm:p-9"><Link to="/login" className="mb-6 inline-flex items-center gap-2 text-sm text-blue-700"><ArrowLeft size={16}/> Back to sign in</Link><div className="mb-7"><div className="mb-4 grid h-12 w-12 place-items-center rounded-xl bg-blue-600 text-white"><Building2/></div><h1 className="text-3xl font-semibold text-slate-900">Register your college</h1><p className="mt-2 text-sm text-slate-500">Create an isolated CampusMind workspace for your institution.</p></div><div className="grid gap-4 sm:grid-cols-2">{[["college_name","College name","text"],["college_code","Unique college code","text"],["admin_name","Administrator full name","text"],["username","Administrator username","text"],["email","Administrator email","email"],["password","Password (10+ characters)","password"]].map(([name,label,type])=><label key={name} className="text-sm font-medium text-slate-700">{label}<input required name={name} type={type} minLength={type === "password" ? 10 : undefined} value={form[name]} onChange={update} className="field mt-2" autoComplete={type === "password" ? "new-password" : "off"}/></label>)}</div>{error && <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<button disabled={busy} className="glass-button mt-6 w-full rounded-xl bg-blue-600 px-4 py-3 font-semibold text-white disabled:opacity-60">{busy ? "Creating workspace…" : "Create college workspace"}</button><p className="mt-4 text-xs leading-5 text-slate-400">Registration is rate-limited. College codes must be unique. Existing data is not shared with this new workspace.</p></form></main>;
}
