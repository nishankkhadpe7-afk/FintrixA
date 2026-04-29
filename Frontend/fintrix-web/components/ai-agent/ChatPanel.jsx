"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";

const STARTER_PROMPTS = [
  "What is Basel III?",
  "Explain SEBI margin rules",
  "How does a credit default swap work?",
];

function buildSourceHref(apiBase, source) {
  if (typeof source?.url === "string" && source.url) {
    if (source.url.startsWith("http://") || source.url.startsWith("https://")) {
      return source.url;
    }
    return `${apiBase}${source.url}`;
  }

  if (typeof source?.file === "string" && source.file) {
    const page = source?.page ? `#page=${source.page}` : "";
    return `${apiBase}/docs/${encodeURIComponent(source.file)}${page}`;
  }

  return "";
}

function SourceDisclosure({ sources, darkMode, messageId, apiBase, sourceReliability }) {
  const [open, setOpen] = useState(false);

  if (!Array.isArray(sources) || !sources.length) {
    return null;
  }

  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className={`flex w-full items-center justify-between rounded-2xl border px-4 py-3 text-left text-sm font-semibold transition-all duration-200 ${
          darkMode
            ? "border-white/14 bg-[#0b355f] text-white hover:bg-[#10416f]"
            : "border-fintrix-dark/10 bg-fintrix-bg/60 text-fintrix-ink hover:bg-fintrix-accent/70"
        }`}
        aria-expanded={open}
        aria-controls={`sources-${messageId}`}
      >
        <span>Sources</span>
        <span className={`text-xs uppercase tracking-[0.2em] ${open ? "opacity-100" : "opacity-70"}`}>
          {open ? "Hide" : "Show"}
        </span>
      </button>
      <div
        id={`sources-${messageId}`}
        className={`fintrix-collapse overflow-hidden transition-all duration-200 ${
          open ? "mt-3 max-h-48 opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        {sourceReliability ? (
          <div
            className={`mb-3 rounded-xl border px-3 py-2 text-xs ${
              darkMode
                ? "border-white/14 bg-[#0b355f] text-white/90"
                : "border-fintrix-dark/10 bg-white text-fintrix-ink"
            }`}
          >
            <span className="font-semibold">Reliability:</span>{" "}
            {sourceReliability.label || "N/A"}
            {typeof sourceReliability.score === "number"
              ? ` (${Math.round(sourceReliability.score * 100)}%)`
              : ""}
            {sourceReliability.reason ? ` - ${sourceReliability.reason}` : ""}
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2">
          {sources.map((source, index) => {
            const label = source?.file
              ? source.page
                ? `${source.file} p.${source.page}`
                : source.file
              : source?.label || source?.title || `Source ${index + 1}`;

            const href = buildSourceHref(apiBase, source);

            return (
              <a
                key={`${label}-${index}`}
                href={href || undefined}
                target="_blank"
                rel="noreferrer noopener"
                className={`rounded-full border px-3 py-2 text-xs font-semibold ${
                  darkMode
                    ? "border-white/14 bg-white/12 text-white hover:bg-white/18"
                    : "border-fintrix-dark/10 bg-white text-fintrix-ink hover:bg-fintrix-bg"
                }`}
                aria-disabled={!href}
                onClick={(event) => {
                  if (!href) {
                    event.preventDefault();
                  }
                }}
              >
                {label}
              </a>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function AssistantBubble({ message, darkMode, apiBase }) {
  const mutedCard = message.result.is_off_topic;

  return (
    <div
      className={`fintrix-message-enter max-w-full rounded-3xl border px-4 py-4 shadow-soft sm:px-5 ${
        mutedCard
          ? darkMode
            ? "border-amber-300/30 bg-[#0d335a] text-white"
            : "border-amber-300 bg-amber-50 text-fintrix-ink/80"
          : darkMode
            ? "border-white/14 bg-[#0b355f] text-white"
            : "border-fintrix-dark/10 bg-white text-fintrix-ink"
      }`}
    >
      <div className="flex items-center gap-3">
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${
            mutedCard
              ? darkMode
                ? "bg-amber-300/15 text-amber-100"
                : "bg-amber-100 text-amber-800"
              : darkMode
                ? "bg-white/10 text-white"
                : "bg-fintrix-accent text-fintrix-dark"
          }`}
        >
          {mutedCard ? "Out of scope" : message.result.mode || "AI"}
        </span>
      </div>

      <p className={`mt-3 text-sm leading-7 sm:text-base ${mutedCard ? "opacity-90" : ""}`}>
        {message.result.answer}
      </p>

      {Array.isArray(message.result.key_points) && message.result.key_points.length ? (
        <div className="mt-4 grid gap-2">
          {message.result.key_points.map((point, index) => (
            <div
              key={`${point}-${index}`}
              className={`rounded-2xl border px-4 py-3 text-sm leading-6 ${
                darkMode
                  ? mutedCard
                    ? "border-amber-200/20 bg-white/5 text-white/88"
                    : "border-white/12 bg-white/8 text-white/90"
                  : mutedCard
                    ? "border-amber-200 bg-white/60 text-fintrix-ink/80"
                    : "border-fintrix-dark/10 bg-fintrix-bg/60 text-fintrix-ink"
              }`}
            >
              {point}
            </div>
          ))}
        </div>
      ) : null}

      {!message.result.is_off_topic ? (
        <SourceDisclosure
          darkMode={darkMode}
          sources={message.result.sources}
          messageId={message.id}
          apiBase={apiBase}
          sourceReliability={message.result.source_reliability}
        />
      ) : null}
    </div>
  );
}

function TypingBubble({ darkMode }) {
  return (
    <div
      className={`fintrix-message-enter inline-flex items-center rounded-3xl border px-4 py-4 ${
        darkMode
          ? "border-white/14 bg-[#0b355f] text-white"
          : "border-fintrix-dark/10 bg-white text-fintrix-ink"
      }`}
    >
      <div className="fintrix-typing-indicator" aria-label="Assistant is typing">
        <span className="fintrix-typing-dot" />
        <span className="fintrix-typing-dot" />
        <span className="fintrix-typing-dot" />
      </div>
    </div>
  );
}

function ChatMessage({ message, darkMode, apiBase }) {
  if (message.role === "user") {
    return (
      <div className="fintrix-message-enter ml-auto w-full max-w-full rounded-3xl rounded-br-xl bg-fintrix-accent/70 px-4 py-4 text-sm text-fintrix-dark shadow-soft sm:max-w-2xl sm:px-5 sm:text-base">
        {message.text}
      </div>
    );
  }

  if (message.pending) {
    return <TypingBubble darkMode={darkMode} />;
  }

  return <AssistantBubble darkMode={darkMode} message={message} apiBase={apiBase} />;
}

export default function ChatPanel({
  darkMode,
  apiBase,
  messages,
  loading,
  onSendQuestion,
  onNewChat,
  activeTitle,
}) {
  const [question, setQuestion] = useState("");
  const [shortcutLabel, setShortcutLabel] = useState("Ctrl+Enter");
  const endRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    if (!textareaRef.current) {
      return;
    }

    const textarea = textareaRef.current;
    textarea.style.height = "0px";
    const computedStyles = window.getComputedStyle(textarea);
    const lineHeight = Number.parseFloat(computedStyles.lineHeight) || 24;
    const maxHeight = lineHeight * 5;
    const nextHeight = Math.min(textarea.scrollHeight, maxHeight);
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > maxHeight ? "auto" : "hidden";
  }, [question]);

  useEffect(() => {
    if (typeof window !== "undefined" && window.navigator.platform.toLowerCase().includes("mac")) {
      setShortcutLabel("Cmd+Enter");
    }
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  async function submitQuestion(rawQuestion) {
    const askedQuestion = rawQuestion.trim();
    if (!askedQuestion || loading) {
      return;
    }

    setQuestion("");
    await onSendQuestion(askedQuestion);
  }

  function handleSubmit(event) {
    event.preventDefault();
    submitQuestion(question);
  }

  function handleStarterPrompt(prompt) {
    setQuestion(prompt);
    submitQuestion(prompt);
  }

  function handleKeyDown(event) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      submitQuestion(question);
    }
  }

  return (
    <section
      className={`flex min-h-0 flex-1 flex-col rounded-3xl border shadow-soft ${
        darkMode
          ? "border-white/14 bg-[#0d2948] text-white"
          : "border-fintrix-dark/10 bg-white text-fintrix-ink"
      }`}
    >
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-4 sm:px-5">
        <div>
          <h2 className="text-lg font-semibold">{activeTitle ? "Chat" : "AI Agent"}</h2>
          <p className={`mt-1 text-xs ${darkMode ? "text-white/75" : "text-fintrix-ink/70"}`}>
            {activeTitle || "Ask the connected AI backend a finance or compliance question."}
          </p>
        </div>
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
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4 sm:px-5" style={{ maxHeight: "calc(100vh - 280px)" }}>
        {!messages.length ? (
          <section
            className={`flex flex-col items-center justify-center rounded-3xl border px-6 py-12 text-center shadow-soft sm:px-8 ${
              darkMode
                ? "border-white/12 bg-white/8 text-white"
                : "border-fintrix-dark/10 bg-fintrix-bg/30 text-fintrix-ink"
            }`}
          >
            <div className="relative mb-6 h-16 w-16 overflow-hidden rounded-3xl border border-fintrix-accent/30 bg-fintrix-dark/5 p-2">
              <Image
                src={darkMode ? "/ai-agent-logo-lightpng.png" : "/ai-agent-logo.png"}
                alt="FinTrix AI"
                fill
                className="object-contain p-2"
                sizes="64px"
              />
            </div>
            <h2 className="text-xl font-semibold sm:text-2xl">Ask anything about finance &amp; compliance</h2>
            <p className={`mt-3 max-w-xl text-sm leading-7 sm:text-base ${darkMode ? "text-white/78" : "text-fintrix-ink/80"}`}>
              FinTrix can explain regulations, market concepts, banking rules, risk controls, and financial products in a practical way.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              {STARTER_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => handleStarterPrompt(prompt)}
                  className={`rounded-full border px-4 py-3 text-sm font-semibold transition-all duration-200 ${
                    darkMode
                      ? "border-white/12 bg-white/10 text-white/90 hover:bg-white/16"
                      : "border-fintrix-dark/10 bg-fintrix-bg text-fintrix-ink hover:bg-fintrix-accent"
                  }`}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </section>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex w-full ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div className="w-full max-w-full lg:max-w-2xl">
                  <ChatMessage darkMode={darkMode} message={message} apiBase={apiBase} />
                </div>
              </div>
            ))}
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="border-t border-white/10 px-4 py-4 sm:px-5">
        <form
          onSubmit={handleSubmit}
          className={`rounded-3xl border px-4 py-4 shadow-soft backdrop-blur ${
            darkMode
              ? "border-white/12 bg-fintrix-dark/85"
              : "border-fintrix-dark/10 bg-white/90"
          }`}
        >
          <textarea
            ref={textareaRef}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about markets, banking, taxation, compliance, or financial products."
            rows={1}
            className={`w-full resize-none border-0 bg-transparent text-sm leading-6 outline-none sm:text-base ${
              darkMode
                ? "text-white placeholder:text-white/55"
                : "text-fintrix-ink placeholder:text-fintrix-ink/55"
            }`}
          />
          <div className="mt-4 flex items-center justify-between gap-3">
            <div className={`hidden text-xs sm:block ${darkMode ? "text-white/55" : "text-fintrix-ink/55"}`}>
              {question.length} chars · {shortcutLabel} to send
            </div>
            <button
              type="submit"
              disabled={loading || !question.trim()}
              className={`ml-auto inline-flex min-w-[126px] items-center justify-center rounded-2xl px-4 py-3 text-sm font-semibold transition-all duration-200 sm:text-base ${
                loading || !question.trim()
                  ? "cursor-not-allowed bg-fintrix-dark/20 text-fintrix-dark/60"
                  : "bg-fintrix-accent text-fintrix-dark hover:opacity-90"
              }`}
            >
              {loading ? (
                <span className="fintrix-spinner" aria-hidden="true" />
              ) : (
                "Send"
              )}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
