import { useState } from "react";

import { getApiErrorMessage } from "../api/api";
import { analyzeText } from "../api/ai";

const MODES = [
  { value: "summary", label: "Summary", hint: "Concise bullet summary" },
  { value: "action_items", label: "Action items", hint: "Checklist of next steps" },
  { value: "sentiment", label: "Sentiment", hint: "Tone as JSON" },
];

function TextAnalyzePanel() {
  const [text, setText] = useState("");
  const [mode, setMode] = useState("summary");
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) return;

    setLoading(true);
    setError("");
    setResult("");
    try {
      const data = await analyzeText({ text: trimmed, mode });
      setResult(data.result || "");
    } catch (err) {
      setError(getApiErrorMessage(err, "Analysis failed. Check GROQ_API_KEY in backend/.env."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ai-analyze">
      <header className="ai-analyze-header">
        <h2 className="ai-heading">Analyze text</h2>
        <p className="ai-analyze-lead">
          Paste meeting notes, retros, or any text. The LLM returns a summary, action items, or
          sentiment — without project RAG context.
        </p>
      </header>

      <form className="ai-analyze-form" onSubmit={handleSubmit}>
        <label className="ai-analyze-label" htmlFor="analyze-mode">
          Mode
        </label>
        <select
          id="analyze-mode"
          className="ai-select"
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          disabled={loading}
        >
          {MODES.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label} — {m.hint}
            </option>
          ))}
        </select>

        <label className="ai-analyze-label" htmlFor="analyze-text">
          Text
        </label>
        <textarea
          id="analyze-text"
          className="ai-analyze-textarea"
          rows={10}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste notes, retro, email thread, or requirements…"
          disabled={loading}
        />

        <button type="submit" className="ai-btn ai-btn--primary" disabled={loading || !text.trim()}>
          {loading ? "Analyzing…" : "Run analysis"}
        </button>
      </form>

      {error ? (
        <div className="ai-error" role="alert">
          {error}
        </div>
      ) : null}

      {result ? (
        <section className="ai-analyze-result" aria-live="polite">
          <h3 className="ai-analyze-result-title">Result ({mode})</h3>
          <pre className="ai-analyze-result-body">{result}</pre>
        </section>
      ) : null}
    </div>
  );
}

export default TextAnalyzePanel;
