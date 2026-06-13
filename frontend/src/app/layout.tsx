import type { Metadata } from "next";
import "./globals.css";
import ErrorBoundary from "@/components/ErrorBoundary";

export const metadata: Metadata = {
  title: "Contract Review AI",
  description: "AI-powered contract analysis and redlining for Indian law firms",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <nav className="bg-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
            <a href="/" className="text-lg font-bold text-indigo-700 tracking-tight">
              Contract Review AI
            </a>
            <div className="flex items-center gap-4 text-sm">
              <a href="/dashboard" className="text-gray-600 hover:text-gray-900 transition-colors">
                Dashboard
              </a>
              <a href="/contracts/new" className="text-gray-600 hover:text-gray-900 transition-colors">
                Upload
              </a>
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
      </body>
    </html>
  );
}
