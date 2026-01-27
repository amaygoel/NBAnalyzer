"use client";

import { Recommendation } from "@/lib/api";

interface RecommendationCardProps {
  recommendation: Recommendation;
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const config = {
    high: {
      bg: "bg-emerald-100",
      text: "text-emerald-700",
      border: "border-emerald-200",
      label: "HIGH CONFIDENCE",
    },
    medium: {
      bg: "bg-amber-100",
      text: "text-amber-700",
      border: "border-amber-200",
      label: "MEDIUM CONFIDENCE",
    },
    low: {
      bg: "bg-slate-100",
      text: "text-slate-600",
      border: "border-slate-200",
      label: "LOW CONFIDENCE",
    },
  };

  const c = config[confidence as keyof typeof config] || config.low;

  return (
    <span
      className={`px-3 py-1 text-xs font-semibold rounded-full border ${c.bg} ${c.text} ${c.border}`}
    >
      {c.label}
    </span>
  );
}

export default function RecommendationCard({
  recommendation,
}: RecommendationCardProps) {
  const borderColor =
    recommendation.confidence === "high"
      ? "border-emerald-200"
      : recommendation.confidence === "medium"
      ? "border-amber-200"
      : "border-slate-200";

  const bgColor =
    recommendation.confidence === "high"
      ? "bg-emerald-50/50"
      : recommendation.confidence === "medium"
      ? "bg-amber-50/50"
      : "bg-white";

  return (
    <div className={`p-5 rounded-xl border ${borderColor} ${bgColor}`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg font-bold text-slate-900">
              {recommendation.subject}
            </span>
            <span className="text-xs text-slate-400 uppercase bg-slate-100 px-2 py-0.5 rounded">
              {recommendation.bet_type}
            </span>
          </div>
          <p className="text-slate-600">{recommendation.insight}</p>
        </div>
        <ConfidenceBadge confidence={recommendation.confidence} />
      </div>

      {/* Supporting stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-4 border-t border-slate-200">
        {recommendation.supporting_stats.map((stat, idx) => (
          <div key={idx} className="text-center p-3 bg-white rounded-lg border border-slate-100">
            <div className="text-xs text-slate-400 mb-1">{stat.label}</div>
            <div className="text-sm font-semibold text-slate-900">{stat.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
