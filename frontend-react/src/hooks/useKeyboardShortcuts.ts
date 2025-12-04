import { useEffect, useCallback } from 'react';

export interface KeyboardShortcut {
  key: string;
  ctrl?: boolean;
  alt?: boolean;
  shift?: boolean;
  meta?: boolean;
  action: () => void;
  description: string;
  category?: string;
}

export const useKeyboardShortcuts = (shortcuts: KeyboardShortcut[], enabled: boolean = true) => {
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!enabled) return;

    // Don't trigger shortcuts when typing in inputs
    const target = event.target as HTMLElement;
    if (
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable
    ) {
      // Allow escape key even in inputs
      if (event.key !== 'Escape') {
        return;
      }
    }

    for (const shortcut of shortcuts) {
      const keyMatches = event.key.toLowerCase() === shortcut.key.toLowerCase();
      const ctrlMatches = !!shortcut.ctrl === (event.ctrlKey || event.metaKey);
      const altMatches = !!shortcut.alt === event.altKey;
      const shiftMatches = !!shortcut.shift === event.shiftKey;

      if (keyMatches && ctrlMatches && altMatches && shiftMatches) {
        event.preventDefault();
        shortcut.action();
        break;
      }
    }
  }, [shortcuts, enabled]);

  useEffect(() => {
    if (!enabled) return;

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown, enabled]);
};

// Common shortcuts for the app
export const APP_SHORTCUTS = {
  FOCUS_SEARCH: { key: 'k', ctrl: true, description: 'Focus search / ask', category: 'Navigation' },
  GO_TO_INGEST: { key: 'i', ctrl: true, description: 'Go to ingest', category: 'Navigation' },
  GO_TO_SOURCES: { key: 's', ctrl: true, description: 'Go to sources', category: 'Navigation' },
  GO_TO_ASSETS: { key: 'a', ctrl: true, description: 'Go to assets', category: 'Navigation' },
  GO_TO_ADMIN: { key: ',', ctrl: true, description: 'Go to admin/settings', category: 'Navigation' },
  ESCAPE: { key: 'Escape', description: 'Close modal / clear focus', category: 'General' },
  HELP: { key: '?', shift: true, description: 'Show keyboard shortcuts', category: 'General' },
};

