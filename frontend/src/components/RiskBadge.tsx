const colors: Record<string, string> = {
  high: "bg-red-100 text-red-800 border-red-300",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-300",
  low: "bg-green-100 text-green-800 border-green-300",
  info: "bg-blue-100 text-blue-800 border-blue-300",
};

export default function RiskBadge({ level }: { level: string | null }) {
  const key = level?.toLowerCase() ?? "info";
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
        colors[key] || colors.info
      }`}
    >
      {level ?? "INFO"}
    </span>
  );
}
