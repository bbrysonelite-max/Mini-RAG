# Claude.md

## rules

1. Always check docs/BUG_SOLUTIONS.md for existing fixes and patterns before fixing any bug.

2. **CRITICAL:** When fixing a bug, identify the root cause, implement the fix, and verify with linting. ALWAYS end with a simple one-sentence summary using exactly 3 alarm emojis (🚨🚨🚨). This is mandatory and must be the very last sentence in your response.

3. Always provide Mac-specific keyboard shortcuts and terminal commands (use Cmd instead of Ctrl, etc.). The user is on macOS.

4. When we add UI elements that repeat between pages, either reuse an existing shared component or refactor the repeated markup into a shared component before finishing the task.

5. When creating or editing README files, always add these social media links at the top of the file, right after the main title: ```markdown
   [Social media links placeholder]
   ```


