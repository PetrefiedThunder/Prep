"use client";

import { useState } from "react";
import { messageThreads } from "@/lib/mock-data";
import { formatDistanceToNow } from "date-fns";

export default function InboxPage() {
  const [activeId, setActiveId] = useState(messageThreads[0]?.id);
  const activeThread = messageThreads.find((thread) => thread.id === activeId);

  return (
    <div className="mx-auto flex max-w-6xl gap-6 px-6 py-12">
      <aside className="w-full max-w-sm space-y-4 rounded-3xl border border-border bg-white p-4 shadow-sm">
        <h1 className="text-xl font-semibold">Inbox</h1>
        <ul className="space-y-3">
          {messageThreads.map((thread) => (
            <li key={thread.id}>
              <button
                onClick={() => setActiveId(thread.id)}
                className={`w-full rounded-2xl border px-4 py-3 text-left text-sm transition ${
                  thread.id === activeId ? "border-brand bg-brand/10" : "border-border"
                }`}
              >
                <p className="font-semibold text-ink">{thread.participant.name}</p>
                <p className="text-xs text-muted-ink">{thread.lastMessagePreview}</p>
              </button>
            </li>
          ))}
        </ul>
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
            <form className="mt-4 flex gap-3">
              <input className="flex-1 rounded-2xl border border-border px-4 py-3" placeholder="Write a message" />
              <button className="rounded-2xl bg-brand px-5 py-3 text-sm font-semibold text-brand-contrast">Send</button>
            </form>
          </div>
        ) : (
          <p className="text-muted-ink">Select a conversation.</p>
        )}
      </section>
    </div>
  );
}
