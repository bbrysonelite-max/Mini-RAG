import { useState, useRef, useEffect } from 'react';
import { LoadingSpinner } from './LoadingSpinner';
import { ErrorMessage } from './ErrorMessage';

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

interface AskPanelProps {
  workspaceId?: string;
}

const COMMANDS = [
  { value: 'ask', label: 'Ask', tooltip: 'Ask your Second Brain anything about this workspace.', placeholder: 'Ask your Second Brain anything about this workspace…' },
  { value: 'success_coach', label: 'Success Coach', tooltip: 'Get a simple, realistic plan and today\'s top 3 actions.', placeholder: 'Tell me what you\'re stuck on or what you want to make progress on…' },
  { value: 'workflow_agent', label: 'Workflow Agent', tooltip: 'Turn a messy process into a clear workflow with steps.', placeholder: 'Describe the process you want to turn into a clear workflow…' },
  { value: 'lead_social_agent', label: 'Lead & Social Agent', tooltip: 'Plan how to find leads and create social content for them.', placeholder: 'Describe your offer and who you want to reach for leads and social…' },
  { value: 'build_prompt', label: 'Build Prompt', tooltip: 'Design a reusable prompt you can save and use again.', placeholder: 'Describe what you want this reusable prompt to do and for which tool…' },
  { value: 'build_workflow', label: 'Build Workflow', tooltip: 'Create a workflow with GOAL, TRIGGER, and step-by-step actions.', placeholder: 'Describe the outcome and the rough steps you want in your workflow…' },
  { value: 'landing_page', label: 'Landing Page', tooltip: 'Draft a landing page with hero, problem, solution, and CTA.', placeholder: 'Describe the offer, audience, and style for this landing page…' },
  { value: 'email_sequence', label: 'Email Sequence', tooltip: 'Generate a multi-email sequence for this offer or lead magnet.', placeholder: 'Describe your offer and what this email sequence should accomplish…' },
  { value: 'content_batch', label: 'Content Batch (Social Posts)', tooltip: 'Create a batch of social posts (e.g., 10 LinkedIn or Instagram posts).', placeholder: 'Describe your topic, platform, and how many posts you want…' },
  { value: 'decision_record', label: 'Decision Record', tooltip: 'Log an important business decision with options and rationale.', placeholder: 'Describe the decision, your options, and any constraints…' },
  { value: 'build_expert_instructions', label: 'Build Expert Instructions', tooltip: 'Research top experts and synthesize a formula or checklist to follow.', placeholder: 'Name the topic you want expert-level instructions for (e.g. "sales pages")…' },
  { value: 'build_customer_avatar', label: 'Build Customer Avatar', tooltip: 'Create an Ideal Customer Avatar for this workspace.', placeholder: 'Describe the product/service and who you think it\'s for…' },
  { value: 'pack_for_gumroad', label: 'Pack for Gumroad', tooltip: 'Bundle existing assets into a product structure and product page copy.', placeholder: 'Tell me which assets and what kind of product bundle you want to create…' },
];

export const AskPanel = ({ workspaceId }: AskPanelProps) => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const [copySuccess, setCopySuccess] = useState<string | null>(null);
  const [selectedCommand, setSelectedCommand] = useState<string>('ask');
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [saveTitle, setSaveTitle] = useState('');
  const questionInputRef = useRef<HTMLTextAreaElement>(null);
  const maxRefinementLevel = 3;

  const currentCommand = COMMANDS.find(c => c.value === selectedCommand) || COMMANDS[0];

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
    if (selectedCommand && selectedCommand !== 'ask') {
      body.append('command', selectedCommand);
    }

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

  const handleSaveAsset = async () => {
    if (!result?.answer || !workspaceId || !saveTitle.trim()) return;
    
    // Determine asset type from command
    const commandToType: Record<string, string> = {
      'build_prompt': 'prompt',
      'build_workflow': 'workflow',
      'landing_page': 'page',
      'email_sequence': 'sequence',
      'content_batch': 'document',
      'decision_record': 'decision',
      'build_expert_instructions': 'expert_instructions',
      'build_customer_avatar': 'customer_avatar',
    };
    const assetType = commandToType[selectedCommand] || 'document';
    
    try {
      const res = await fetch(`/api/v1/workspaces/${workspaceId}/assets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: assetType,
          title: saveTitle.trim(),
          content: result.answer,
          tags: [selectedCommand, 'from_ask']
        })
      });
      
      if (res.ok) {
        setShowSaveModal(false);
        setSaveTitle('');
        alert('Asset saved successfully!');
      } else {
        const error = await res.json().catch(() => ({ detail: 'Failed to save asset' }));
        alert(error.detail || 'Failed to save asset');
      }
    } catch (err) {
      console.error('Failed to save asset:', err);
      alert('Failed to save asset');
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
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div>
            <label htmlFor="command-select" className="small" style={{ display: 'block', marginBottom: '0.25rem' }}>
              Command
            </label>
            <select
              id="command-select"
              value={selectedCommand}
              onChange={(e) => setSelectedCommand(e.target.value)}
              title={currentCommand.tooltip}
              style={{ padding: '0.5rem' }}
            >
              {COMMANDS.map(cmd => (
                <option key={cmd.value} value={cmd.value} title={cmd.tooltip}>
                  {cmd.label}
                </option>
              ))}
            </select>
            <span className="small" style={{ display: 'block', marginTop: '0.25rem', color: '#666' }}>
              {currentCommand.tooltip}
            </span>
          </div>
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
        placeholder={currentCommand.placeholder}
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

      {loading && (
        <LoadingSpinner 
          size="medium" 
          message="Searching your knowledge base..." 
        />
      )}

      {error && (
        <ErrorMessage
          title="Query Error"
          message={error}
          onRetry={() => {
            setError(null);
            submit();
          }}
          type="error"
        />
      )}
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
              {workspaceId && selectedCommand !== 'ask' && (
                <button
                  type="button"
                  onClick={() => {
                    setSaveTitle(`${currentCommand.label} - ${new Date().toLocaleDateString()}`);
                    setShowSaveModal(true);
                  }}
                  className="button-primary small"
                  title="Save as asset"
                >
                  Save
                </button>
              )}
            </div>
          </div>
          <pre>{result.answer}</pre>
          
          {showSaveModal && (
            <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
              <div style={{ background: 'white', padding: '2rem', borderRadius: '8px', maxWidth: '500px', width: '90%' }}>
                <h3>Save as Asset</h3>
                <label style={{ display: 'block', marginTop: '1rem' }}>
                  Title:
                  <input
                    type="text"
                    value={saveTitle}
                    onChange={(e) => setSaveTitle(e.target.value)}
                    style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem' }}
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveAsset();
                      if (e.key === 'Escape') setShowSaveModal(false);
                    }}
                  />
                </label>
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                  <button type="button" onClick={handleSaveAsset} className="button-primary">Save</button>
                  <button type="button" onClick={() => setShowSaveModal(false)} className="button-outline">Cancel</button>
                </div>
              </div>
            </div>
          )}
          
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

