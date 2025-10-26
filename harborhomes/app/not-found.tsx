import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="flex min-h-[70vh] flex-col items-center justify-center gap-6 px-6 text-center">
      <h1 className="text-4xl font-semibold">We can't find that HarborHome</h1>
      <p className="max-w-xl text-lg text-muted-ink">
        The page you're looking for may have sailed off. Explore curated stays and host tools from our home page.
      </p>
      <Button asChild>
        <Link href="/">Back to safety</Link>
      </Button>
    </main>
  );
}
