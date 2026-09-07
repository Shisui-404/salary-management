# ACME Compensation — Frontend

Next.js (App Router) UI for the ACME salary-management app. Built against
[`docs/api-contract.md`](../docs/api-contract.md) — see that document for the
binding shape of every request/response.

## Stack

- **Next.js 16** (App Router, Turbopack), **TypeScript**, **Tailwind CSS v4**
- **shadcn/ui** (Base UI primitives under the hood, `base-nova` style)
- **TanStack Query** for server state, **TanStack Table v8** for the
  employee directory (the freshly-published v9 has an incompatible API and
  is pinned back deliberately — see `package.json`)
- **Recharts** for the dashboard's charts
- **Vitest + Testing Library** for tests

## Getting started

```bash
cp .env.example .env.local   # point NEXT_PUBLIC_API_URL at your backend
npm install
npm run dev                  # http://localhost:3000
```

`NEXT_PUBLIC_API_URL` defaults to `http://localhost:8000/api/v1` if unset.

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Dev server (Turbopack) |
| `npm run build` | Production build + typecheck — the hard gate |
| `npm run lint` | ESLint (flat config) |
| `npm test` | Vitest, non-watch (`vitest run`) |
| `npm run test:watch` | Vitest in watch mode |

## Screens

- **`/`** — Compensation dashboard: KPI tiles, salary distribution histogram
  with percentile markers, median-by-dimension chart (department / country /
  job role / level switcher), pay-equity panel (with a note on suppressed
  small-sample groups), band-health panel with a linked outlier table.
- **`/employees`** — Directory: server-side paginated/sorted/filtered
  TanStack Table, debounced search, faceted filters from `GET /reference`,
  salary-range filter, CSV export, "Add employee" dialog. Filter/sort/page
  state lives in the URL so views are shareable and back/forward works.
- **`/employees/[id]`** — Profile: current compensation (local + base
  amount, compa-ratio, band gauge), salary history timeline, "Record a
  raise" dialog with client-side validation mirroring the server's
  `salary_effective_date_invalid` rule.

## Architecture

```
src/
├── app/                    # routes (App Router)
├── components/
│   ├── ui/                 # shadcn primitives (generated, lightly used as-is)
│   ├── layout/              # site header/nav
│   ├── shared/              # ErrorState, EmptyState, PageHeader
│   ├── employees/           # directory table, filters, profile, raise dialog
│   └── analytics/           # dashboard KPIs, charts, pay-equity/band-health
├── hooks/                   # TanStack Query hooks + directory filter state
└── lib/
    ├── api/                 # typed client: types.ts mirrors the contract
    │                        # field-for-field, client.ts is the one fetchJson
    │                        # wrapper + typed ApiError, one module per resource
    ├── fixtures/             # contract-shaped sample data (tests + reference)
    ├── format.ts             # money/percent formatting, compa-ratio -> badge,
    │                         # band-position -> color — all unit-tested
    ├── employee-query-params.ts  # directory filters <-> URL round trip
    └── chart-colors.ts       # dashboard color roles (see below)
```

**Money.** Amounts are decimal strings over the wire and are never run
through `parseFloat` for anything but display formatting
(`Intl.NumberFormat`, honouring each currency). The one deliberate exception
is `BandGauge`, which parses `amount_base`/`band.{min,mid,max}` to position a
marker on screen — a geometry problem, not a money calculation — and says so
in a comment.

**Colors.** Chart colors follow Anthropic's dataviz method rather than being
picked ad hoc: `--chart-1`/`--chart-2` in `globals.css` are a validated
categorical blue/orange pair in fixed hue order; band-position colors in
`chart-colors.ts` intentionally reuse the exact hexes behind
`BandPositionBadge` so a chart segment and a badge for "below band" always
look like the same concept.

## Testing

`npm test` runs 44 tests across 5 files: formatting/derivation helpers,
the filter↔URL round trip, the API client's error-envelope parsing (mocked
`fetch`), and two component tests (the employees table rendering fixture
rows, the raise dialog blocking an invalid effective date). Fixtures live in
`src/lib/fixtures/` and are shaped exactly like the contract's example
payloads.

## Known limitations

- No live-backend integration pass had a backend to run against as of the
  last verification — screens were confirmed to render their loading/error
  states without crashing. Re-run against a live API and diff against
  `docs/api-contract.md` before shipping.
- CSV import (`POST /employees/import`) has a typed API client method
  (`importEmployeesCsv`) but no UI — only export and "Add employee" were in
  scope for the directory screen.
- No auth, per the product's documented out-of-scope list.
