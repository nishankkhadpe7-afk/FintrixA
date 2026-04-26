"use client";

import { useEffect, useState } from "react";
import ConnectedShell from "../../components/ConnectedShell";
import { useTheme } from "../../components/ThemeProvider";
import { getApiBaseUrl } from "../../lib/api";

export default function NewsPage() {
  const API_BASE = getApiBaseUrl();
  const { darkMode } = useTheme();
  const [items, setItems] = useState([]);

  useEffect(() => {
    let active = true;

    async function loadNews() {
      try {
        const response = await fetch(`${API_BASE}/api/news`, { cache: "no-store" });
        if (!response.ok) {
          if (active) setItems([]);
          return;
        }
        const data = await response.json();
        if (active) setItems(Array.isArray(data) ? data : []);
      } catch {
        if (active) setItems([]);
      }
    }

    loadNews();
    return () => {
      active = false;
    };
  }, []);

  return (
    <ConnectedShell
      title="News"
      description="Live finance and compliance news pulled directly from the connected S92 backend."
    >
      <div className="mt-8 grid gap-5 lg:grid-cols-2">
        {items.length ? (
          items.slice(0, 8).map((item, index) => (
            <article
              key={`${item.id ?? index}-${item.title}`}
              className={`overflow-hidden rounded-2xl border ${
                darkMode ? "border-white/14 bg-white/10" : "border-fintrix-dark/10 bg-white"
              }`}
            >
              {item.image_url ? (
                <img
                  src={item.image_url}
                  alt={item.title || "News image"}
                  className="h-44 w-full object-cover sm:h-52"
                />
              ) : (
                <div
                  className={`flex h-52 w-full items-center justify-center text-base font-medium ${
                    darkMode ? "bg-white/5 text-white/70" : "bg-[#eef4eb] text-fintrix-ink/70"
                  }`}
                >
                  No preview image
                </div>
              )}
              <div className="p-4 sm:p-5">
                <p className={`text-sm font-semibold uppercase tracking-[0.2em] ${darkMode ? "text-fintrix-accent" : "text-fintrix-dark"}`}>
                  {item.source || "FinTrix"}
                </p>
                <h2 className={`mt-3 text-lg font-semibold sm:text-xl ${darkMode ? "text-white" : "text-fintrix-dark"}`}>
                  {item.title}
                </h2>
                <p className={`mt-3 text-base font-medium leading-7 ${darkMode ? "text-white/88" : "text-fintrix-ink/80"}`}>
                  {item.description || item.content || "No description available."}
                </p>
                {item.url ? (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    className={`mt-4 inline-flex text-base font-semibold ${darkMode ? "text-fintrix-accent" : "text-fintrix-dark"}`}
                  >
                    Read article
                  </a>
                ) : null}
              </div>
            </article>
          ))
        ) : (
          <div
            className={`rounded-2xl border p-5 text-base font-medium ${
              darkMode ? "border-white/14 bg-white/10 text-white/88" : "border-fintrix-dark/10 bg-white text-fintrix-ink/80"
            }`}
          >
            No news available from the backend right now.
          </div>
        )}
      </div>
    </ConnectedShell>
  );
}
