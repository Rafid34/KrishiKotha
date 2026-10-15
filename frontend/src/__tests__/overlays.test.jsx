import React from 'react';
import { describe, it, expect } from 'vitest';
import { renderToString } from 'react-dom/server';
import OverlayControl from '../components/OverlayControl.jsx';
import SourceNotes from '../components/SourceNotes.jsx';
import { LangContext } from '../i18n/index.jsx';
import {
  GIBS_LAYERS,
  gibsTileUrl,
  layerAvailability,
  overlayMessageKey,
} from '../config/layers.js';

const render = (node, lang = 'en') =>
  renderToString(<LangContext.Provider value={{ lang, setLang: () => {} }}>{node}</LangContext.Provider>);

const IMERG = GIBS_LAYERS.find(l => l.key === 'imerg');
const NDVI8 = GIBS_LAYERS.find(l => l.key === 'ndvi8');

describe('GIBS layer config (ids confirmed from GetCapabilities 2026-10-15)', () => {
  it('uses the confirmed layer ids and tile matrix sets', () => {
    expect(GIBS_LAYERS.map(l => l.id)).toEqual([
      'IMERG_Precipitation_Rate',
      'MODIS_Terra_L3_NDVI_16Day',
      'MODIS_Terra_NDVI_8Day',
    ]);
    expect(IMERG.tileMatrixSet).toBe('GoogleMapsCompatible_Level6');
    expect(NDVI8.tileMatrixSet).toBe('GoogleMapsCompatible_Level9');
  });

  it('builds a Leaflet URL template for the selected date', () => {
    expect(gibsTileUrl(IMERG, '2022-06-16')).toBe(
      'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/IMERG_Precipitation_Rate/default/2022-06-16/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png',
    );
  });

  it('flags dates outside the layer coverage', () => {
    expect(layerAvailability(IMERG, '2022-06-16', '2026-10-15')).toBe('ok');
    expect(layerAvailability(NDVI8, '2022-06-16', '2026-10-15')).toBe('before_coverage');
    expect(layerAvailability(IMERG, '2027-01-01', '2026-10-15')).toBe('future');
    expect(layerAvailability(IMERG, '', '2026-10-15')).toBe('invalid');
  });

  it('maps states to fallback message keys', () => {
    expect(overlayMessageKey('ok', false)).toBeNull();
    expect(overlayMessageKey('before_coverage')).toBe('overlay.beforeCoverage');
    expect(overlayMessageKey('ok', true)).toBe('overlay.tileError');
  });
});

describe('OverlayControl', () => {
  const base = { onChange: () => {}, tileError: false, layer: null, lang: 'en' };

  it('shows no attribution and no fallback when the overlay is off', () => {
    const html = render(<OverlayControl {...base} value="none" status={null} />);
    expect(html).not.toContain('gibs-credit');
    expect(html).not.toContain('gibs-fallback');
    expect(html).toContain('NASA IMERG precipitation rate');
  });

  it('shows the NASA GIBS attribution when a layer is on', () => {
    const html = render(<OverlayControl {...base} value="imerg" status="ok" layer={IMERG} />);
    expect(html).toContain('gibs-credit');
    expect(html).toContain('Imagery: NASA GIBS');
    expect(html).not.toContain('gibs-fallback');
  });

  it('explains the fallback when the layer has no imagery for the date', () => {
    const html = render(<OverlayControl {...base} value="ndvi8" status="before_coverage" layer={NDVI8} />);
    expect(html).toContain('gibs-fallback');
    expect(html).toContain('this layer starts 2025-02-12');
  });

  it('renders the fallback in Bangla too', () => {
    const html = render(
      <OverlayControl {...base} value="ndvi8" status="before_coverage" layer={NDVI8} lang="bn" />,
      'bn',
    );
    expect(html).toContain('শুধু মূল মানচিত্র');
  });
});

describe('SourceNotes (soil source and NDVI fallback)', () => {
  it('shows SMAP as the soil source with its version', () => {
    const html = render(
      <SourceNotes hazard="flood" soilSource={{ source: 'SMAP_L4', version: '008', fallback: false }} ndvi={null} lang="en" />,
    );
    expect(html).toContain('NASA SMAP L4 root zone percentile');
    expect(html).toContain('(008)');
    expect(html).not.toContain('factor-note--fallback');
  });

  it('shows the POWER fallback for soil moisture', () => {
    const html = render(
      <SourceNotes hazard="drought" soilSource={{ source: 'POWER_GWETROOT', version: 'V2', fallback: true }} ndvi={null} lang="en" />,
    );
    expect(html).toContain('SMAP unavailable for this date, fallback in use');
    expect(html).toContain('factor-note--fallback');
  });

  it('shows the NDVI anomaly with product and version for salinity', () => {
    const html = render(
      <SourceNotes
        hazard="salt"
        soilSource={null}
        ndvi={{ used: true, anomaly: -0.08, product: 'AppEEARS MOD13Q1.061 NDVI anomaly', version: '061' }}
        lang="en"
      />,
    );
    expect(html).toContain('-0.080');
    expect(html).toContain('MOD13Q1.061');
    expect(html).toContain('(v061)');
  });

  it('shows the Level 1 fallback when NDVI is unavailable', () => {
    const html = render(<SourceNotes hazard="salt" soilSource={null} ndvi={{ used: false }} lang="en" />);
    expect(html).toContain('salinity uses the Level 1 formula without NDVI');
  });

  it('shows nothing for snapshots stored before Phase 10', () => {
    expect(render(<SourceNotes hazard="flood" soilSource={null} ndvi={null} lang="en" />)).not.toContain('factor-note');
  });
});
