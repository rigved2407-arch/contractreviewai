import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">
        AI-Powered Contract Review
      </h1>
      <p className="text-lg text-gray-600 max-w-xl mb-8">
        Upload contracts, extract clauses, assess risk, and generate redlined
        documents — all powered by AI.
      </p>
      <div className="flex gap-4">
        <Link
          href="/contracts/new"
          className="px-6 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors"
        >
          Upload a Contract
        </Link>
        <Link
          href="/dashboard"
          className="px-6 py-3 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          View Dashboard
        </Link>
      </div>
      <div className="grid grid-cols-3 gap-8 mt-20 max-w-2xl">
        <div>
          <div className="text-3xl font-bold text-indigo-600">1.</div>
          <p className="text-sm text-gray-600 mt-1">Upload contract (PDF/DOCX)</p>
        </div>
        <div>
          <div className="text-3xl font-bold text-indigo-600">2.</div>
          <p className="text-sm text-gray-600 mt-1">AI extracts &amp; analyzes clauses</p>
        </div>
        <div>
          <div className="text-3xl font-bold text-indigo-600">3.</div>
          <p className="text-sm text-gray-600 mt-1">Review risks &amp; download redline</p>
        </div>
      </div>
    </div>
  );
}
