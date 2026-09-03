import type { Verdict } from "../types";

interface ResultsScreenProps {
  verdict: Verdict;
  rationale: string;
  recommendation: string;
}

const VERDICT_LABEL: Record<Verdict, string> = {
  below: "Below Expectations",
  meeting: "Meeting Expectations",
  exceeding: "Exceeding Expectations",
};

export function ResultsScreen({ verdict, rationale, recommendation }: ResultsScreenProps) {
  return (
    <div className="max-w-md mx-auto mt-16 p-6">
      <h1 data-testid="verdict" className="text-2xl font-semibold mb-4">
        {VERDICT_LABEL[verdict]}
      </h1>
      <p className="text-sm text-gray-600 mb-1 font-medium">Rationale</p>
      <p data-testid="rationale" className="mb-4">
        {rationale}
      </p>
      <p className="text-sm text-gray-600 mb-1 font-medium">Recommended next step</p>
      <p data-testid="recommendation">{recommendation}</p>
    </div>
  );
}
