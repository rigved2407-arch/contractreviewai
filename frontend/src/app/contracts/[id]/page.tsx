"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Loader2, Sparkles, Download, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import type { Contract as ContractType, AnalysisResult } from "@/types";
import ClauseReview from "@/components/ClauseReview";
import RiskBadge from "@/components/RiskBadge";

export default function ContractDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [contract, setContract] = useState<ContractType | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getContract(id)
      .then(setContract)
      .catch((err) => {
        setError(err.message || "Failed to load contract");
        router.push("/dashboard");
      })
      .finally(() => setLoading(false));
  }, [id, router]);

  const runAnalysis = useCallback(async () => {
    if (analyzing) return;
    setAnalyzing(true);
    setError(null);
    try {
      const result = await api.analyzeContract(id);
      setAnalysis(result);
      setContract((prev) =>
        prev ? { ...prev, status: "analyzed", risk_score: result.risk_score, clauses: result.clauses } : prev
      );
    } catch (err: any) {
      setError(err.message || "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  }, [id, analyzing]);

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  if (!contract) return null;

  if (error && !contract.clauses.length) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle className="w-12 h-12 text-red-500 mb-4" />
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Error</h2>
        <p className="text-sm text-gray-500 mb-4">{error}</p>
        <button onClick={() => router.push("/dashboard")} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm">
          Back to Dashboard
        </button>
      </div>
    );
  }

  const alreadyAnalyzed = contract.status === "analyzed" && contract.clauses.length > 0;

  return (
    <div>
      <button
        onClick={() => router.push("/dashboard")}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 mb-4 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Dashboard
      </button>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="bg-white border rounded-xl p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900 break-all">
              {contract.filename}
            </h1>
            <div className="flex items-center gap-3 mt-2 text-sm text-gray-500">
              <span>{contract.file_type?.toUpperCase()}</span>
              <span>&middot;</span>
              <span>Status: {contract.status}</span>
              {contract.risk_score != null && (
                <>
                  <span>&middot;</span>
                  <span className="font-semibold">
                    Risk Score: {contract.risk_score}%
                  </span>
                  <RiskBadge
                    level={
                      contract.risk_score > 50
                        ? "high"
                        : contract.risk_score > 25
                        ? "medium"
                        : "low"
                    }
                  />
                </>
              )}
            </div>
          </div>
          <div className="flex gap-3">
            {!alreadyAnalyzed && (
              <button
                onClick={runAnalysis}
                disabled={analyzing}
                className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {analyzing ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                {analyzing ? "Analyzing..." : "Run AI Analysis"}
              </button>
            )}
            {(analysis?.redline_url || alreadyAnalyzed) && (
              <a
                href={`/api/contracts/${id}/redline`}
                className="flex items-center gap-2 px-5 py-2.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                <Download className="w-4 h-4" />
                Download Redline
              </a>
            )}
          </div>
        </div>

        {contract.summary && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">
              Summary
            </p>
            <p className="text-sm text-gray-700">{contract.summary}</p>
          </div>
        )}
      </div>

      {alreadyAnalyzed && (
        <div className="bg-white border rounded-xl p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">
            Clause Analysis
          </h2>
          <ClauseReview clauses={contract.clauses} />
        </div>
      )}

      {analyzing && (
        <div className="text-center py-12">
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-3" />
          <p className="text-gray-600">
            Extracting clauses and assessing risk under Indian law...
          </p>
          <p className="text-sm text-gray-400 mt-1">
            This usually takes 30–60 seconds
          </p>
        </div>
      )}
    </div>
  );
}
