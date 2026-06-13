"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus } from "lucide-react";
import { api } from "@/lib/api";
import type { ContractListItem } from "@/types";
import ContractList from "@/components/ContractList";

export default function Dashboard() {
  const [contracts, setContracts] = useState<ContractListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.listContracts();
      setContracts(data);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Contracts</h1>
        <Link
          href="/contracts/new"
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Upload Contract
        </Link>
      </div>
      <ContractList
        contracts={contracts}
        loading={loading}
        onDeleted={(id) => setContracts((prev) => prev.filter((c) => c.id !== id))}
      />
    </div>
  );
}
