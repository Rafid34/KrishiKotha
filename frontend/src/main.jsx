// Self-hosted font imports (via @fontsource packages) — all 5 font families
// 1. Newsreader (editorial serif for headings and score numbers)
import '@fontsource/newsreader/300.css';
import '@fontsource/newsreader/300-italic.css';
import '@fontsource/newsreader/400.css';
import '@fontsource/newsreader/400-italic.css';
import '@fontsource/newsreader/600.css';

// 2. Instrument Sans (modern sans-serif for UI, navigation and body)
import '@fontsource/instrument-sans/400.css';
import '@fontsource/instrument-sans/500.css';
import '@fontsource/instrument-sans/600.css';
import '@fontsource/instrument-sans/700.css';

// 3. Noto Serif Bengali (Bangla headings, weight 400+)
import '@fontsource/noto-serif-bengali/400.css';
import '@fontsource/noto-serif-bengali/600.css';
import '@fontsource/noto-serif-bengali/700.css';

// 4. Noto Sans Bengali (Bangla UI & body, weight 400+)
import '@fontsource/noto-sans-bengali/400.css';
import '@fontsource/noto-sans-bengali/500.css';
import '@fontsource/noto-sans-bengali/700.css';

// 5. Inter (retained for system Latin fallback)
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';

// Leaflet default icon fix (must come before any Leaflet import)
import 'leaflet/dist/leaflet.css';

// Global styles
import './styles/global.css';

import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
