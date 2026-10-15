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
 * RiskMap â€” Leaflet map with 8 district markers coloured by the active hazard level.
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

  // Build a lookup: district_id â†’ risk entry
  const riskByDistrict = useMemo(() => {
    const map = {};
    for (const r of riskData) map[r.district_id] = r;
    return map;
  }, [riskData]);

  return (
    <div className="risk-map" role="region" aria-label="District risk map">
      <MapContainer
        center={BANGLADESH_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ width: '100%', height: '100%', minHeight: 340 }}
        zoomControl={true}
        attributionControl={true}
        id="district-risk-map"
      >
        {/* OpenStreetMap base tiles */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={18}
        />

        {/* NASA GIBS overlay: added when selected and available, removed otherwise */}
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

        {/* District markers */}
        {districts.map(district => {
          const risk = riskByDistrict[district.id];
          const hazardData = risk?.[hazard];
          const level = hazardData?.level ?? 'low';
          const score = hazardData?.score;
          const color = levelColor(level);
          const districtName = lang === 'bn' ? district.name_bn : district.name_en;
          const hazardName = hazardLabel(hazard, lang);
          const isSelected = selectedId === district.id;

          // aria-label per spec Â§8.4: "Sylhet, flood risk high, score 84"
          const ariaLabel = `${district.name_en}, ${hazardLabel(hazard, 'en')} risk ${level}${score != null ? `, score ${Math.round(score)}` : ''}`;

          return (
            <CircleMarker
              key={district.id}
              center={[district.lat, district.lon]}
              radius={isSelected ? 20 : 16}
              pathOptions={{
                fillColor: color,
                color: isSelected ? 'var(--ink)' : (level === 'moderate' ? 'var(--ink)' : '#fff'),
                weight: isSelected ? 3 : 2,
                fillOpacity: 0.85,
                opacity: 1,
              }}
              eventHandlers={{
                click: () => onSelectDistrict?.(district.id),
              }}
              aria-label={ariaLabel}
              title={ariaLabel}
            >
              <Tooltip
                direction="top"
                offset={[0, -16]}
                permanent={false}
                sticky={false}
                opacity={1}
              >
                <div className="map-tooltip" lang={lang === 'bn' ? 'bn' : undefined}>
                  <strong>{districtName}</strong>
                  <div className="map-tooltip__row">
                    <span>{hazardName}:</span>
                    <span style={{ color: level === 'moderate' ? 'var(--risk-moderate-text)' : color, fontWeight: 700 }}>
                      {score != null ? Math.round(score) : 'â€”'}
                    </span>
                  </div>
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

/* â”€â”€â”€ Styles â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const style = document.createElement('style');
style.textContent = `
.risk-map {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 340px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.overlay-control {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 1000;
  max-width: min(240px, calc(100% - 70px));
  margin: 0;
  padding: 6px 10px 8px;
  background: rgba(255,255,255,.95);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  font-size: 12px;
  color: var(--ink);
}
.overlay-control__title { font-weight: 700; padding: 0 4px; }
.overlay-control__option {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  cursor: pointer;
}
.overlay-control__option input:focus-visible { outline: 3px solid var(--brand); outline-offset: 2px; }
.overlay-control__credit { margin: 4px 0 0; color: var(--nasa-blue); font-weight: 600; }
.overlay-control__fallback { margin: 4px 0 0; color: #856404; background: #FFF3CD; border-radius: var(--radius-sm); padding: 4px 6px; }

.map-tooltip {
  font-size: 13px;
  line-height: 1.4;
  min-width: 100px;
}
.map-tooltip__row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-top: 2px;
}

/* Leaflet tooltip custom styling */
.leaflet-tooltip {
  background: white !important;
  border: none !important;
  box-shadow: 0 2px 8px rgba(0,0,0,.18) !important;
  border-radius: 8px !important;
  padding: 8px 12px !important;
  color: var(--ink) !important;
}
.leaflet-tooltip-top::before {
  border-top-color: white !important;
}
`;
if (!document.getElementById('risk-map-styles')) {
  style.id = 'risk-map-styles';
  document.head.appendChild(style);
}

