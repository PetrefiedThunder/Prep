"use client";

import { useEffect, useMemo, useState } from "react";
import { formatDistanceToNow } from "date-fns";

import { ActionableErrorFallback, ErrorBoundary } from "@/components/system/error-boundary";
import { MaintenanceBanner } from "@/components/system/maintenance-banner";
import { messageThreads } from "@/lib/mock-data";
import { normalizeError, reportClientError } from "@/lib/telemetry";

type MessageThread = (typeof messageThreads)[number];

type InboxState = {
  threads: MessageThread[];
  activeThreadId: string | null;
};

const initialState: InboxState = {
  threads: [],
  activeThreadId: null
};

export default function InboxPage() {
  const [{ threads, activeThreadId }, setState] = useState<InboxState>(initialState);
  const [guardError, setGuardError] = useState<Error | null>(null);

  useEffect(() => {
    try {
      if (!Array.isArray(messageThreads) || messageThreads.length === 0) {
        throw new Error("Inbox threads are not available yet");
      }

      setState({
        threads: messageThreads,
        activeThreadId: messageThreads[0]?.id ?? null
      });
    } catch (error) {
      const normalized = normalizeError(error, "Failed to initialise inbox threads");
      setGuardError(normalized);
      reportClientError(normalized, "inbox-page:init");
    }
  }, []);

  const activeThread = useMemo(() => {
    if (!activeThreadId) {
      return null;
    }

    return threads.find((thread) => thread.id === activeThreadId) ?? null;
  }, [threads, activeThreadId]);

  return (
    <ErrorBoundary
      context="app/(site)/inbox/page"
      fallback={({ reset }) => (
        <ActionableErrorFallback
          title="We couldn't load your inbox"
          description="Our messaging experience is having trouble. Try again or let us know if the issue keeps happening."
          primaryActionLabel="Try again"
          onPrimaryAction={() => {
            reset();
            if (typeof window !== "undefined") {
              window.location.reload();
            }
          }}
          secondaryActionLabel="Contact support"
          secondaryActionHref="mailto:support@harborhomes.app"
          reset={reset}
          errorDetails={guardError?.message}
        />
      )}
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-12">
        <MaintenanceBanner
          title="Messaging in maintenance"
          description="We're polishing the inbox experience. You can review demo content below, but sending replies is temporarily offline."
          actionLabel="Email support"
          onAction={() => {
            if (typeof window !== "undefined") {
              window.location.href = "mailto:support@harborhomes.app";
            }
          }}
        />
        {guardError ? (
          <div className="flex flex-1 items-center justify-center rounded-3xl border border-dashed border-border bg-white p-12 text-center">
            <p className="max-w-md text-sm text-muted-ink">
              We couldn't fetch your latest conversations. Please reach out to
              <a className="ml-1 font-medium text-ink underline" href="mailto:support@harborhomes.app">
                support@harborhomes.app
              </a>{" "}
              while we finish maintenance.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-6 md:flex-row">
            <aside className="w-full max-w-sm space-y-4 rounded-3xl border border-border bg-white p-4 shadow-sm">
              <h1 className="text-xl font-semibold">Inbox</h1>
              {threads.length === 0 ? (
                <p className="text-sm text-muted-ink">Loading demo conversations…</p>
              ) : (
                <ul className="space-y-3">
                  {threads.map((thread) => (
                    <li key={thread.id}>
                      <button
                        onClick={() => setState((current) => ({ ...current, activeThreadId: thread.id }))}
                        className={`w-full rounded-2xl border px-4 py-3 text-left text-sm transition ${
                          thread.id === activeThreadId ? "border-brand bg-brand/10" : "border-border"
                        }`}
                      >
                        <p className="font-semibold text-ink">{thread.participant.name}</p>
                        <p className="text-xs text-muted-ink">{thread.lastMessagePreview}</p>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </aside>
            <section className="flex-1 rounded-3xl border border-border bg-white p-6 shadow-sm">
              {activeThread ? (
                <div className="flex h-full flex-col">
                  <header className="border-b border-border pb-4">
                    <p className="text-sm font-semibold">Conversation with {activeThread.participant.name}</p>
                    <p className="text-xs text-muted-ink">
                      {formatDistanceToNow(new Date(activeThread.lastMessageAt), { addSuffix: true })}
                    </p>
                  </header>
                  <div className="flex-1 space-y-4 overflow-y-auto py-4">
                    {activeThread.messages.map((message) => (
                      <div
                        key={message.id}
                        className={`max-w-md rounded-2xl px-4 py-3 text-sm ${
                          message.senderId === activeThread.participant.id
                            ? "bg-surface text-ink"
                            : "ml-auto bg-brand text-brand-contrast"
                        }`}
                      >
                        {message.body}
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 flex flex-col gap-3 rounded-2xl border border-dashed border-border p-4 text-sm text-muted-ink">
                    <p>Replying is paused while we stabilise messaging. Please check back soon.</p>
                  </div>
                </div>
              ) : (
                <div className="flex h-full items-center justify-center text-center text-muted-ink">
                  Select a conversation to preview the thread.
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
}
