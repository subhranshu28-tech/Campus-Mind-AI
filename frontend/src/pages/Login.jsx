import { useState } from "react";
import { ArrowRight, GraduationCap, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { Link } from "react-router-dom";

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(username, password);
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to sign in. Check your credentials and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app-shell grid min-h-screen lg:grid-cols-[1fr_0.85fr]">
      <section className="relative hidden overflow-hidden bg-[linear-gradient(145deg,#101b31,#1c2a4d_58%,#232c53)] p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div aria-hidden="true" className="login-orb login-orb--one" />
        <div aria-hidden="true" className="login-orb login-orb--two" />
        <div className="relative flex items-center gap-3 content-enter"><span className="sidebar-brand-mark grid h-11 w-11 place-items-center rounded-xl"><GraduationCap size={24} /></span><span className="font-semibold tracking-tight">CampusMind AI<span className="block text-xs font-normal tracking-[.2em] text-slate-400">CAMPUS WORKSPACE</span></span></div>
        <div className="relative max-w-lg content-enter"><p className="mb-4 text-sm font-medium uppercase tracking-[.18em] text-blue-300">One campus. Connected.</p><h1 className="text-5xl font-semibold leading-tight tracking-tight">A smarter way to run your campus.</h1><p className="mt-6 max-w-md text-lg leading-8 text-slate-300">Bring academic operations and campus teams together in one secure workspace.</p></div>
        <p className="relative text-sm text-slate-400">Secure access for your campus community</p>
      </section>
      <section className="flex items-center justify-center px-5 py-10 sm:px-8">
        <form className="login-glass-card content-enter w-full max-w-[430px] p-6 sm:p-9" onSubmit={submit}>
          <div className="mb-10 flex items-center gap-3 lg:hidden"><span className="grid h-10 w-10 place-items-center rounded-xl bg-blue-600 text-white"><GraduationCap size={22} /></span><span className="font-semibold">CampusMind AI</span></div>
          <div className="mb-8"><div className="glass-badge mb-4 inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium text-blue-700"><ShieldCheck size={14} />Authorized campus access</div><h2 className="text-3xl font-semibold tracking-tight text-slate-900">Welcome back</h2><p className="mt-2 text-sm text-slate-500">Sign in with your campus account to continue.</p></div>
          <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="username">Username</label>
          <input id="username" autoComplete="username" required value={username} onChange={(e) => setUsername(e.target.value)} className="field mb-5" placeholder="Your campus username" />
          <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} className="field mb-5" placeholder="Enter your password" />
          <div className="mb-4 text-right"><Link to="/password-reset" className="text-sm font-medium text-blue-600 hover:underline">Forgot password?</Link></div>
          {error && <p role="alert" className="mb-4 rounded-lg bg-red-50 px-3 py-2.5 text-sm text-red-700">{error}</p>}
          <button disabled={busy} className="glass-button flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-wait disabled:opacity-60">{busy ? "Signing in…" : "Sign in"}{!busy && <ArrowRight size={16} />}</button>
          <p className="mt-6 text-center text-xs leading-5 text-slate-400">Access is managed by your campus administrator. Contact them if you need help signing in.</p><p className="mt-4 text-center text-sm text-slate-500">Register a new college? <Link to="/register-college" className="font-semibold text-blue-600 hover:underline">Create a workspace</Link></p>
        </form>
      </section>
    </main>
  );
}
