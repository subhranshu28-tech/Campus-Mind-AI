import { useState } from "react";
import { Bot, Send, Sparkles } from "lucide-react";
import api from "../services/api";

export default function AIAssistant() {
  const [messages, setMessages] = useState([{ role: "assistant", content: "Hello! I can help with academic planning, timetable concepts, campus workflows and study questions. I do not automatically access private campus records." }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function send(event) {
    event.preventDefault(); const message = input.trim(); if (!message || busy) return;
    setMessages(current => [...current, { role: "user", content: message }]); setInput(""); setError(""); setBusy(true);
    try {
      const { data } = await api.post("/ai/chat/", { message });
      setMessages(current => [...current, { role: "assistant", content: data.answer }]);
    } catch (err) {
      setError(err.response?.data?.detail || "The assistant could not respond. Please try again.");
    } finally { setBusy(false); }
  }
  return <main className="mx-auto flex min-h-screen max-w-4xl flex-col bg-slate-50 px-4 py-8"><header className="mb-6 flex items-center gap-3"><span className="grid h-11 w-11 place-items-center rounded-xl bg-blue-600 text-white"><Bot /></span><div><p className="text-lg font-semibold text-slate-900">CampusMind AI</p><p className="text-xs text-slate-500">Academic and campus assistant</p></div></header><section aria-live="polite" className="flex-1 space-y-4 rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">{messages.map((item, index) => <div key={index} className={`max-w-[90%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-6 ${item.role === "user" ? "ml-auto bg-blue-600 text-white" : "bg-slate-100 text-slate-800"}`}>{item.content}</div>)}{busy && <p className="text-sm text-slate-500">Thinking…</p>}{error && <p role="alert" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">{error}</p>}</section><form onSubmit={send} className="mt-4 flex gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm"><label className="sr-only" htmlFor="ai-message">Message CampusMind AI</label><input id="ai-message" className="min-w-0 flex-1 border-0 px-3 text-sm outline-none focus:ring-0" placeholder="Ask about academic planning…" value={input} onChange={e=>setInput(e.target.value)} maxLength={4000} /><button aria-label="Send message" disabled={busy || !input.trim()} className="grid h-11 w-11 place-items-center rounded-xl bg-blue-600 text-white disabled:opacity-50"><Send size={17}/></button></form><p className="mt-3 flex items-center justify-center gap-1 text-center text-xs text-slate-400"><Sparkles size={12}/> AI responses may be inaccurate. Verify important academic or administrative decisions.</p></main>;
}
