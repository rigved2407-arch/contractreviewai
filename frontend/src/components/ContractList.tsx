"use client";

import Link from "next/link";
import { FileText, Trash2, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import type { ContractListItem } from "@/types";
import RiskBadge from "./RiskBadge";

interface Props {
  contracts: ContractListItem[];
  loading: boolean;
  onDeleted: (id: string) => void;
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function ContractList({ contracts, loading, onDeleted }: Props) {
  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  if (contracts.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <FileText className="w-12 h-12 mx-auto mb-3 opacity-40" />
        <p>No contracts yet. Upload one to get started.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {contracts.map((c) => (
        <div
          key={c.id}
          className="flex items-center justify-between bg-white border rounded-lg px-5 py-4 hover:shadow-sm transition-shadow"
        >
          <Link href={`/contracts/${c.id}`} className="flex items-center gap-4 flex-1 min-w-0">
            <div className="p-2 bg-indigo-50 rounded-lg">
              <FileText className="w-5 h-5 text-indigo-600" />
            </div>
            <div className="min-w-0">
              <p className="font-medium text-gray-900 truncate">{c.filename}</p>
              <p className="text-sm text-gray-500">
                {formatDate(c.created_at)} &middot; {c.status}
              </p>
            </div>
            <div className="ml-auto flex items-center gap-3">
              {c.risk_score != null && (
                <span className="text-sm font-semibold text-gray-700">
                  Risk: {c.risk_score}%
                </span>
              )}
              <RiskBadge level={c.risk_score != null ? (c.risk_score > 50 ? "high" : c.risk_score > 25 ? "medium" : "low") : null} />
            </div>
          </Link>
          <button
            onClick={async (e) => {
              e.preventDefault();
              if (confirm("Delete this contract?")) {
                await api.deleteContract(c.id);
                onDeleted(c.id);
              }
            }}
            className="ml-4 p-2 text-gray-400 hover:text-red-600 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
