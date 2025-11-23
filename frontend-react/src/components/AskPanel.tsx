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

  return (
    <section>
      <h2>Ask</h2>
      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask about your videos and guides..."
      />
      <button onClick={submit} disabled={loading}>
        {loading ? 'Searching…' : 'Ask'}
      </button>
      {error && <p className="small error">{error}</p>}
      {result && (
        <div className="answer-card">
          <h3>Answer</h3>
          <pre>{result.answer}</pre>
          {result.chunks?.length ? (
            <div>
              <h4>Top Chunks</h4>
              {result.chunks.map((chunk) => (
                <div key={chunk.index} className="chunk-card">
                  <div>
                    <strong>Chunk {chunk.index}</strong>
                    <span className="badge">Score: {chunk.score?.toFixed(2)}</span>
                  </div>
                  <p>{chunk.content}</p>
                  <div className="small">
                    <a href={chunk.citation} target="_blank" rel="noreferrer">
                      View Source
                    </a>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div class purple empty-state>No chunks returned.</div>
          )}
        </div>
      )}
    </section>
  );
};

