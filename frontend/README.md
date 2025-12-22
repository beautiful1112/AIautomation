# AIOps Frontend

React + TypeScript frontend for the AIOps Monitoring Dashboard.

## Features

- **Dashboard**: System health overview, summary cards, active incidents preview, and recent agent activity
- **Incidents List**: Filterable table of all incidents with search and filtering capabilities
- **Incident Detail**: Detailed view with timeline, findings, and recommendations
- **Agents Activity**: View agent statistics and activity logs

## Tech Stack

- **React 18** with TypeScript
- **Vite** for build tooling
- **React Router** for routing
- **TanStack Query (React Query)** for data fetching and caching
- **Tailwind CSS** for styling
- **Lucide React** for icons

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`.

## Environment Variables

Create a `.env` file in the frontend directory:

```env
VITE_API_URL=http://localhost:8000
```

If not set, it defaults to `http://localhost:8000`.

## Build

To build for production:

```bash
npm run build
```

The built files will be in the `dist` directory.

## Project Structure

```
src/
  ├── api/          # API client
  ├── components/  # Reusable UI components
  │   └── ui/      # Base UI components (Button, Card, Badge, etc.)
  ├── hooks/       # React Query hooks
  ├── lib/         # Utility functions
  ├── pages/       # Page components
  ├── types.ts     # TypeScript type definitions
  ├── App.tsx      # Main app component with routing
  └── main.tsx     # Entry point
```

