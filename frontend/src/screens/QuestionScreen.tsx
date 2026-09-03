import { useState } from "react";

interface QuestionScreenProps {
  question: string;
  onSubmit: (answer: string) => void;
  isLoading: boolean;
  error: string | null;
}

export function QuestionScreen({ question, onSubmit, isLoading, error }: QuestionScreenProps) {
  const [answer, setAnswer] = useState("");

  return (
    <div className="max-w-md mx-auto mt-16 p-6">
      <p data-testid="question-text" className="text-lg font-medium mb-4">
        {question}
      </p>
      <textarea
        data-testid="answer-input"
        className="w-full border rounded px-3 py-2 mb-4"
        rows={4}
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
      />
      {error && <p className="text-red-600 mb-4">{error}</p>}
      <button
        data-testid="submit-answer-button"
        className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        disabled={isLoading || answer.trim().length === 0}
        onClick={() => onSubmit(answer.trim())}
      >
        {isLoading ? "Submitting..." : "Submit Answer"}
      </button>
    </div>
  );
}
