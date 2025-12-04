import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'secondbrain_llm_settings';

export interface ProviderSettings {
  apiKey: string;
  selectedModel: string;
}

export interface LLMSettings {
  providers: Record<string, ProviderSettings>;
  preferredProvider: string;
}

const DEFAULT_SETTINGS: LLMSettings = {
  providers: {},
  preferredProvider: 'openai',
};

export function useSettings() {
  const [settings, setSettings] = useState<LLMSettings>(DEFAULT_SETTINGS);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load settings from localStorage
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setSettings(parsed);
      } catch (e) {
        console.error('Failed to parse settings:', e);
      }
    }
    setIsLoaded(true);
  }, []);

  // Save settings to localStorage
  const saveSettings = useCallback((newSettings: LLMSettings) => {
    setSettings(newSettings);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newSettings));
  }, []);

  // Get API key for a specific provider
  const getApiKey = useCallback((provider: string): string | null => {
    return settings.providers[provider]?.apiKey || null;
  }, [settings]);

  // Get the preferred provider's API key
  const getPreferredApiKey = useCallback((): { provider: string; apiKey: string } | null => {
    const provider = settings.preferredProvider;
    const apiKey = settings.providers[provider]?.apiKey;
    if (apiKey) {
      return { provider, apiKey };
    }
    
    // Fallback to any configured provider
    for (const [p, s] of Object.entries(settings.providers)) {
      if (s.apiKey) {
        return { provider: p, apiKey: s.apiKey };
      }
    }
    
    return null;
  }, [settings]);

  // Check if any provider is configured
  const hasConfiguredProvider = useCallback((): boolean => {
    return Object.values(settings.providers).some(p => !!p.apiKey);
  }, [settings]);

  // Build headers with API key for requests
  const getAuthHeaders = useCallback((): Record<string, string> => {
    const preferred = getPreferredApiKey();
    if (!preferred) return {};
    
    // For now, we send the API key as a custom header
    // The backend can pick this up and use it for LLM calls
    return {
      'X-LLM-Provider': preferred.provider,
      'X-LLM-API-Key': preferred.apiKey,
    };
  }, [getPreferredApiKey]);

  return {
    settings,
    isLoaded,
    saveSettings,
    getApiKey,
    getPreferredApiKey,
    hasConfiguredProvider,
    getAuthHeaders,
  };
}

