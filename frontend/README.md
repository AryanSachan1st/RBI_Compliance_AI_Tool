# AI Compliance Copilot — Web UI

React + TypeScript + Vite + Tailwind frontend for the compliance analysis tool.
Assumes the backend implements the API surface in `webui-and-api-plan.md` (upload, status, report, stream).

## Setup

```bash
npm install
npm run dev
```

By default the dev server proxies `/upload-doc/*` requests to `http://localhost:8000`.
If your backend runs elsewhere:

```bash
BACKEND_URL=http://localhost:9000 npm run dev
```

For a production build, requests go to whatever `VITE_API_BASE_URL` is set to
(e.g. in a `.env` file), or same-origin if left unset:

```bash
VITE_API_BASE_URL=https://api.yourcompany.com npm run build
```

## Pages

- `/` — upload a document
- `/status/:docId` — live processing status (SSE with polling fallback if the
  connection drops; safe to refresh or revisit later)
- `/report/:docId` — the finished compliance report

## Structure

```
src/
  api/          fetch wrapper + document endpoints
  hooks/        useDocumentStatus — SSE + reconnect/poll logic
  components/   RiskBadge, StatusStepper, Dropzone, ClauseCard, PageShell
  pages/        UploadPage, StatusPage, ReportPage
  types/api.ts  mirrors the backend's pydantic models
```

## Notes / assumptions made while building

- The backend's `ClauseAnalysis` model has a `clause_test` field name (looks like
  a typo for `clause_text`) — the frontend types use `clause_text`. If the
  backend doesn't fix that typo, update `src/types/api.ts` and `ClauseCard.tsx`
  to match.
- `risk` is treated as a loosely-matched string (`RiskBadge.tsx` does keyword
  matching: "non"/"fail" → Non-Compliant, "review"/"uncertain" → Needs Review,
  "complian" → Compliant) rather than a strict enum, since it's LLM-authored
  text on the backend. Tighten this once the backend locks the exact values it
  returns.
- No History page in this build (by request) — a `doc_id` is only reachable via
  its URL. Add one later against `GET /upload-doc/` whenever that's wanted.
