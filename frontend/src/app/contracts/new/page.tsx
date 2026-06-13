"use client";

import { useRouter } from "next/navigation";
import UploadZone from "@/components/UploadZone";
import type { Contract } from "@/types";

export default function NewContract() {
  const router = useRouter();

  const handleUploaded = (contract: Contract) => {
    router.push(`/contracts/${contract.id}`);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        Upload Contract
      </h1>
      <UploadZone onUploaded={handleUploaded} />
    </div>
  );
}
