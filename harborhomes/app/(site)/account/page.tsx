import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function AccountPage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-3xl font-semibold">Account</h1>
      <p className="text-muted-ink">Manage your profile, preferences, and privacy settings.</p>
      <section className="mt-8 space-y-6 rounded-3xl border border-border bg-white p-6 shadow-sm">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="text-sm font-semibold text-muted-ink">
            Full name
            <Input className="mt-2" defaultValue="Jordan Rivers" />
          </label>
          <label className="text-sm font-semibold text-muted-ink">
            Email
            <Input type="email" className="mt-2" defaultValue="jordan@example.com" />
          </label>
        </div>
        <Button className="rounded-full">Save profile</Button>
      </section>
      <section className="mt-8 grid gap-6 md:grid-cols-2">
        <div className="space-y-3 rounded-3xl border border-border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Notifications</h2>
          <p className="text-sm text-muted-ink">Choose how HarborHomes keeps you in the loop.</p>
          <Button variant="ghost" size="sm">
            Manage alerts
          </Button>
        </div>
        <div className="space-y-3 rounded-3xl border border-border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Privacy</h2>
          <p className="text-sm text-muted-ink">Download data, manage consent, and deactivate.</p>
          <Button variant="ghost" size="sm">
            Privacy controls
          </Button>
        </div>
      </section>
    </div>
  );
}
