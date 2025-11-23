# Mini-RAG UI Navigation Blueprint

## Pain Points Observed

- Chunk preview modal trapped the user; “Close” did not return to the list or restore scroll position.
- Navigating between Ask / Sources / Admin required manual URL hacking—no persistent home/back links.
- Authenticated state was hidden; logout button only visible in certain panels.
- Ingest flows lacked loading and error feedback, making it unclear whether requests succeeded.

## Target Flow (Nov 20, 2025)

| Pane | Breadcrumb | Primary Actions | Notes |
|------|------------|-----------------|-------|
| Ask | `Home / Ask` | Submit query, view chunks | Loading spinner while `/ask` runs, empty-state when no chunks. |
| Sources | `Home / Sources` | View, filter, delete sources | Cards link to chunk modal. Close returns to list (restores filter/scroll). |
| Ingest | `Home / Ingest` | Upload files, ingest URLs | Buttons show progress + toast; disabled when billing/quota blocks. |
| Admin | `Home / Admin` | (future) workspace/billing management | Placeholder until admin UI is built. |

### Navigation Shell
- Persistent top bar with:
  - Product name / logo (Mini-RAG).
  - Nav links: Ask, Sources, Ingest, Admin.
  - User avatar/email + logout button.
- Breadcrumb component under the top bar, reflecting current pane. For modals (chunk preview) show `Home / Sources / Chunk`.

### Chunk Modal Behavior
1. Open chunk from sources list.
2. Body scroll locks, breadcrumb updates to include chunk.
3. Close button and ESC dismiss the modal, focus/scroll returns to previous card.

### Feedback & States
- Ask button: spinner + disabled while pending; result area shows “No chunks found” when empty.
- Ingest buttons: disabled during upload; show toast (success/error).
- Banners for billing/quota issues (HTTP 402/429) with CTA to go to Admin/Billing.

## Implementation Checklist

1. Update `frontend/index.html`:
   - Introduce `<header>` with nav links, user info, logout.
   - Add breadcrumb component (e.g., `<nav aria-label="Breadcrumb">`).
   - Refactor chunk modal to reuse shared close helper; add ESC listener.
2. UX states:
   - `#askBtn` toggles loading state; `#statusMessage` for ingest results.
   - Add empty-state text for `#chunksList`, `#sourcesList`, ingest history.
3. Accessibility:
   - Ensure nav links have `aria-current`.
   - Trap focus inside chunk modal while open; return focus on close.

## Future Enhancements

- Replace inline styles with Tailwind or CSS modules.
- Convert UI to component framework (React/Vue) for state management.
- Add keyboard shortcuts (Cmd+K for search, Cmd+Enter to ask).
- Integrate analytics (page view + action telemetry) once privacy review is complete.

