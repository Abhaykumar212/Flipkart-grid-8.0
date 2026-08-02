# Implementation Backlog

Items discovered outside the active phase are recorded here to avoid expanding phase scope.

- Upgrade `react-router-dom` when a compatible release clears the current high-severity RSC-mode advisory reported by `npm audit`. This storefront uses `BrowserRouter`, not RSC mode.
- Separate shared exports from React component/context modules to clear the existing Oxlint `react(only-export-components)` Fast Refresh warnings.
- Revisit the FastAPI/Starlette test client when its documented `httpx2` replacement is stable; the pinned Phase 0 stack currently emits a deprecation warning.
