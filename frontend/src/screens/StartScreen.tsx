import { useState } from "react";

interface StartScreenProps {
  onStart: (roleTitle: string) => void;
  isLoading: boolean;
  error: string | null;
}

export function StartScreen({ onStart, isLoading, error }: StartScreenProps) {
  const [roleTitle, setRoleTitle] = useState("");

  return (
    <div className="max-w-md mx-auto mt-16 p-6">
      <h1 className="text-2xl font-semibold mb-4">Employee Skill Assessment</h1>
      <label htmlFor="role-title" className="block mb-2 text-sm font-medium">
        What's your current role?
      </label>
      <input
        id="role-title"
        data-testid="role-title-input"
        className="w-full border rounded px-3 py-2 mb-4"
        value={roleTitle}
        onChange={(e) => setRoleTitle(e.target.value)}
        placeholder="e.g. Software Engineer"
      />
      {error && <p className="text-red-600 mb-4">{error}</p>}
      <button
        data-testid="start-button"
        className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        disabled={isLoading || roleTitle.trim().length === 0}
        onClick={() => onStart(roleTitle.trim())}
      >
        {isLoading ? "Starting..." : "Start Assessment"}
      </button>
    </div>
  );
}
