import { useEffect, useMemo, useState } from "react";
import { Loader, MapPin } from "lucide-react";
import L from "leaflet";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import NavBarAuth from "../components/NavBarAuth";
import { apiGet } from "../lib/api";
import "./Map.css";

const ROLE_LABELS = {
  producer: "Productorx",
  consumer: "Consumidorx",
  both: "Ambxs",
};

const ROLE_COLORS = {
  producer: "var(--accent-primary, #3b7a3f)",
  consumer: "var(--accent-tertiary, #8ab870)",
  both: "var(--confidence-medium, #c8a85b)",
};

const ROLE_COLOR_FALLBACK = {
  producer: "#3b7a3f",
  consumer: "#8ab870",
  both: "#c8a85b",
};

const AR_CENTER = [-34, -64];
const AR_ZOOM = 5;
const ALL_ROLES = ["producer", "consumer", "both"];

function isValidCoord(n) {
  return typeof n === "number" && Number.isFinite(n);
}

function isValidLatLng(node) {
  return (
    isValidCoord(node.latitude) &&
    isValidCoord(node.longitude) &&
    node.latitude >= -90 &&
    node.latitude <= 90 &&
    node.longitude >= -180 &&
    node.longitude <= 180
  );
}

function makePinIcon(role) {
  const color = ROLE_COLOR_FALLBACK[role] || ROLE_COLOR_FALLBACK.both;
  return L.divIcon({
    className: "map-pin",
    html: `<span class="map-pin__dot" style="background:${color}"></span>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
    popupAnchor: [0, -8],
  });
}

function FitToBounds({ nodes }) {
  const map = useMap();
  useEffect(() => {
    if (nodes.length === 0) return;
    const bounds = L.latLngBounds(nodes.map((n) => [n.latitude, n.longitude]));
    map.fitBounds(bounds, { padding: [40, 40] });
  }, [nodes, map]);
  return null;
}

export default function MapPage() {
  const [state, setState] = useState({ status: "loading" });
  const [activeRoles, setActiveRoles] = useState(new Set(ALL_ROLES));

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await apiGet("/api/map");
        if (cancelled) return;
        if (!response.ok) {
          setState({ status: "error" });
          return;
        }
        const body = await response.json();
        setState({ status: "ready", body });
      } catch {
        if (!cancelled) setState({ status: "error" });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const validNodes = useMemo(() => {
    if (state.status !== "ready") return [];
    return state.body.nodes.filter((n) => {
      const ok = isValidLatLng(n);
      if (!ok) {
        console.warn("map: skipping node with invalid coordinates", n.id);
      }
      return ok;
    });
  }, [state]);

  const visibleNodes = useMemo(
    () => validNodes.filter((n) => activeRoles.has(n.role)),
    [validNodes, activeRoles],
  );

  function toggleRole(role) {
    setActiveRoles((prev) => {
      const next = new Set(prev);
      if (next.has(role)) next.delete(role);
      else next.add(role);
      return next;
    });
  }

  const producerCount = validNodes.filter(
    (n) => n.role === "producer" || n.role === "both",
  ).length;
  const consumerCount = validNodes.filter(
    (n) => n.role === "consumer" || n.role === "both",
  ).length;

  return (
    <div className="page-shell map-page">
      <NavBarAuth />
      <main className="map-page__content">
        <header className="map-page__header">
          <h1 className="map-page__title">Mapa de la red</h1>
          {state.status === "ready" && (
            <p className="map-page__subtitle">
              {producerCount} productorxs · {consumerCount} consumidorxs
            </p>
          )}
        </header>

        <div className="map-page__filters" role="group" aria-label="Filtros">
          {ALL_ROLES.map((role) => {
            const selected = activeRoles.has(role);
            return (
              <button
                key={role}
                type="button"
                aria-pressed={selected}
                onClick={() => toggleRole(role)}
                className={
                  selected
                    ? "map-page__filter map-page__filter--active"
                    : "map-page__filter"
                }
                style={
                  selected
                    ? {
                        borderColor: ROLE_COLORS[role],
                        color: ROLE_COLORS[role],
                      }
                    : undefined
                }
              >
                {ROLE_LABELS[role]}
              </button>
            );
          })}
        </div>

        {state.status === "loading" && (
          <div className="map-page__status" role="status">
            <Loader size={24} aria-hidden="true" />
            <span>Cargando mapa…</span>
          </div>
        )}

        {state.status === "error" && (
          <div
            className="map-page__status map-page__status--error"
            role="alert"
          >
            No pudimos cargar el mapa, intentá de nuevo.
          </div>
        )}

        {state.status === "ready" && validNodes.length === 0 && (
          <div className="map-page__empty" role="status">
            <MapPin size={48} aria-hidden="true" />
            <h2>Todavía no hay nodxs registradxs</h2>
            <p>Empezá agregando productorxs al colectivo desde Mis pedidos.</p>
          </div>
        )}

        {state.status === "ready" &&
          validNodes.length > 0 &&
          activeRoles.size === 0 && (
            <div className="map-page__status" role="status">
              Mostrá al menos un rol con los filtros de arriba.
            </div>
          )}

        {state.status === "ready" &&
          validNodes.length > 0 &&
          activeRoles.size > 0 && (
            <div className="map-page__map" data-testid="map-container">
              <MapContainer
                center={AR_CENTER}
                zoom={AR_ZOOM}
                scrollWheelZoom
                style={{ height: "100%", width: "100%" }}
              >
                <TileLayer
                  attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <FitToBounds nodes={visibleNodes} />
                {visibleNodes.map((node) => (
                  <Marker
                    key={node.id}
                    position={[node.latitude, node.longitude]}
                    icon={makePinIcon(node.role)}
                  >
                    <Popup>
                      <NodePopup node={node} />
                    </Popup>
                  </Marker>
                ))}
              </MapContainer>
            </div>
          )}
      </main>
    </div>
  );
}

function NodePopup({ node }) {
  return (
    <div className="map-popup">
      <h3 className="map-popup__name">{node.display_name}</h3>
      <span
        className="map-popup__role"
        style={{
          background: `${ROLE_COLOR_FALLBACK[node.role]}22`,
          color: ROLE_COLOR_FALLBACK[node.role],
        }}
      >
        {ROLE_LABELS[node.role]}
      </span>
      <p className="map-popup__stats">
        {node.orders_last_week} pedidos esta semana · {node.orders_total} total
      </p>
      {node.top_products && node.top_products.length > 0 && (
        <p className="map-popup__products">{node.top_products.join(" · ")}</p>
      )}
    </div>
  );
}
