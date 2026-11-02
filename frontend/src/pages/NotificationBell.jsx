import { useCallback, useEffect, useState } from "react";
import { Bell, CheckCheck } from "lucide-react";
import api from "../services/api";

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);

  const load = useCallback(() => {
    api.get("/notifications/").then(({ data }) => { setItems(data.results); setUnread(data.unread); }).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, 60000);
    return () => clearInterval(timer);
  }, [load]);

  const markAll = async () => { await api.post("/notifications/read-all/"); load(); };

  return (
    <div className="relative">
      <button aria-label="Notifications" onClick={() => { setOpen(!open); if (!open) load(); }} className="relative rounded-xl p-2 text-slate-500 transition hover:bg-slate-100/70">
        <Bell size={18} />
        {unread > 0 && <span className="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-blue-600 px-1 text-[10px] font-semibold text-white">{unread > 9 ? "9+" : unread}</span>}
      </button>
      {open && (
        <div className="absolute right-0 z-40 mt-2 w-80 max-w-[88vw] rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
          <div className="flex items-center justify-between px-2 py-1.5">
            <p className="text-sm font-semibold text-slate-800">Notifications</p>
            <button onClick={markAll} className="inline-flex items-center gap-1 text-xs font-medium text-blue-700"><CheckCheck size={13} />Mark all read</button>
          </div>
          <div className="max-h-80 divide-y divide-slate-100 overflow-y-auto">
            {items.length === 0 && <p className="px-2 py-6 text-center text-xs text-slate-500">You're all caught up.</p>}
            {items.map((item) => (
              <article key={item.id} className={`px-2 py-2.5 ${item.is_read ? "opacity-60" : ""}`}>
                <p className="text-sm font-medium text-slate-800">{item.title}</p>
                <p className="mt-0.5 text-xs leading-5 text-slate-600">{item.message}</p>
                <p className="mt-1 text-[10px] text-slate-400">{new Date(item.created_at).toLocaleString()}</p>
              </article>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
