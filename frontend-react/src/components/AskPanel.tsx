import { useState } from 'react';

interface Chunk {
  index: number;
  content: string;
  score: number;
  citation: string;
}

interface AskResponse {
  answer: string;
  chunks: Chunk[];
  score?: Record<string, number>;
}

export const AskPanel = () => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);

  const toggleListening = () => {
    setIsListening((prev) => !prev);
  };

  const submit = async () => {
    if (!question.trim()) {
      setError('Please enter a question.');
      return;
    }
    setError(null);
    setLoading(true);
    const body = new FormData();
    body.append('query', question);
    body.append('k', '8');

    try {
      const resp = await fetch('/api/v1/ask', {
        method: 'POST',
        body
      });
      
      if (resp.status === 401) {
        setError('Authentication required. Please sign in.');
        return;
      }
      if (resp.status === 429) {
        setError('Rate limit exceeded. Please wait and try again.');
        return;
      }
      if (resp.status === 402) {
        setError('Billing issue. Please update your subscription.');
        return;
      }
      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({}));
        throw new Error(errorData.detail || `Request failed (${resp.status})`);
      }
      
      const data = (await resp.json()) as AskResponse;
      setResult(data);
    } catch (err) {
      const message = (err as Error).message;
      setError(message.includes('fetch') ? 'Network error. Check connection.' : message);
    } finally {
      setLoading(false);
    }
  };

  const chunkCount = result?.chunks?.length ?? 0;
  const confidenceValue = result?.score ? Object.values(result.score)[0] : undefined;
  const formattedConfidence =
    typeof confidenceValue === 'number' ? confidenceValue.toFixed(2) : confidenceValue;

  return (
    <section>
      <h2>Ask</h2>
      <div className="ask-toolbar">
        <button
          type="button"
          className={`mic-button ${isListening ? 'active' : 'button-outline'}`}
          onClick={toggleListening}
          aria-pressed={isListening}
        >
          {isListening ? 'Stop Listening' : 'Start Listening'}
        </button>
        <span className="pill-badge">
          {chunkCount.toString().padStart(2, '0')} Chunks
        </span>
      </div>

      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask your Second Brain anything..."
        aria-label="Ask a question about your knowledge base"
      />

      <div className="ask-actions">
        <button type="button" onClick={submit} disabled={loading}>
          {loading ? 'Searching…' : 'Ask'}
        </button>
      </div>

      {error && <p className="small error" role="alert">{error}</p>}
      {result && (
        <div className="answer-card">
          <div className="chunk-meta">
            <h3>Answer</h3>
            {confidenceValue !== undefined && (
              <span className="pill-badge">
                Confidence&nbsp;
                {formattedConfidence ?? '—'}
              </span>
            )}
          </div>
          <pre>{result.answer}</pre>
          {result.chunks?.length ? (
            <>
              <h4>Retrieved Chunks</h4>
              <div className="chunk-grid">
                {result.chunks.map((chunk) => (
                  <div key={chunk.index} className="chunk-card">
                    <div className="chunk-meta">
                      <strong>Chunk {chunk.index}</strong>
                      <span className="pill-badge">
                        Score:{' '}
                        {typeof chunk.score === 'number'
                          ? chunk.score.toFixed(2)
                          : chunk.score}
                      </span>
                    </div>
                    <p className="chunk-content">{chunk.content}</p>
                    <div className="chunk-footer">
                      <span className="small">Source</span>
                      <a href={chunk.citation} target="_blank" rel="noreferrer">
                        View chunk
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="empty-state">No context chunks returned.</div>
          )}
        </div>
      )}
    </section>
  );
};

