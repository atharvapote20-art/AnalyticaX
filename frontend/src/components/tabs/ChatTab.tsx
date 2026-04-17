import type { FormEvent } from "react";
import type { ChatEntry } from "../../types/app";

type ChatTabProps = {
  chatPrompt: string;
  setChatPrompt: (v: string) => void;
  chatLog: ChatEntry[];
  isBusy: boolean;
  onSubmit: (e: FormEvent) => void;
};

export function ChatTab({ chatPrompt, setChatPrompt, chatLog, isBusy, onSubmit }: ChatTabProps) {
  return (
    <div className="chat-layout">
      <form onSubmit={onSubmit} className="chat-form">
        <input
          value={chatPrompt}
          onChange={(e) => setChatPrompt(e.target.value)}
          placeholder="Ask: What is the average of sales?"
        />
        <button className="primary-btn" type="submit" disabled={isBusy}>
          Ask
        </button>
      </form>
      <div className="chat-log">
        {chatLog.length === 0 ? (
          <p>No chat yet. Ask your first question.</p>
        ) : (
          chatLog.map((entry, idx) => (
            <div className="chat-item" key={`${idx}-${entry.question}`}>
              <p className="q">Q: {entry.question}</p>
              <p className="a">A: {entry.answer.reply}</p>
              <details className="ai-details">
                <summary>Answer summary</summary>
                <p className="insight-meta">
                  <strong>Mode:</strong> {entry.answer.mode ?? "unknown"}
                </p>
                <p className="insight-meta">
                  <strong>Confidence:</strong> {Math.max(0, Math.min(100, entry.answer.confidence ?? 0))}%
                </p>
                <p className="insight-meta">
                  <strong>English summary:</strong> {entry.answer.explanation ?? "Summary unavailable."}
                </p>
              </details>
              {entry.answer.result ? <ResultTable entry={entry} /> : null}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function ResultTable({ entry }: { entry: ChatEntry }) {
  const result = entry.answer.result;
  if (!result) return null;
  const columns = result.columns ?? [];
  const rows = result.rows ?? [];

  return (
    <div className="table-wrap">
      <table className="profile-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={`${idx}-${entry.question}`}>
              {row.map((cell, cellIdx) => (
                <td key={`${idx}-${cellIdx}`}>{formatCell(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {result.truncated ? <p className="insight-meta">Showing a preview. Result rows were truncated for speed.</p> : null}
    </div>
  );
}

function formatCell(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return Number.isFinite(value) ? value.toLocaleString() : "-";
  return String(value);
}
