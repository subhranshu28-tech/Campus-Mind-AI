import { useEffect, useState } from "react";
import { BookOpen, Download, FileText, Sparkles, Trash2, Upload } from "lucide-react";
import api from "../services/api";

export default function SubjectNotes({ canUpload = false, user, kind = "notes" }) {
  const isPaperLibrary = kind === "papers";
  const endpoint = isPaperLibrary ? "/question-papers/" : "/subject-notes/";
  const heading = isPaperLibrary ? "Previous year question papers" : "Subject notes";
  const [notes, setNotes] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [subject, setSubject] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [examYear, setExamYear] = useState("");
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function loadNotes() {
    setError("");
    try {
      const { data } = await api.get(endpoint);
      setNotes(data.results || data);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Subject notes could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    loadNotes();
    if (canUpload) {
      api.get(`${endpoint}subjects/`)
        .then(({ data }) => { if (active) setSubjects(data); })
        .catch((requestError) => {
          if (active) setError(requestError.response?.data?.detail || "Your teaching subjects could not be loaded.");
        });
    }
    return () => { active = false; };
  }, [canUpload, endpoint]);

  async function uploadNote(event) {
    event.preventDefault();
    if (!file) {
      setError("Choose a PDF file to upload.");
      return;
    }
    const formData = new FormData();
    formData.append("subject", subject);
    formData.append("title", title);
    formData.append("description", description);
    if (isPaperLibrary) formData.append("exam_year", examYear);
    formData.append("file", file);
    setSaving(true);
    setError("");
    try {
      await api.post(endpoint, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setTitle("");
      setDescription("");
      setExamYear("");
      setFile(null);
      event.target.reset();
      await loadNotes();
    } catch (requestError) {
      const details = requestError.response?.data;
      setError(details?.subject?.[0] || details?.file?.[0] || details?.title?.[0] || details?.exam_year?.[0] || details?.detail || "The PDF could not be uploaded.");
    } finally {
      setSaving(false);
    }
  }

  async function downloadNote(note) {
    setError("");
    try {
      const { data } = await api.get(`${endpoint}${note.id}/download/`, { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const link = document.createElement("a");
      link.href = url;
      link.download = note.file_name;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "The PDF could not be downloaded.");
    }
  }

  async function deleteNote(noteId) {
    setError("");
    try {
      await api.delete(`${endpoint}${noteId}/`);
      setNotes((current) => current.filter((note) => note.id !== noteId));
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "The PDF could not be deleted.");
    }
  }

  return <div className="content-enter">
    <section className="resource-hero mb-6">
      <div className="resource-hero__copy">
        <span className="resource-kicker"><Sparkles size={13} /> {isPaperLibrary ? "EXAM PREPARATION" : "LEARNING RESOURCES"}</span>
        <p className="mt-4 text-sm font-medium text-blue-700">{canUpload ? "Faculty workspace" : "Student workspace"}</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-[32px]">{heading}</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">{canUpload ? (isPaperLibrary ? "Share previous exam papers with the students taking your subjects." : "Upload course PDFs for students in your assigned sections.") : (isPaperLibrary ? "Browse and download previous exam papers for your subjects." : "Download PDFs shared by your teachers for your subjects.")}</p>
      </div>
      <div className={`resource-art ${isPaperLibrary ? "resource-art--papers" : ""}`} aria-hidden="true">
        <div className="resource-art__glow" />
        <div className="resource-orbit resource-orbit--one" />
        <div className="resource-orbit resource-orbit--two" />
        <div className="resource-sheet resource-sheet--back" />
        <div className="resource-sheet resource-sheet--middle" />
        <div className="resource-sheet resource-sheet--front">
          <div className="resource-sheet__icon"><FileText size={22} /></div>
          <span className="resource-sheet__line resource-sheet__line--strong" />
          <span className="resource-sheet__line" />
          <span className="resource-sheet__line resource-sheet__line--short" />
          <span className="resource-sheet__tag">{isPaperLibrary ? "PAST PAPERS" : "STUDY NOTES"}</span>
        </div>
        <span className="resource-float resource-float--top"><BookOpen size={16} /></span>
        <span className="resource-float resource-float--bottom"><Sparkles size={15} /></span>
      </div>
    </section>
    {error && <div role="alert" className="mb-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
    <div className={canUpload ? "grid gap-5 xl:grid-cols-[0.8fr_1.2fr]" : ""}>
      {canUpload && <form className="panel h-fit" onSubmit={uploadNote}>
        <div className="mb-4 flex items-center gap-2"><Upload size={18} className="text-blue-600" /><h2 className="text-base font-semibold">{isPaperLibrary ? "Upload question paper" : "Upload subject PDF"}</h2></div>
        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="note-subject">Subject</label>
        <select id="note-subject" className="field mb-4" required value={subject} onChange={(event) => setSubject(event.target.value)}><option value="">Select an assigned subject</option>{subjects.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}</select>
        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="note-title">Title</label>
        <input id="note-title" className="field mb-4" maxLength={160} required value={title} onChange={(event) => setTitle(event.target.value)} placeholder={isPaperLibrary ? "e.g. 2024 end-semester paper" : "e.g. Unit 1 lecture notes"} />
        {isPaperLibrary && <><label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="exam-year">Exam year</label><input id="exam-year" className="field mb-4" type="number" min="1950" max={new Date().getFullYear()} required value={examYear} onChange={(event) => setExamYear(event.target.value)} placeholder={String(new Date().getFullYear() - 1)} /></>}
        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="note-description">Description <span className="font-normal text-slate-400">(optional)</span></label>
        <textarea id="note-description" className="field mb-4 min-h-24 resize-y py-3" maxLength={2000} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="What should students know about this resource?" />
        <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="note-file">PDF file <span className="font-normal text-slate-400">(max 20 MB)</span></label>
        <input id="note-file" className="field mb-4 py-2.5 file:mr-3 file:rounded-lg file:border-0 file:bg-blue-50 file:px-3 file:py-1 file:text-sm file:font-medium file:text-blue-700" type="file" accept="application/pdf,.pdf" required onChange={(event) => setFile(event.target.files?.[0] || null)} />
        <button disabled={saving || !subjects.length} className="glass-button flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"><Upload size={16} />{saving ? "Uploading…" : isPaperLibrary ? "Upload question paper" : "Upload PDF"}</button>
      </form>}
      <section className="panel">
        <div className="mb-5 flex items-center justify-between"><div><h2 className="text-base font-semibold">{isPaperLibrary ? "Available past papers" : canUpload ? "Shared subject PDFs" : "Notes from your teachers"}</h2><p className="mt-1 text-sm text-slate-500">{notes.length} {notes.length === 1 ? "PDF" : "PDFs"}</p></div><FileText className="text-blue-600" size={19} /></div>
        {loading ? <p className="py-12 text-center text-sm text-slate-500">Loading subject PDFs…</p> : notes.length ? <div className="space-y-3">{notes.map((note) => <article key={note.id} className="flex items-start justify-between gap-3 rounded-xl border border-slate-100 bg-white/55 p-4"><div className="flex min-w-0 items-start gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-red-50 text-red-600"><FileText size={19} /></span><div className="min-w-0"><span className="text-xs font-semibold text-blue-700">{note.subject_code} · {note.subject_name}{isPaperLibrary ? ` · ${note.exam_year}` : ""}</span><h3 className="mt-1 break-words text-sm font-semibold text-slate-900">{note.title}</h3>{note.description && <p className="mt-1 whitespace-pre-wrap break-words text-sm leading-5 text-slate-600">{note.description}</p>}<p className="mt-2 text-xs text-slate-400">{note.file_name} · Uploaded by {note.uploaded_by_name || "faculty"} · {new Date(note.uploaded_at).toLocaleDateString()}</p></div></div><div className="flex shrink-0 items-center gap-1"><button aria-label={`Download ${note.title}`} title="Download PDF" onClick={() => downloadNote(note)} className="rounded-lg p-2 text-blue-600 transition hover:bg-blue-50"><Download size={17} /></button>{canUpload && (user?.role !== "faculty" || note.uploaded_by_id === user.id) && <button aria-label={`Delete ${note.title}`} title="Delete PDF" onClick={() => deleteNote(note.id)} className="rounded-lg p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600"><Trash2 size={16} /></button>}</div></article>)}</div> : <div className="grid min-h-48 place-items-center rounded-xl border border-dashed border-slate-200 text-center"><div><BookOpen className="mx-auto text-slate-300" size={28} /><p className="mt-3 text-sm font-medium text-slate-600">{isPaperLibrary ? "No previous papers yet" : "No subject PDFs yet"}</p><p className="mt-1 text-xs text-slate-400">{canUpload ? (isPaperLibrary ? "Upload a past paper and it will be available to students assigned to that subject." : "Upload a PDF and it will be available to students assigned to that subject.") : (isPaperLibrary ? "Your teachers’ uploaded question papers will appear here." : "Your teacher’s uploaded notes will appear here.")}</p></div></div>}
      </section>
    </div>
  </div>;
}
