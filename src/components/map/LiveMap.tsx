import { MapContainer, TileLayer, CircleMarker, Popup, useMap, Marker } from 'react-leaflet';
import { useEffect } from 'react';
import L from 'leaflet';
import type { RoadAlert } from '@/types';
import type { FleetDevice } from '@/types';
import { DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM, EVENT_META } from '@/lib/constants';
import { alertPopupLines } from '@/lib/alertMeta';
import { useShowFleetOnMap } from '@/context/PreferencesContext';
import 'leaflet/dist/leaflet.css';

function FitBounds({ alerts }: { alerts: RoadAlert[] }) {
  const map = useMap();
  useEffect(() => {
    if (alerts.length < 2) return;
    const lats = alerts.map((a) => a.latitude);
    const lngs = alerts.map((a) => a.longitude);
    map.fitBounds([
      [Math.min(...lats), Math.min(...lngs)],
      [Math.max(...lats), Math.max(...lngs)],
    ], { padding: [48, 48], maxZoom: 12 });
  }, [alerts, map]);
  return null;
}

const vehicleIcon = L.divIcon({
  className: '',
  html: '<div style="background:#2563eb;width:12px;height:12px;border-radius:50%;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.3)"></div>',
  iconSize: [12, 12],
  iconAnchor: [6, 6],
});

interface LiveMapProps {
  alerts: RoadAlert[];
  vehicles?: FleetDevice[];
  height?: string;
  selectedId?: string | null;
  onSelect?: (alert: RoadAlert) => void;
  zoom?: number;
}

export function LiveMap({ alerts, vehicles = [], height = '520px', selectedId, onSelect, zoom = DEFAULT_MAP_ZOOM }: LiveMapProps) {
  const center = alerts[0]
    ? [alerts[0].latitude, alerts[0].longitude] as [number, number]
    : DEFAULT_MAP_CENTER;
  const fleetVisible = useShowFleetOnMap();

  return (
    <div className="overflow-hidden rounded-xl border border-border shadow-inner" style={{ height }}>
      <MapContainer center={center} zoom={zoom} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="© OpenStreetMap · العراق"
        />
        {alerts.length > 1 && <FitBounds alerts={alerts} />}
        {alerts.map((a) => {
          const meta = EVENT_META[a.event_type];
          const selected = selectedId === a.id;
          const popup = alertPopupLines(a);
          return (
            <CircleMarker
              key={a.id}
              center={[a.latitude, a.longitude]}
              radius={selected ? 14 : 10}
              pathOptions={{
                color: meta.color,
                fillColor: meta.color,
                fillOpacity: selected ? 0.95 : 0.75,
                weight: selected ? 3 : 2,
              }}
              eventHandlers={{ click: () => onSelect?.(a) }}
            >
              <Popup>
                <strong>{popup.title}</strong><br />
                {popup.subtitle}
              </Popup>
            </CircleMarker>
          );
        })}
        {fleetVisible && vehicles.filter((v) => v.is_online && v.latitude != null && v.longitude != null).map((v) => (
          <Marker key={v.id} position={[v.latitude!, v.longitude!]} icon={vehicleIcon}>
            <Popup>{v.vehicle_id} · متصل</Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
