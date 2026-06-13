"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, FileCheck } from "lucide-react";
import type { Clause } from "@/types";
import RiskBadge from "./RiskBadge";

interface Props {
  clauses: Clause[];
}

export default function ClauseReview({ clauses }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (clauses.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <FileCheck className="w-12 h-12 mx-auto mb-3 opacity-40" />
        <p>No clauses extracted. Run analysis first.</p>
      </div>
    );
  }

  const grouped = clauses.reduce<Record<string, Clause[]>>((acc, c) => {
    const key = c.risk_level ?? "info";
    if (!acc[key]) acc[key] = [];
    acc[key].push(c);
    return acc;
  }, {});

  const order = ["high", "medium", "low", "info"];

  return (
    <div className="space-y-4">
      {order.map((level) => {
        const items = grouped[level];
        if (!items || items.length === 0) return null;
        return (
          <div key={level} className="border rounded-lg overflow-hidden">
            <div className="bg-gray-50 px-4 py-2 border-b flex items-center gap-2">
              <RiskBadge level={level} />
              <span className="text-sm text-gray-600">{items.length} clause(s)</span>
            </div>
            <div className="divide-y">
              {items.map((clause) => (
                <div key={clause.id}>
                  <button
                    onClick={() =>
                      setExpanded(expanded === clause.id ? null : clause.id)
                    }
                    className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition-colors"
                  >
                    <div className="min-w-0 flex-1">
                      <span className="font-medium text-gray-900">
                        {clause.clause_type}
                      </span>
                      {clause.section_header && (
                        <span className="ml-2 text-sm text-gray-500">
                          &mdash; {clause.section_header}
                        </span>
                      )}
                    </div>
                    {expanded === clause.id ? (
                      <ChevronUp className="w-4 h-4 text-gray-400 shrink-0" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
                    )}
                  </button>
                  {expanded === clause.id && (
                    <div className="px-4 pb-4 space-y-3">
                      <div>
                        <p className="text-xs text-gray-500 mb-1 uppercase tracking-wide">
                          Clause Text
                        </p>
                        <p className="text-sm text-gray-700 bg-gray-50 rounded p-3 whitespace-pre-wrap">
                          {clause.clause_text || "—"}
                        </p>
                      </div>
                      {clause.risk_reason && (
                        <div>
                          <p className="text-xs text-gray-500 mb-1 uppercase tracking-wide">
                            Risk Reason
                          </p>
                          <p className="text-sm text-red-700 bg-red-50 rounded p-3">
                            {clause.risk_reason}
                          </p>
                        </div>
                      )}
                      {clause.suggested_redline && (
                        <div>
                          <p className="text-xs text-gray-500 mb-1 uppercase tracking-wide">
                            Suggested Redline
                          </p>
                          <p className="text-sm text-green-700 bg-green-50 rounded p-3 whitespace-pre-wrap">
                            {clause.suggested_redline}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
