# Football Predictor - React Frontend Plan

## Overview

A modern, responsive React dashboard for visualising football predictions, tracking accuracy, and monitoring system performance. Deployed on Netlify with Supabase backend integration.

---

## Tech Stack

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool (faster than Create React App)
- **Tailwind CSS** - Styling
- **Recharts** - Data visualisation
- **React Query** - Data fetching and caching
- **React Router** - Navigation

### Backend Integration
- **Supabase JS Client** - Direct database access
- **Supabase Auth** - User authentication (optional Phase 2)

### Deployment
- **Netlify** - Static hosting
- **Netlify Functions** - Serverless API endpoints (if needed)

---

## Key Features

### Phase 1 (MVP - Week 1-2)

1. **Dashboard Home**
   - Upcoming fixtures with predictions
   - Confidence scores highlighted
   - League filter
   - Date range selector

2. **Predictions Table**
   - Sortable columns (date, confidence, league)
   - Color-coded confidence levels
   - Expandable rows for detailed stats
   - Export to CSV

3. **Performance Metrics**
   - Overall accuracy by prediction type
   - Accuracy trends over time (line chart)
   - Best performing prediction types
   - Recent results summary

4. **System Status**
   - Current learning weights
   - Last update timestamp
   - Predictions made vs completed
   - API health status

### Phase 2 (Enhanced - Week 3-4)

5. **Historical Analysis**
   - Past predictions with actual results
   - Win/loss patterns
   - League-specific performance
   - Confidence bucket analysis

6. **Advanced Filters**
   - Filter by team
   - Filter by prediction confidence
   - Filter by accuracy
   - Date range selection

7. **Visualisations**
   - Accuracy trends chart
   - Weight evolution over time
   - Confidence distribution
   - League comparison

8. **Settings Panel**
   - Configure display preferences
   - Export options
   - Notification settings (email via Resend)

### Phase 3 (Future)

9. **User Accounts**
   - Save favourite teams
   - Custom alerts
   - Personal betting history
   - ROI tracking

10. **Advanced Features**
    - Live odds integration
    - Betting strategy simulator
    - Mobile app (React Native)
    - Social sharing

---

## Page Structure

```
/
├── /dashboard              # Main dashboard
├── /predictions            # All predictions table
├── /results               # Historical results
├── /performance           # Accuracy metrics
├── /system               # System status & weights
└── /about                # About the system
```

---

## Component Hierarchy

```
App
├── Layout
│   ├── Header
│   │   ├── Logo
│   │   ├── Navigation
│   │   └── ThemeToggle
│   ├── Sidebar (optional)
│   └── Footer
├── Pages
│   ├── Dashboard
│   │   ├── StatsCards (4 cards: accuracy, pending, recent, confidence)
│   │   ├── UpcomingFixtures
│   │   │   └── FixtureCard (repeatable)
│   │   ├── RecentResults
│   │   │   └── ResultCard (repeatable)
│   │   └── AccuracyChart
│   ├── PredictionsPage
│   │   ├── FilterBar
│   │   ├── PredictionsTable
│   │   │   └── PredictionRow (repeatable)
│   │   └── ExportButton
│   ├── PerformancePage
│   │   ├── OverallStats
│   │   ├── AccuracyByType
│   │   ├── TrendChart
│   │   └── ConfidenceAnalysis
│   ├── SystemPage
│   │   ├── CurrentWeights
│   │   ├── WeightEvolution
│   │   ├── SystemHealth
│   │   └── UpdateLog
│   └── ResultsPage
│       ├── ResultsFilter
│       └── ResultsTable
└── Common Components
    ├── LoadingSpinner
    ├── ErrorBoundary
    ├── Modal
    ├── Tooltip
    └── Badge
```

---

## Data Flow

```
Supabase Database
       ↓
React Query (caching & refetching)
       ↓
React Components (state management)
       ↓
Tailwind CSS (styling)
       ↓
User Interface
```

### API Queries

```typescript
// Example React Query hooks
useUpcomingPredictions(days?: number)
useHistoricalResults(limit?: number)
useAccuracyMetrics()
useLearningWeights()
useSystemStatus()
```

---

## Design System

### Color Palette

```css
/* Confidence Levels */
--confidence-very-high: #10B981  /* Green - 0.8+ */
--confidence-high: #3B82F6       /* Blue - 0.6-0.8 */
--confidence-medium: #F59E0B     /* Amber - 0.4-0.6 */
--confidence-low: #EF4444        /* Red - 0.0-0.4 */

/* Prediction Types */
--home-win: #2563EB
--draw: #6B7280
--away-win: #DC2626
--over: #059669
--under: #7C3AED
--btts: #EA580C

/* UI */
--background: #F9FAFB
--surface: #FFFFFF
--border: #E5E7EB
--text-primary: #111827
--text-secondary: #6B7280
```

### Typography

- **Headings**: Inter font family
- **Body**: Inter font family
- **Monospace**: JetBrains Mono (for numbers)

### Component Styles

#### Stat Card
```typescript
<div className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition">
  <h3 className="text-gray-500 text-sm font-medium">Overall Accuracy</h3>
  <p className="text-3xl font-bold text-gray-900 mt-2">68.5%</p>
  <p className="text-sm text-green-600 mt-1">↑ 2.3% from last week</p>
</div>
```

#### Prediction Row
```typescript
<tr className="border-b hover:bg-gray-50">
  <td className="px-4 py-3">2025-11-25</td>
  <td className="px-4 py-3 font-medium">Celtic vs Rangers</td>
  <td className="px-4 py-3">
    <span className="text-blue-600 font-bold">72%</span>
  </td>
  <td className="px-4 py-3">
    <Badge color="green" text="0.89" />
  </td>
</tr>
```

---

## Supabase Integration

### Database Connection

```typescript
// src/lib/supabase.ts
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

### Example Queries

```typescript
// Get upcoming predictions
export async function getUpcomingPredictions() {
  const { data, error } = await supabase
    .from('predictions')
    .select('*')
    .is('actual_result', null)
    .gte('match_date', new Date().toISOString().split('T')[0])
    .order('match_date', { ascending: true })
    .limit(20)

  if (error) throw error
  return data
}

// Get accuracy metrics
export async function getAccuracyMetrics() {
  const { data, error } = await supabase
    .from('accuracy_overview')
    .select('*')

  if (error) throw error
  return data
}

// Get learning weights
export async function getLearningWeights() {
  const { data, error } = await supabase
    .from('learning_weights')
    .select('*')
    .order('last_adjusted', { ascending: false })

  if (error) throw error
  return data
}
```

---

## File Structure

```
frontend/
├── public/
│   ├── favicon.ico
│   └── logo.png
├── src/
│   ├── assets/
│   │   ├── images/
│   │   └── icons/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   └── ErrorMessage.tsx
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── Sidebar.tsx
│   │   ├── dashboard/
│   │   │   ├── StatsCard.tsx
│   │   │   ├── UpcomingFixtures.tsx
│   │   │   ├── RecentResults.tsx
│   │   │   └── AccuracyChart.tsx
│   │   ├── predictions/
│   │   │   ├── PredictionsTable.tsx
│   │   │   ├── PredictionRow.tsx
│   │   │   └── FilterBar.tsx
│   │   └── performance/
│   │       ├── AccuracyMetrics.tsx
│   │       ├── TrendChart.tsx
│   │       └── ConfidenceAnalysis.tsx
│   ├── hooks/
│   │   ├── usePredictions.ts
│   │   ├── useAccuracy.ts
│   │   ├── useWeights.ts
│   │   └── useSystemStatus.ts
│   ├── lib/
│   │   ├── supabase.ts
│   │   ├── api.ts
│   │   └── utils.ts
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Predictions.tsx
│   │   ├── Performance.tsx
│   │   ├── System.tsx
│   │   └── Results.tsx
│   ├── types/
│   │   ├── predictions.ts
│   │   ├── accuracy.ts
│   │   └── weights.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── .env.example
├── .eslintrc.json
├── .gitignore
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
├── vite.config.ts
└── README.md
```

---

## Development Workflow

### Setup

```bash
# Create React app with Vite
npm create vite@latest frontend -- --template react-ts
cd frontend

# Install dependencies
npm install
npm install @supabase/supabase-js
npm install @tanstack/react-query
npm install react-router-dom
npm install recharts
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Install additional utilities
npm install date-fns
npm install clsx
npm install react-icons
```

### Development

```bash
# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Variables

```bash
# .env.example
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key_here
```

---

## Netlify Deployment

### Setup

1. **Connect Repository**
   - Log in to Netlify
   - Click "Add new site" → "Import an existing project"
   - Connect to GitHub
   - Select `football-predictor` repository

2. **Configure Build Settings**
   ```
   Base directory: frontend
   Build command: npm run build
   Publish directory: frontend/dist
   ```

3. **Environment Variables**
   - Go to Site settings → Build & deploy → Environment
   - Add:
     - `VITE_SUPABASE_URL`
     - `VITE_SUPABASE_ANON_KEY`

4. **Deploy**
   - Click "Deploy site"
   - Wait 2-3 minutes
   - Site will be live at `your-site-name.netlify.app`

### Custom Domain (Optional)

```
# Add custom domain in Netlify settings
football-predictor.yourdomain.com
```

### Continuous Deployment

- Push to `main` branch → Automatic deployment
- Pull requests → Deploy previews

---

## Key Features Implementation

### 1. Confidence Badge Component

```typescript
// components/common/ConfidenceBadge.tsx
interface ConfidenceBadgeProps {
  score: number;
}

export function ConfidenceBadge({ score }: ConfidenceBadgeProps) {
  const getColor = (score: number) => {
    if (score >= 0.8) return 'bg-green-100 text-green-800';
    if (score >= 0.6) return 'bg-blue-100 text-blue-800';
    if (score >= 0.4) return 'bg-amber-100 text-amber-800';
    return 'bg-red-100 text-red-800';
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getColor(score)}`}>
      {score.toFixed(2)}
    </span>
  );
}
```

### 2. Upcoming Fixtures Component

```typescript
// components/dashboard/UpcomingFixtures.tsx
import { useQuery } from '@tanstack/react-query';
import { getUpcomingPredictions } from '../../lib/api';
import { ConfidenceBadge } from '../common/ConfidenceBadge';

export function UpcomingFixtures() {
  const { data: fixtures, isLoading, error } = useQuery({
    queryKey: ['upcoming-fixtures'],
    queryFn: getUpcomingPredictions,
    refetchInterval: 60000, // Refetch every minute
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b">
        <h2 className="text-lg font-semibold">Upcoming Fixtures</h2>
      </div>
      <div className="divide-y">
        {fixtures?.map((fixture) => (
          <div key={fixture.id} className="px-6 py-4 hover:bg-gray-50">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm text-gray-500">{fixture.match_date}</p>
                <p className="font-medium mt-1">
                  {fixture.home_team} vs {fixture.away_team}
                </p>
              </div>
              <ConfidenceBadge score={fixture.confidence_score} />
            </div>
            <div className="mt-3 flex gap-4 text-sm">
              <span className="text-blue-600">
                Home Win: {fixture.predicted_home_win_pct}%
              </span>
              <span className="text-gray-600">
                Draw: {fixture.predicted_draw_pct}%
              </span>
              <span className="text-red-600">
                Away Win: {fixture.predicted_away_win_pct}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 3. Accuracy Trend Chart

```typescript
// components/performance/AccuracyTrendChart.tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { getAccuracyTrends } from '../../lib/api';

export function AccuracyTrendChart() {
  const { data, isLoading } = useQuery({
    queryKey: ['accuracy-trends'],
    queryFn: getAccuracyTrends,
  });

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold mb-4">Accuracy Over Time</h2>
      <LineChart width={800} height={400} data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis domain={[0, 100]} label={{ value: 'Accuracy %', angle: -90 }} />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="home_win" stroke="#2563EB" strokeWidth={2} />
        <Line type="monotone" dataKey="over_25" stroke="#059669" strokeWidth={2} />
        <Line type="monotone" dataKey="btts" stroke="#EA580C" strokeWidth={2} />
      </LineChart>
    </div>
  );
}
```

---

## Performance Optimisation

### React Query Configuration

```typescript
// src/lib/queryClient.ts
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60000, // 1 minute
      cacheTime: 300000, // 5 minutes
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});
```

### Code Splitting

```typescript
// Lazy load pages
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Predictions = lazy(() => import('./pages/Predictions'));
const Performance = lazy(() => import('./pages/Performance'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/predictions" element={<Predictions />} />
        <Route path="/performance" element={<Performance />} />
      </Routes>
    </Suspense>
  );
}
```

---

## Testing Strategy

### Unit Tests
- Component rendering
- Hook functionality
- Utility functions

### Integration Tests
- API calls
- Data flow
- User interactions

### E2E Tests (Cypress)
- Complete user journeys
- Critical paths

---

## Timeline

| Week | Tasks | Deliverables |
|------|-------|-------------|
| Week 1 | Project setup, basic components | Dashboard MVP |
| Week 2 | Data integration, styling | Functional predictions view |
| Week 3 | Charts, filters, advanced features | Performance metrics |
| Week 4 | Testing, optimisation, deployment | Production-ready app |

---

## Next Steps

1. **Initialize React project**
   ```bash
   cd ~/football-predictor
   npm create vite@latest frontend -- --template react-ts
   ```

2. **Set up Tailwind CSS**
3. **Create Supabase client**
4. **Build Dashboard layout**
5. **Implement first components**
6. **Deploy to Netlify**

---

**Ready to build a beautiful frontend for your prediction system!** 🎨⚽
