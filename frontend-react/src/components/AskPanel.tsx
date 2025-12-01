import { useState, useRef, useEffect } from 'react';

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

interface ConversationMessage {
  id: string;
  question: string;
  answer: string;
  level: number;
  timestamp: Date;
}

export const AskPanel = () => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const [copySuccess, setCopySuccess] = useState<string | null>(null);
  const questionInputRef = useRef<HTMLTextAreaElement>(null);
  const maxRefinementLevel = 3;

  const toggleListening = () => {
    setIsListening((prev) => !prev);
  };

  const submit = async () => {
    if (!question.trim()) {
      setError('Please enter a question.');
      return;
    }
    
    // Check refinement level
    const currentLevel = conversation.length + 1;
    if (currentLevel > maxRefinementLevel) {
      setError(`Maximum refinement level (${maxRefinementLevel}) reached. Start a new conversation.`);
      return;
    }
    
    setError(null);
    setLoading(true);
    const currentQuestion = question;
    const body = new FormData();
    body.append('query', currentQuestion);
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
      
      // Add to conversation history
      const message: ConversationMessage = {
        id: Date.now().toString(),
        question: currentQuestion,
        answer: data.answer,
        level: currentLevel,
        timestamp: new Date()
      };
      setConversation([...conversation, message]);
      
      // Clear question for next iteration
      setQuestion('');
    } catch (err) {
      const message = (err as Error).message;
      setError(message.includes('fetch') ? 'Network error. Check connection.' : message);
    } finally {
      setLoading(false);
    }
  };

  const handleAskClick = () => {
    questionInputRef.current?.focus();
    submit();
  };

  const handleRefineClick = () => {
    if (result) {
      setQuestion('Can you elaborate on: ');
      questionInputRef.current?.focus();
      questionInputRef.current?.setSelectionRange(questionInputRef.current.value.length, questionInputRef.current.value.length);
    }
  };

  const copyToClipboard = async (text: string, type: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopySuccess(type);
      setTimeout(() => setCopySuccess(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const copyAnswer = () => {
    if (result?.answer) {
      copyToClipboard(result.answer, 'answer');
    }
  };

  const copyChunk = (chunk: Chunk) => {
    const chunkText = `${chunk.content}\n\nSource: ${chunk.citation}`;
    copyToClipboard(chunkText, `chunk-${chunk.index}`);
  };

  const startNewConversation = () => {
    setConversation([]);
    setResult(null);
    setQuestion('');
    questionInputRef.current?.focus();
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
        ref={questionInputRef}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder="Ask your Second Brain anything... (Cmd/Ctrl+Enter to submit)"
        aria-label="Ask a question about your knowledge base"
      />

      <div className="ask-actions">
        <button type="button" onClick={handleAskClick} disabled={loading}>
          {loading ? 'Searching…' : 'Ask'}
        </button>
        {conversation.length > 0 && (
          <button type="button" onClick={startNewConversation} className="button-outline">
            New Conversation
          </button>
        )}
      </div>

      {error && <p className="small error" role="alert">{error}</p>}
      {conversation.length > 0 && (
        <div className="conversation-history">
          <h4>Conversation ({conversation.length}/{maxRefinementLevel})</h4>
          {conversation.map((msg) => (
            <div key={msg.id} className="conversation-item">
              <div className="conversation-question">
                <strong>Q{msg.level}:</strong> {msg.question}
              </div>
              <div className="conversation-answer">
                <strong>A{msg.level}:</strong> {msg.answer.substring(0, 100)}...
              </div>
            </div>
          ))}
        </div>
      )}

      {result && (
        <div className="answer-card">
          <div className="chunk-meta">
            <h3>Answer</h3>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              {confidenceValue !== undefined && (
                <span className="pill-badge">
                  Confidence&nbsp;
                  {formattedConfidence ?? '—'}
                </span>
              )}
              <button
                type="button"
                onClick={copyAnswer}
                className="button-outline small"
                title="Copy answer to clipboard"
              >
                {copySuccess === 'answer' ? '✓ Copied' : 'Copy Answer'}
              </button>
            </div>
          </div>
          <pre>{result.answer}</pre>
          
          {conversation.length < maxRefinementLevel && (
            <div className="refinement-actions">
              <button
                type="button"
                onClick={handleRefineClick}
                className="button-primary"
              >
                Refine This Answer
              </button>
            </div>
          )}
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
                      <button
                        type="button"
                        onClick={() => copyChunk(chunk)}
                        className="button-outline small"
                        title="Copy chunk to clipboard"
                      >
                        {copySuccess === `chunk-${chunk.index}` ? '✓ Copied' : 'Copy'}
                      </button>
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

