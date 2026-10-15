import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LangProvider } from './i18n/index.jsx';
import Layout from './components/Layout.jsx';
import Dashboard from './pages/Dashboard.jsx';
import EventReplay from './pages/EventReplay.jsx';
import Simulator from './pages/Simulator.jsx';
import Method from './pages/Method.jsx';

export default function App() {
  return (
    <LangProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="replay" element={<EventReplay />} />
            <Route path="simulator" element={<Simulator />} />
            <Route path="method" element={<Method />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </LangProvider>
  );
}
