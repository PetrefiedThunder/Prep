export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center gap-4 text-center">
      <span className="text-sm font-semibold uppercase tracking-[0.2em] text-brand">404</span>
      <h1 className="text-3xl font-semibold text-ink">This tide has gone out.</h1>
      <p className="text-muted-ink">The HarborHome you are looking for might have sailed away. Try another search.</p>
    </div>
  );
}
