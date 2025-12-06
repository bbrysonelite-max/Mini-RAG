# Version 1.4 - UX Polish & Settings

**Target Release:** TBD
**Focus:** Settings polish + keyboard UX improvements

---

## Settings UX Polish

### Keyboard Shortcuts - Ask Text Box
- [ ] **Enter key submits question**
  - Current: May need to click "Ask" button
  - Target: Pressing Enter/Return submits the question immediately
  - Implementation: Add `onKeyDown` handler to Ask textarea
  
- [ ] **Shift+Enter adds new line**
  - Current: Enter might add new line (unclear behavior)
  - Target: Shift+Enter creates multi-line queries
  - Implementation: Check for `event.shiftKey` in handler

### Settings Panel Improvements
- [ ] **Make settings more discoverable**
  - Add visual indicator when settings need configuration
  - Show which API keys are missing/present
  
- [ ] **Improve API key input UX**
  - Show masked preview of existing keys (e.g., "sk-...xyz")
  - Add "Test Connection" button for each API key
  - Show green/red status indicator

- [ ] **Workspace settings**
  - Add UI to edit workspace default_engine
  - Show dropdown of available engines from engines.json
  - Allow per-workspace model preferences

### Additional UX Polish
- [ ] **Loading states**
  - Show spinner while query is processing
  - Disable Ask button during query to prevent double-submit
  
- [ ] **Error messages**
  - Clearer error messages when API keys missing
  - Helpful suggestions ("Add OPENAI_API_KEY in Settings")
  
- [ ] **Query history**
  - Show recent queries in dropdown/autocomplete
  - Allow re-running previous queries

---

## Technical Implementation

### Ask Text Box Keyboard Handler

**File:** `frontend-react/src/components/AskPanel.tsx`

**Implementation:**
```tsx
const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();  // Prevent newline
    handleAsk();  // Submit question
  }
  // Shift+Enter: default behavior (adds newline)
};

// In textarea:
<textarea
  onKeyDown={handleKeyDown}
  ...
/>
```

### Settings API Connection Test

**Endpoint needed:** `GET /api/v1/settings/test-connection?service=openai|anthropic|cohere`

Returns:
```json
{
  "service": "openai",
  "configured": true,
  "connection": "success" | "failed",
  "error": null | "error message"
}
```

---

## Success Criteria

- [ ] User can submit questions with Enter key (80% faster workflow)
- [ ] Multi-line queries work with Shift+Enter
- [ ] Settings show which services are configured
- [ ] User knows immediately if API keys work
- [ ] Error messages are helpful, not cryptic

---

## Priority

**High Priority:**
- Enter to submit (biggest UX win)
- Shift+Enter for multi-line

**Medium Priority:**
- Settings visual improvements
- API key testing

**Low Priority:**
- Query history/autocomplete

---

## Notes

- Keep changes minimal and focused
- Follow existing React component patterns
- Test keyboard shortcuts on Mac (Cmd) and Windows (Ctrl)
- Maintain accessibility (keyboard navigation)

