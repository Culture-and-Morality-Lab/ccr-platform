---
paths:
  - "frontend/**/*.jsx"
  - "frontend/**/*.js"
  - "frontend/**/*.css"
---

# Frontend rules

- Scale rule (Deva, 2026-07-10): any list or dropdown that can exceed ~15 options must be
  searchable and grouped (see ConstructPicker.jsx for the house pattern: search + category
  groups + recently-used + full keyboard navigation). Flat selects are for short, fixed lists.

- Current stack: React 18 + Vite, JavaScript (TypeScript arrives in Phase 2 cleanup - do not introduce it piecemeal now).
- All server communication through frontend/src/api.js - no fetch calls inside components.
- The UI never computes analysis values; it renders what the API returns. If a number needs computing, it belongs in the backend.
- Warnings from the API are always rendered (amber panel); never drop or reword warning text in the UI.
- Accessibility floor (design §19): label every input, keyboard-navigable controls, no color-only signals, charts need an accessible alternative.
- Keep the dependency count minimal (currently react + react-dom only); adding a UI library requires a DECISIONS.md entry.
- After frontend changes that should ship: npm run build (outputs to backend/static/) - the API serves the built SPA.
