import Link from "next/link";

const footerLinks = {
  company: [
    { label: "About", href: "/legal/tos" },
    { label: "Careers", href: "/" },
    { label: "Press", href: "/" }
  ],
  support: [
    { label: "Help center", href: "/" },
    { label: "Cancellation options", href: "/" },
    { label: "Safety", href: "/" }
  ],
  hosting: [
    { label: "Start hosting", href: "/host/new" },
    { label: "Resources", href: "/host" },
    { label: "Community", href: "/" }
  ]
};

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-surface">
      <div className="mx-auto grid max-w-6xl gap-10 px-6 py-12 md:grid-cols-4">
        <div>
          <p className="text-lg font-semibold">HarborHomes</p>
          <p className="mt-3 text-sm text-muted-ink">
            HarborHomes curates welcoming stays with local insight and warm service. Explore responsibly and feel at home.
          </p>
        </div>
        {Object.entries(footerLinks).map(([group, links]) => (
          <div key={group} className="text-sm">
            <p className="font-semibold capitalize text-ink">{group}</p>
            <ul className="mt-3 space-y-2 text-muted-ink">
              {links.map((link) => (
                <li key={link.label}>
                  <Link href={link.href} className="hover:text-ink">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-border bg-white py-4">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 text-sm text-muted-ink md:flex-row md:items-center md:justify-between">
          <p>© {new Date().getFullYear()} HarborHomes. Crafted for demo purposes.</p>
          <div className="flex flex-wrap gap-4">
            <Link href="/legal/privacy">Privacy</Link>
            <Link href="/legal/tos">Terms</Link>
            <Link href="/legal/cookies">Cookies</Link>
            <Link href="/legal/consent">Consent preferences</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
