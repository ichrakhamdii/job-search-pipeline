# Frontend (React + Vite + TypeScript)

Web UI for the job search pipeline: sign up, upload a CV, run a search, review ranked matches, track applications, and generate tailored application material.

## Structure

```
src/
├── components/   # Reusable UI: Button, Input, Card, Spinner, Table, ApiKeysForm, Layout
├── context/      # AuthContext (JWT storage + auto-refresh), ThemeContext (light/dark)
├── features/
│   ├── auth/         # Login, Register, ProtectedRoute
│   ├── dashboard/    # Job search trigger + polling, ranked results table, application status board
│   └── tailor/       # CV upload, tailored CV / cover letter / mock interview generation
├── services/     # api.ts (typed Axios client), types.ts (mirrors backend schemas)
└── App.tsx       # Routes and provider wiring
```

## API keys

Voyage AI, Groq, and Adzuna keys are entered by the user in the UI (`ApiKeysForm`) and stored only in that browser's `localStorage` — never sent anywhere except this app's own backend on each request, never persisted server-side.

## Setup

```bash
npm install
cp .env.example .env   # set VITE_API_URL to your running backend
npm run dev
```

## Build

```bash
npm run build
```
