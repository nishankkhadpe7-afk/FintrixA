# RegTech Dashboard - RBI Rule Engine

A trust-first regulatory technology dashboard for viewing RBI circulars, inspecting extracted rules, evaluating inputs against rules, and understanding decision traceability.

## Features

- **Dashboard**: Overview of ingested circulars, extracted rules, and success/failure rates
- **Circular Viewer**: Browse and inspect RBI circulars with full text view
- **Rule Explorer**: View all extracted rules with conditions, actions, and confidence scores
- **Evaluation Panel**: Test loan applications against regulatory rules with detailed debug traces
- **Traceability View**: Understand the origin and impact of each rule

## Tech Stack

- React 18 with TypeScript
- TailwindCSS for styling
- Zustand for state management
- React Query for data fetching
- React Router for navigation
- Vite for build tooling

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

1. Navigate to the frontend directory:

```bash
cd frontend
```

2. Install dependencies:

```bash
npm install
```

3. Start the development server:

```bash
npm run dev
```

4. Open your browser and navigate to `http://localhost:3000`

### Building for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## Project Structure

```
frontend/
├── src/
│   ├── api/           # API integration layer
│   ├── components/    # Reusable UI components
│   │   ├── CircularList.tsx
│   │   ├── EvaluationPanel.tsx
│   │   ├── JSONViewer.tsx
│   │   ├── RuleCard.tsx
│   │   └── TraceTable.tsx
│   ├── hooks/         # Custom React hooks
│   ├── pages/         # Page components
│   │   ├── Dashboard.tsx
│   │   ├── CircularViewer.tsx
│   │   ├── RuleExplorer.tsx
│   │   ├── Evaluation.tsx
│   │   └── Traceability.tsx
│   ├── store/         # Zustand state management
│   ├── types/         # TypeScript type definitions
│   ├── utils/         # Utility functions and sample data
│   ├── App.tsx        # Main application component
│   ├── main.tsx       # Application entry point
│   └── index.css      # Global styles with Tailwind
├── index.html         # HTML entry point
├── package.json       # Dependencies and scripts
├── tsconfig.json      # TypeScript configuration
├── vite.config.ts     # Vite configuration
├── tailwind.config.js # TailwindCSS configuration
└── postcss.config.js  # PostCSS configuration
```

## Design Principles

- **Clarity over aesthetics**: Every element serves a purpose
- **Explainability over animation**: Users understand how decisions are made
- **Traceability over density**: Complete audit trail for every decision
- **Minimal design**: Clean, Stripe/Linear-inspired interface

## Key Components

### RuleCard

Displays individual rules with conditions, actions, and confidence scores. Expandable to show full JSON.

### TraceTable

Shows detailed debug traces for rule evaluations with PASS/FAIL indicators.

### EvaluationPanel

Input form for testing loan applications with real-time evaluation results.

### CircularList

Browse and search RBI circulars with metadata and source links.

### JSONViewer

Syntax-highlighted JSON viewer for rule details.

## State Management

The application uses Zustand for state management with the following stores:

- **Circulars**: List of ingested RBI circulars
- **Rules**: Extracted regulatory rules
- **Evaluation**: Input/output for rule evaluation
- **Dashboard**: Statistics and recent activity

## API Integration

The frontend is configured to proxy API requests to `http://localhost:8000/api`. The API layer includes:

- `GET /api/circulars` - Fetch all circulars
- `GET /api/circulars/:id` - Fetch specific circular
- `GET /api/rules` - Fetch all rules
- `GET /api/rules/:id` - Fetch specific rule
- `POST /api/simulate` - Evaluate input against rules
- `GET /api/stats` - Fetch dashboard statistics

## Sample Data

The application includes sample data for demonstration purposes:

- 3 sample RBI circulars
- 5 sample regulatory rules
- 1 sample evaluation result

## License

This project is part of the RegTech Rule Engine platform.
