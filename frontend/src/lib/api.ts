import type { Contract, ContractListItem, AnalysisResult, Playbook } from "@/types";

const BASE = "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function fetchJson<T>(url: string, opts?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, { ...opts, signal: AbortSignal.timeout(120000) });
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === "TimeoutError") {
      throw new ApiError(0, "Request timed out. Please try again.");
    }
    throw new ApiError(0, "Network error. Please check your connection.");
  }
  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {
      const text = await res.text().catch(() => "");
      if (text) detail = text;
    }
    throw new ApiError(res.status, detail);
  }
  return res.json();
}

export const api = {
  listContracts(): Promise<ContractListItem[]> {
    return fetchJson(`${BASE}/contracts`);
  },

  getContract(id: string): Promise<Contract> {
    return fetchJson(`${BASE}/contracts/${id}`);
  },

  uploadContract(file: File): Promise<Contract> {
    const form = new FormData();
    form.append("file", file);
    return fetchJson(`${BASE}/contracts/upload`, { method: "POST", body: form });
  },

  deleteContract(id: string): Promise<void> {
    return fetchJson(`${BASE}/contracts/${id}`, { method: "DELETE" });
  },

  analyzeContract(id: string, playbookId?: string): Promise<AnalysisResult> {
    return fetchJson(`${BASE}/analysis/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ playbook_id: playbookId || null }),
    });
  },

  listPlaybooks(): Promise<Playbook[]> {
    return fetchJson(`${BASE}/playbooks`);
  },

  getPlaybook(id: string): Promise<Playbook> {
    return fetchJson(`${BASE}/playbooks/${id}`);
  },

  createPlaybook(data: { name: string; description?: string; rules: any[] }): Promise<Playbook> {
    return fetchJson(`${BASE}/playbooks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  },
};
