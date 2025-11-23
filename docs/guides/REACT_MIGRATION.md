# React Migration Playbook

This guide documents how to roll out the new Vite/React shell alongside the existing vanilla UI, toggle between them, and keep the experience smooth during the transition.

## Goals
1. Deliver a modern component-based UI without breaking the current `/app` workflow.
2. Provide a clear toggle for beta testers (e.g., `/app-react`).
3. Keep auth, billing banners, and workspace context consistent across both frontends.

## Architecture
- **Legacy UI:** Served at `/app` (static `frontend/index.html`). Remains default until React reaches feature parity.
- **React UI:** Built from `frontend-react/`, served at `/app-react` once compiled (`vite build` output deployed to `dist/`).
- **API:** All clients use the same `/api/v1/*` endpoints. Authentication (JWT or API key) is shared.

## Local Development
```bash
# Backend
uvicorn server:app --reload

# React dev server
cd frontend-react
npm install
npm run dev
```

The Vite dev server proxies `/api`, `/auth`, and `/ask` to `http://localhost:8000`, so there’s no CORS hassle during development.

## Deployment Toggle
1. **Short term:** The backend automatically serves `/app` (legacy) and `/app-react` (React build) whenever `frontend-react/dist` exists. Create the build with `npm run build` before deploying.

2. **Switching default:** Once React hits parity, flip `/app` to the React build and move the legacy UI to `/app-legacy` for a deprecation window.

3. **Config flag (optional):** Introduce an env variable (`USE_REACT_UI=true`) to control which template `/app` serves. Useful for blue/green deploys.

## Auth & Billing Considerations
- React shell relies on the same `/auth/me` endpoint and cookies. Confirm login/logout flows before enabling `/app-react`.
- Billing/quota banners:
  - Fetch `/api/v1/admin/billing` for admin dashboards.
  - Show hard-fail messages when `/api/v1/ingest/*` returns 402/429 (already surfaced in existing API responses).

## Feature Parity Tracker
| Feature | Vanilla UI | React UI | Status |
|---------|------------|----------|--------|
| Ask + chunk preview | ✅ | MVP (Ask panel) | Expand chunk modal + citation details |
| Sources list | ✅ | MVP | Add filter + view chunk modal parity |
| Ingest (URLs) | ✅ | MVP (URLs only) | Add file upload + progress |
| Admin workspace/billing | In progress | Table view | Expand to editing/unlock controls |
| Toasts/loading | ✅ | Basic states | Port advanced toasts + error banners |
| Auth state indicator | ✅ | TODO | Hook `GET /auth/me` into Header component |

## Rollout Plan
1. **Phase 1 (current):** Dev-only React shell accessible at `/app-react`.
2. **Phase 2:** Provide a toggle link in legacy UI (“Try the new experience”) pointing to `/app-react`.
3. **Phase 3:** Switch default to React, keep `/app-legacy` read-only for a release or two.
4. **Phase 4:** Remove legacy UI once React covers all workflows.

## Testing
- Add React build + lint jobs to CI once the shell stabilizes:
  ```yaml
  - run: npm run lint
  - run: npm run build
  ```
- Use Playwright/Cypress for E2E flows once React becomes primary (Phase 3).

## Support & Docs
- Update `README.md` and `docs/guides/UI_NAVIGATION.md` with React-specific instructions.
- Provide a short FAQ: how to switch back to legacy UI, known limitations, how to report issues.

