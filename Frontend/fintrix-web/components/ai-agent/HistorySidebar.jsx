"use client";

function formatTimestamp(value) {
  if (!value) return "";
  const input = typeof value === "string" && /\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}/.test(value) && !/[zZ]|[+-]\d{2}:?\d{2}$/.test(value)
    ? `${value.replace(" ", "T")}Z`
    : value;
  const date = new Date(input);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function HistorySidebar({
  darkMode,
  sessions,
  activeSessionId,
  onSelectSession,
  onDeleteSession,
  onNewChat,
  isMobileOpen,
  onToggleMobile,
}) {
  return (
    <aside
      className={`flex min-h-0 flex-col overflow-hidden rounded-3xl border shadow-soft ${
        darkMode
          ? "border-white/14 bg-[#0d2948] text-white"
          : "border-fintrix-dark/10 bg-white text-fintrix-ink"
      }`}
    >
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-4 sm:px-5">
        <h2 className="text-lg font-semibold">History</h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onNewChat}
            className={`rounded-xl px-3 py-2 text-xs font-semibold transition ${
              darkMode
                ? "bg-white/12 text-white hover:bg-white/18"
                : "bg-fintrix-accent text-fintrix-dark hover:opacity-90"
            }`}
          >
            New Chat
          </button>
          <button
            type="button"
            onClick={onToggleMobile}
            className={`rounded-xl px-3 py-2 text-xs font-semibold transition md:hidden ${
              darkMode
                ? "bg-white/12 text-white hover:bg-white/18"
                : "bg-fintrix-bg text-fintrix-ink hover:bg-fintrix-accent/70"
            }`}
            aria-expanded={isMobileOpen}
          >
            {isMobileOpen ? "Hide" : "Show"}
          </button>
        </div>
      </div>

      <div
        className={`${isMobileOpen ? "block max-h-[50vh]" : "hidden"} min-h-0 overflow-y-auto p-3 md:block md:flex-1 md:max-h-none md:min-h-0`}
      >
        {sessions.length ? (
          <div className="space-y-2">
            {sessions.map((session) => {
              const isActive = session.id === activeSessionId;
              return (
                <button
                  key={session.id}
                  type="button"
                  onClick={() => onSelectSession(session.id)}
                  className={`w-full rounded-2xl border px-3 py-3 text-left transition ${
                    isActive
                      ? darkMode
                        ? "border-fintrix-accent/60 bg-fintrix-accent/20"
                        : "border-fintrix-dark/20 bg-fintrix-accent/40"
                      : darkMode
                        ? "border-white/10 bg-white/5 hover:bg-white/10"
                        : "border-fintrix-dark/10 bg-fintrix-bg/40 hover:bg-fintrix-accent/20"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold">{session.title || "New chat"}</p>
                      <p className={`mt-1 text-xs ${darkMode ? "text-white/70" : "text-fintrix-ink/65"}`}>
                        {formatTimestamp(session.updatedAt || session.createdAt)}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        onDeleteSession(session.id);
                      }}
                      className={`inline-flex h-8 w-8 items-center justify-center rounded-lg border transition ${
                        darkMode
                          ? "border-white/14 text-white/85 hover:bg-white/12"
                          : "border-fintrix-dark/15 text-fintrix-ink hover:bg-fintrix-bg"
                      }`}
                      aria-label="Delete chat"
                    >
                      <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M3 6h18" />
                        <path d="M8 6V4h8v2" />
                        <path d="M19 6l-1 14H6L5 6" />
                        <path d="M10 11v6" />
                        <path d="M14 11v6" />
                      </svg>
                    </button>
                  </div>
                </button>
              );
            })}
          </div>
        ) : (
          <div className={`rounded-2xl border px-4 py-4 text-sm ${darkMode ? "border-white/10 bg-white/5 text-white/80" : "border-fintrix-dark/10 bg-fintrix-bg/40 text-fintrix-ink/75"}`}>
            No chat history yet.
          </div>
        )}
      </div>
    </aside>
  );
}
