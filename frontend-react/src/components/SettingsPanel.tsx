import { useState, useEffect } from 'react';

interface LLMProvider {
  id: string;
  name: string;
  apiKeyEnvVar: string;
  apiKey: string;
  isConfigured: boolean;
  models: string[];
  defaultModel: string;
}

const DEFAULT_PROVIDERS: Omit<LLMProvider, 'apiKey' | 'isConfigured'>[] = [
  {
    id: 'openai',
    name: 'OpenAI',
    apiKeyEnvVar: 'OPENAI_API_KEY',
    models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
    defaultModel: 'gpt-4o',
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    apiKeyEnvVar: 'ANTHROPIC_API_KEY',
    models: ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229', 'claude-3-haiku-20240307'],
    defaultModel: 'claude-3-5-sonnet-20241022',
  },
  {
    id: 'cohere',
    name: 'Cohere (Reranking)',
    apiKeyEnvVar: 'COHERE_API_KEY',
    models: ['rerank-v3.5'],
    defaultModel: 'rerank-v3.5',
  },
];

const STORAGE_KEY = 'secondbrain_llm_settings';

interface StoredSettings {
  providers: Record<string, { apiKey: string; selectedModel: string }>;
  preferredProvider: string;
}

export const SettingsPanel = () => {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [preferredProvider, setPreferredProvider] = useState<string>('openai');
  const [showApiKey, setShowApiKey] = useState<Record<string, boolean>>({});
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [serverStatus, setServerStatus] = useState<Record<string, boolean>>({});

  // Load settings from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    let storedSettings: StoredSettings | null = null;
    
    if (stored) {
      try {
        storedSettings = JSON.parse(stored);
      } catch (e) {
        console.error('Failed to parse stored settings:', e);
      }
    }

    // Initialize providers with stored values
    const initializedProviders = DEFAULT_PROVIDERS.map(p => ({
      ...p,
      apiKey: storedSettings?.providers?.[p.id]?.apiKey || '',
      isConfigured: !!storedSettings?.providers?.[p.id]?.apiKey,
    }));

    setProviders(initializedProviders);
    setPreferredProvider(storedSettings?.preferredProvider || 'openai');
    
    // Check server status
    checkServerStatus();
  }, []);

  const checkServerStatus = async () => {
    try {
      const res = await fetch('/health');
      if (res.ok) {
        const data = await res.json();
        // The server can tell us which providers are configured via env vars
        setServerStatus({
          openai: data.openai_configured || false,
          anthropic: data.anthropic_configured || false,
          cohere: data.cohere_configured || false,
        });
      }
    } catch (e) {
      console.error('Failed to check server status:', e);
    }
  };

  const handleApiKeyChange = (providerId: string, apiKey: string) => {
    setProviders(prev => prev.map(p => 
      p.id === providerId 
        ? { ...p, apiKey, isConfigured: !!apiKey }
        : p
    ));
  };

  const saveSettings = () => {
    const settings: StoredSettings = {
      providers: {},
      preferredProvider,
    };

    providers.forEach(p => {
      if (p.apiKey) {
        settings.providers[p.id] = {
          apiKey: p.apiKey,
          selectedModel: p.defaultModel,
        };
      }
    });

    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    setSaveStatus('Settings saved! API keys are stored locally in your browser.');
    setTimeout(() => setSaveStatus(null), 3000);
  };

  const clearSettings = () => {
    if (confirm('Clear all stored API keys? This cannot be undone.')) {
      localStorage.removeItem(STORAGE_KEY);
      setProviders(DEFAULT_PROVIDERS.map(p => ({
        ...p,
        apiKey: '',
        isConfigured: false,
      })));
      setSaveStatus('Settings cleared.');
      setTimeout(() => setSaveStatus(null), 3000);
    }
  };

  const toggleShowApiKey = (providerId: string) => {
    setShowApiKey(prev => ({ ...prev, [providerId]: !prev[providerId] }));
  };

  const configuredCount = providers.filter(p => p.isConfigured || serverStatus[p.id]).length;

  return (
    <section className="settings-panel">
      <h2>Settings</h2>
      
      <div style={{ marginBottom: '2rem' }}>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
          Configure your LLM providers to enable AI-powered answers. 
          API keys are stored locally in your browser and never sent to our servers.
        </p>
        
        {/* Status Summary */}
        <div 
          style={{
            padding: '1rem',
            borderRadius: '8px',
            background: configuredCount > 0 ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            border: `1px solid ${configuredCount > 0 ? '#10b981' : '#ef4444'}`,
            marginBottom: '1.5rem'
          }}
        >
          <strong style={{ color: configuredCount > 0 ? '#10b981' : '#ef4444' }}>
            {configuredCount > 0 
              ? `${configuredCount} provider${configuredCount > 1 ? 's' : ''} configured`
              : 'No LLM providers configured'}
          </strong>
          <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            {configuredCount > 0 
              ? 'Your Second Brain is ready to generate AI-powered answers.'
              : 'Add at least one API key below to enable AI answers.'}
          </p>
        </div>
      </div>

      {/* Provider Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {providers.map(provider => (
          <div 
            key={provider.id}
            style={{
              padding: '1.5rem',
              borderRadius: '8px',
              background: 'var(--bg-panel-solid)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ margin: 0 }}>{provider.name}</h3>
                <span 
                  style={{ 
                    fontSize: '0.75rem',
                    padding: '0.25rem 0.5rem',
                    borderRadius: '4px',
                    background: (provider.isConfigured || serverStatus[provider.id]) ? '#10b981' : '#6b7280',
                    color: 'white',
                    marginTop: '0.5rem',
                    display: 'inline-block'
                  }}
                >
                  {serverStatus[provider.id] 
                    ? 'Server configured' 
                    : provider.isConfigured 
                      ? 'Local key set' 
                      : 'Not configured'}
                </span>
              </div>
              
              {provider.id === preferredProvider && (
                <span style={{ 
                  padding: '0.25rem 0.75rem', 
                  background: 'var(--accent)', 
                  color: 'white',
                  borderRadius: '9999px',
                  fontSize: '0.75rem'
                }}>
                  Preferred
                </span>
              )}
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
                API Key
              </label>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input
                  type={showApiKey[provider.id] ? 'text' : 'password'}
                  value={provider.apiKey}
                  onChange={(e) => handleApiKeyChange(provider.id, e.target.value)}
                  placeholder={`Enter your ${provider.name} API key...`}
                  style={{ 
                    flex: 1, 
                    padding: '0.75rem',
                    fontFamily: 'monospace',
                    fontSize: '0.875rem'
                  }}
                />
                <button
                  type="button"
                  onClick={() => toggleShowApiKey(provider.id)}
                  className="button-outline"
                  style={{ padding: '0.75rem' }}
                >
                  {showApiKey[provider.id] ? 'Hide' : 'Show'}
                </button>
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginTop: '0.25rem' }}>
                Env var: <code>{provider.apiKeyEnvVar}</code>
              </p>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                type="button"
                onClick={() => setPreferredProvider(provider.id)}
                className={provider.id === preferredProvider ? 'button-primary' : 'button-outline'}
                disabled={!provider.isConfigured && !serverStatus[provider.id]}
              >
                {provider.id === preferredProvider ? 'Preferred' : 'Set as Preferred'}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <button type="button" onClick={saveSettings} className="button-primary">
          Save Settings
        </button>
        <button type="button" onClick={clearSettings} className="button-outline">
          Clear All Keys
        </button>
      </div>

      {saveStatus && (
        <div style={{ 
          marginTop: '1rem', 
          padding: '1rem', 
          borderRadius: '8px',
          background: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid #10b981',
          color: '#10b981'
        }}>
          {saveStatus}
        </div>
      )}

      {/* Help Section */}
      <div style={{ marginTop: '3rem', padding: '1.5rem', background: 'var(--bg-subtle)', borderRadius: '8px' }}>
        <h3 style={{ marginTop: 0 }}>How to get API keys</h3>
        <ul style={{ paddingLeft: '1.25rem', lineHeight: 1.8 }}>
          <li>
            <strong>OpenAI:</strong> Visit{' '}
            <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer">
              platform.openai.com/api-keys
            </a>
          </li>
          <li>
            <strong>Anthropic:</strong> Visit{' '}
            <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer">
              console.anthropic.com/settings/keys
            </a>
          </li>
          <li>
            <strong>Cohere:</strong> Visit{' '}
            <a href="https://dashboard.cohere.com/api-keys" target="_blank" rel="noopener noreferrer">
              dashboard.cohere.com/api-keys
            </a>
            {' '}(optional, for better search ranking)
          </li>
        </ul>
        
        <h4>Security Note</h4>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          API keys entered here are stored only in your browser's localStorage. 
          They are never transmitted to our servers. For production deployments, 
          we recommend setting environment variables on your server instead.
        </p>
      </div>
    </section>
  );
};

