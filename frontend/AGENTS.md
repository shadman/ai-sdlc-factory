# Frontend Agent Instructions

## Tech Stack
- Angular 17+
- Styling: Tailwind CSS
- State: RxJS / Signals

## Critical Rules
- **Components:** Use Standalone Components only.
- **UI:** Follow the color palette defined in `tailwind.config.js`.
- **API:** Use the `ApiService` wrapper for all HTTP calls; do not use `HttpClient` directly in components.
- **Verification:** Run `ng lint` and `npm audit` after adding dependencies.

