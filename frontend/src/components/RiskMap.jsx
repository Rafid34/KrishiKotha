import React, { useState, useEffect, useRef, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { MapContainer, TileLayer, CircleMarker, Tooltip, useMap } from 'react-leaflet';
import L from 'leaflet';
import Legend from './Legend.jsx';
import { levelColor, hazardLabel } from '../utils/risk.js';
import { useLang } from '../i18n/index.jsx';
import OverlayControl from './OverlayControl.jsx';
import { GIBS_LAYERS, GIBS_ATTRIBUTION, gibsTileUrl, layerAvailability } from '../config/layers.js';

// Bangladesh approximate centre
const BANGLADESH_CENTER = [23.685, 90.356];
const DEFAULT_ZOOM = 7;

/** Fix Leaflet's default icon paths when bundled with Vite */
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: new URL('leaflet/dist/images/marker-icon-2x.png', import.meta.url).href,
  iconUrl: new URL('leaflet/dist/images/marker-icon.png', import.meta.url).href,
  shadowUrl: new URL('leaflet/dist/images/marker-shadow.png', import.meta.url).href,
});

/**
 * Renders the Legend as a Leaflet custom control positioned at bottom-left.
 */
function LegendControl() {
  const map = useMap();
  const [container, setContainer] = useState(null);

  useEffect(() => {
    const control = L.control({ position: 'bottomleft' });
    control.onAdd = () => {
      const div = L.DomUtil.create('div', 'leaflet-legend-control');
      L.DomEvent.disableClickPropagation(div);
      return div;
    };
    control.addTo(map);
    setContainer(control.getContainer());
    return () => control.remove();
  }, [map]);

  return container ? createPortal(<Legend />, container) : null;
}

/**
 * RiskMap — Leaflet map with 8 district markers, dark pill labels, and Catalog label.
 *
 * @param {{
 *   districts: Array<{id, name_en, name_bn, lat, lon}>,
 *   riskData: Array<{district_id, drought, flood, salt}>,
 *   hazard: 'drought'|'flood'|'salt',
 *   selectedId: string|null,
 *   onSelectDistrict: (id: string) => void,
 *   date: string|null,   // YYYY-MM-DD used for the GIBS overlay time
 * }} props
 */
export default function RiskMap({
  districts = [],
  riskData = [],
  hazard = 'flood',
  selectedId = null,
  onSelectDistrict,
  date = null,
}) {
  const { lang } = useLang();
  const [overlayKey, setOverlayKey] = useState('none');
  const [tileError, setTileError] = useState(false);
  const overlayLayer = GIBS_LAYERS.find(l => l.key === overlayKey) ?? null;
  const overlayStatus = overlayLayer ? layerAvailability(overlayLayer, date) : null;
  const showOverlay = overlayLayer && overlayStatus === 'ok';

  useEffect(() => { setTileError(false); }, [overlayKey, date]);

  // Build a lookup: district_id -> risk entry
  const riskByDistrict = useMemo(() => {
    const map = {};
    for (const r of riskData) map[r.district_id] = r;
    return map;
  }, [riskData]);

  const catalogDateStr = date || '16 Jun 2022';
  const catalogHazardStr = hazardLabel(hazard, 'en');

  return (
    <div className="risk-map" role="region" aria-label="District risk map">
      {/* Catalog label (technical metadata badge) */}
      <div className="catalog-label map-catalog-label" aria-hidden="true">
        <span className="catalog-label__dot" />
        <span className="catalog-label__mono">
          Fig. 1 {catalogHazardStr} risk, {catalogDateStr}
        </span>
      </div>

      <MapContainer
        center={BANGLADESH_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ width: '100%', height: '100%', minHeight: 340, background: '#0C0A09' }}
        zoomControl={true}
        attributionControl={true}
        id="district-risk-map"
      >
        {/* Dark Matter Carto basemap that reads cleanly on dark UI */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank" rel="noopener">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          maxZoom={18}
        />

        {/* NASA GIBS overlay */}
        {showOverlay && (
          <TileLayer
            key={`${overlayLayer.id}-${date}`}
            url={gibsTileUrl(overlayLayer, date)}
            attribution={GIBS_ATTRIBUTION}
            opacity={overlayLayer.opacity}
            maxNativeZoom={overlayLayer.maxNativeZoom}
            maxZoom={18}
            eventHandlers={{ tileerror: () => setTileError(true) }}
          />
        )}

        {/* District markers: equally sized (radius 16), solid dark pill labels */}
        {districts.map(district => {
          const risk = riskByDistrict[district.id];
          const hazardData = risk?.[hazard];
          const level = hazardData?.level ?? 'low';
          const score = hazardData?.score;
          const color = levelColor(level);
          const districtName = lang === 'bn' ? district.name_bn : district.name_en;
          const isSelected = selectedId === district.id;

          // aria-label per spec §8.4: "Sylhet, flood risk high, score 84"
          const ariaLabel = `${district.name_en}, ${hazardLabel(hazard, 'en')} risk ${level}${score != null ? `, score ${Math.round(score)}` : ''}`;

          return (
            <CircleMarker
              key={district.id}
              center={[district.lat, district.lon]}
              radius={16}
              pathOptions={{
                fillColor: color,
                color: isSelected ? 'var(--accent)' : 'rgba(255, 255, 255, 0.7)',
                weight: isSelected ? 3.5 : 1.5,
                fillOpacity: 0.9,
                opacity: 1,
              }}
              eventHandlers={{
                click: () => onSelectDistrict?.(district.id),
              }}
              aria-label={ariaLabel}
              title={ariaLabel}
            >
              {/* Permanent solid dark pill label showing district name + numeric score */}
              <Tooltip
                direction="top"
                offset={[0, -16]}
                permanent={true}
                className="map-marker-pill"
              >
                <div className="map-marker-pill__content" lang={lang === 'bn' ? 'bn' : undefined}>
                  <span className="map-marker-pill__name">{districtName}</span>
                  <span
                    className="map-marker-pill__score"
                    style={{ color: color, fontWeight: 700 }}
                  >
                    {score != null ? Math.round(score) : '—'}
                  </span>
                </div>
              </Tooltip>
            </CircleMarker>
          );
        })}

        {/* Legend inside the map */}
        <LegendControl />
      </MapContainer>

      <OverlayControl
        value={overlayKey}
        onChange={setOverlayKey}
        status={overlayStatus}
        tileError={tileError}
        layer={overlayLayer}
        lang={lang}
      />
    </div>
  );
}

/* ─── Styles ────────────────────────────────────────────────────────── */
const style = typeof document !== 'undefined' ? document.createElement('style') : null;
if (style) {
  style.textContent = `
.risk-map {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 380px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

/* Catalog label positioned top-left over map */
.map-catalog-label {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 1000;
  box-shadow: var(--shadow-sm);
}

/* Solid dark pill background for Leaflet markers */
.leaflet-tooltip.map-marker-pill {
  background: #1C1917 !important;
  border: 1px solid rgba(255, 255, 255, 0.18) !important;
  color: #E7E5E4 !important;
  border-radius: var(--radius-full) !important;
  padding: 3px 10px !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.6) !important;
  font-family: var(--font-sans);
  pointer-events: none;
}
.leaflet-tooltip-top.map-marker-pill::before {
  border-top-color: #1C1917 !important;
}
.map-marker-pill__content {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  line-height: 1.2;
}
.map-marker-pill__name {
  font-weight: 500;
  color: #E7E5E4;
}
.map-marker-pill__score {
  font-family: var(--font-serif);
  font-size: 12px;
}

/* Dark mode OverlayControl */
.overlay-control {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 1000;
  max-width: min(260px, calc(100% - 60px));
  margin: 0;
  padding: 8px 12px 10px;
  background: rgba(28, 25, 24, 0.92);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  font-size: 12px;
  color: var(--foreground);
}
.overlay-control__title {
  font-weight: 600;
  padding: 0 4px;
  color: var(--foreground);
}
.overlay-control__option {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  cursor: pointer;
  color: var(--ink-muted);
}
.overlay-control__option:hover {
  color: var(--foreground);
}
.overlay-control__option input:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.overlay-control__credit {
  margin: 6px 0 0;
  color: var(--nasa-blue);
  font-weight: 600;
  font-size: 11px;
}
.overlay-control__fallback {
  margin: 6px 0 0;
  color: var(--risk-moderate);
  background: rgba(251, 191, 36, 0.12);
  border: 1px solid rgba(251, 191, 36, 0.3);
  border-radius: var(--radius-sm);
  padding: 4px 6px;
  font-size: 11px;
}
`;
  if (!document.getElementById('risk-map-styles')) {
    style.id = 'risk-map-styles';
    document.head.appendChild(style);
  }
}
