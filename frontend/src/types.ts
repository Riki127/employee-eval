export type Verdict = "below" | "meeting" | "exceeding";

export interface SessionStartResponse {
  session_id: number;
  role_id: number;
  question: string;
}

export interface AnswerResponse {
  status: "in_progress" | "completed";
  question?: string | null;
  verdict?: Verdict | null;
  rationale?: string | null;
  recommendation?: string | null;
}

export interface QAPairRead {
  order: number;
  question: string;
  answer: string | null;
}

export interface SessionRead {
  id: number;
  status: "in_progress" | "completed";
  role_title: string;
  qa_pairs: QAPairRead[];
  verdict?: Verdict | null;
  rationale?: string | null;
  recommendation?: string | null;
}
