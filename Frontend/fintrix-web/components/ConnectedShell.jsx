"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./AuthProvider";
import { useTheme } from "./ThemeProvider";
import Navbar from "./Navbar";

export default function ConnectedShell({ title, description, children }) {
  const router = useRouter();
  const { isAuthenticated, isReady } = useAuth();
  const { darkMode, toggleTheme } = useTheme();

  useEffect(() => {
    if (isReady && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, isReady, router]);

  if (!isReady || !isAuthenticated) {
    return (
      <main className={`min-h-screen pt-20 px-3 py-5 sm:px-6 sm:py-8 lg:px-8 ${darkMode ? "bg-fintrix-dark" : "bg-fintrix-bg"}`}>
        <div className="mx-auto max-w-6xl">
          <Navbar darkMode={darkMode} onToggleTheme={toggleTheme} />
        </div>
        <div className="mt-20 w-full">
          <div className={`rounded-[28px] border p-6 shadow-[0_24px_60px_rgba(0,0,0,0.25)] backdrop-blur-2xl sm:p-8 ${darkMode ? "border-white/18 bg-white/12 text-white" : "border-fintrix-dark/10 bg-white text-fintrix-ink"}`}>
            <div className={`text-sm ${darkMode ? "text-white/75" : "text-fintrix-muted"}`}>Checking your session...</div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className={`min-h-screen pt-20 px-3 py-5 sm:px-6 sm:py-8 lg:px-8 ${darkMode ? "bg-fintrix-dark" : "bg-fintrix-bg"}`}>
      <div className="mx-auto max-w-6xl">
        <Navbar darkMode={darkMode} onToggleTheme={toggleTheme} />
      </div>

      <div
        className={`mt-20 w-full rounded-[24px] border p-4 shadow-[0_24px_60px_rgba(0,0,0,0.25)] backdrop-blur-2xl sm:mt-24 sm:rounded-[28px] sm:p-8 ${
          darkMode
            ? "border-white/18 bg-white/12 text-white"
            : "border-fintrix-dark/10 bg-white text-fintrix-ink"
        }`}
      >
        <div className="space-y-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-[-0.04em] sm:text-4xl">{title}</h1>
            <p className={`mt-4 max-w-3xl text-base font-medium leading-7 sm:text-lg sm:leading-8 ${darkMode ? "text-white/85" : "text-fintrix-muted"}`}>
              {description}
            </p>
          </div>
        </div>
        <div className="mt-6 sm:mt-8">{children}</div>
      </div>
    </main>
  );
}
