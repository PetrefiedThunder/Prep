import type { Metadata } from "next";
import Header from "@/components/Header";
import "./globals.css";

export const metadata: Metadata = {
  title: "PrepChef - Commercial Kitchen Rentals",
  description: "Find and book commercial kitchen space for your culinary business",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen flex flex-col">
          <Header />

          <main className="flex-grow container mx-auto px-4 py-8">
            {children}
          </main>

          <footer className="bg-gray-100 border-t mt-8">
            <div className="container mx-auto px-4 py-6 text-center text-sm text-gray-600">
              <p>&copy; {new Date().getFullYear()} PrepChef. All rights reserved.</p>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
