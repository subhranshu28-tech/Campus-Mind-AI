import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api from "../services/api";

export default function PasswordReset() {
  const [params] = useSearchParams();
  const uid = params.get("uid") || "";
  const token = params.get("token") || "";
  const validLink = Boolean(uid && token);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const title = useMemo(() => validLink ? "Choose a new password" : "Reset your password", [validLink]);

  async function submit(event) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try {
      if (validLink) {
        if (password !== confirm) throw new Error("Passwords do not match.");
        await api.post("/auth/password-reset/confirm/", { uid, token, new_password: password });
        setMessage("Password updated. You can now sign in.");
      } else {
        await api.post("/auth/password-reset/", { email });
        setMessage("If an account exists for that email, reset instructions will be sent.");
      }
    } catch (err) {
      setError(err.message || err.response?.data?.detail || "Unable to complete the request. Check the details and try again.");
    } finally { setBusy(false); }
  }

  return <main className="grid min-h-screen place-items-center bg-slate-50 px-5 py-10"><form onSubmit={submit} className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-7 shadow-xl"><p className="text-xs font-semibold uppercase tracking-widest text-blue-600">CampusMind AI</p><h1 className="mt-3 text-2xl font-semibold text-slate-900">{title}</h1><p className="mt-2 text-sm text-slate-500">{validLink ? "Use at least 10 characters for your new password." : "Enter your account email to receive password reset instructions."}</p>
    {!validLink ? <label className="mt-6 block text-sm font-medium">Email<input className="field mt-2" type="email" required autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} /></label> : <><label className="mt-6 block text-sm font-medium">New password<input className="field mt-2" type="password" minLength={10} required autoComplete="new-password" value={password} onChange={e=>setPassword(e.target.value)} /></label><label className="mt-4 block text-sm font-medium">Confirm password<input className="field mt-2" type="password" minLength={10} required autoComplete="new-password" value={confirm} onChange={e=>setConfirm(e.target.value)} /></label></>}
    {error && <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}{message && <p role="status" className="mt-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">{message}</p>}<button disabled={busy} className="mt-6 w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-60">{busy ? "Please wait…" : validLink ? "Update password" : "Send reset instructions"}</button><Link className="mt-5 block text-center text-sm text-blue-600 hover:underline" to="/login">Back to sign in</Link></form></main>;
}
