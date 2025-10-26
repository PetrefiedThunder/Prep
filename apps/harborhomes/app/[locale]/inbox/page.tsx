import { threads } from '@/lib/mock-data';

export default function InboxPage() {
  const active = threads[0];
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
      <aside className="space-y-3 rounded-3xl border border-border p-4">
        {threads.map((thread) => (
          <button
            key={thread.id}
            className={`w-full rounded-2xl px-4 py-3 text-left text-sm ${thread.id === active.id ? 'bg-surface text-ink' : 'text-muted-ink'}`}
          >
            <span className="font-semibold text-ink">{thread.participants[1]}</span>
            <p className="truncate text-xs">{thread.messages.at(-1)?.body}</p>
          </button>
        ))}
      </aside>
      <section className="flex flex-col gap-4 rounded-3xl border border-border p-6">
        <header>
          <h1 className="text-lg font-semibold text-ink">Conversation with {active.participants[1]}</h1>
          <p className="text-xs text-muted-ink">{active.messages.length} messages</p>
        </header>
        <div className="flex flex-1 flex-col gap-3 overflow-y-auto">
          {active.messages.map((message) => (
            <div key={message.id} className="rounded-3xl bg-surface px-4 py-3 text-sm text-ink">
              <p className="text-xs text-muted-ink">{message.author}</p>
              <p>{message.body}</p>
            </div>
          ))}
        </div>
        <form className="flex gap-2">
          <input
            className="focus-ring flex-1 rounded-full border border-border px-4 py-3 text-sm"
            placeholder="Send a message"
            aria-label="Message input"
          />
          <button className="rounded-full bg-brand px-6 py-3 text-sm font-semibold text-brand-contrast">Send</button>
        </form>
      </section>
    </div>
  );
}
