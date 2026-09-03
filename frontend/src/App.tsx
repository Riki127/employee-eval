import { useState } from "react";

import { startSession, submitAnswer } from "./api";
import { QuestionScreen } from "./screens/QuestionScreen";
import { ResultsScreen } from "./screens/ResultsScreen";
import { StartScreen } from "./screens/StartScreen";
import type { Verdict } from "./types";

type Screen =
  | { kind: "start" }
  | { kind: "question"; sessionId: number; question: string }
  | { kind: "results"; verdict: Verdict; rationale: string; recommendation: string };

export default function App() {
  const [screen, setScreen] = useState<Screen>({ kind: "start" });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleStart(roleTitle: string) {
    setIsLoading(true);
    setError(null);
    try {
      const res = await startSession(roleTitle);
      setScreen({ kind: "question", sessionId: res.session_id, question: res.question });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleAnswer(answer: string) {
    if (screen.kind !== "question") return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await submitAnswer(screen.sessionId, answer);
      if (res.status === "completed" && res.verdict && res.rationale && res.recommendation) {
        setScreen({ kind: "results", verdict: res.verdict, rationale: res.rationale, recommendation: res.recommendation });
      } else if (res.question) {
        setScreen({ kind: "question", sessionId: screen.sessionId, question: res.question });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  }

  if (screen.kind === "start") {
    return <StartScreen onStart={handleStart} isLoading={isLoading} error={error} />;
  }
  if (screen.kind === "question") {
    return <QuestionScreen question={screen.question} onSubmit={handleAnswer} isLoading={isLoading} error={error} />;
  }
  return <ResultsScreen verdict={screen.verdict} rationale={screen.rationale} recommendation={screen.recommendation} />;
}
