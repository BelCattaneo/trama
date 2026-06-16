import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Loader, Map as MapIcon } from "lucide-react";
import L from "leaflet";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import NavBarAuth from "../components/NavBarAuth";
import { useAuth } from "../contexts/AuthContext";
import { apiGet } from "../lib/api";
import "./Map.css";

const ROLE_LABELS = {
  producer: "Productorx",
  consumer: "Consumidorx",
  both: "Ambxs",
};

const ROLE_COLORS = {
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

function makePinIcon(role, isMe) {
  const color = ROLE_COLORS[role] ?? ROLE_COLORS.both;
  const html = isMe
    ? `<span class="map-pin__dot" style="background:${color}"></span><span class="map-pin__label">tu nodo</span>`
    : `<span class="map-pin__dot" style="background:${color}"></span>`;
  return L.divIcon({
    className: isMe ? "map-pin map-pin--me" : "map-pin",
    html,
    iconSize: isMe ? [60, 36] : [18, 18],
    iconAnchor: isMe ? [30, 9] : [9, 9],
    popupAnchor: [0, -8],
  });
}

function InvalidateOnMount() {
  const map = useMap();
  useEffect(() => {
    const t = setTimeout(() => map.invalidateSize(), 50);
    return () => clearTimeout(t);
  }, [map]);
  return null;
}

export default function MapPage() {
  const { user } = useAuth();
  const myNodeId = user?.node?.id ?? null;
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
    () =>
      validNodes.filter((n) => n.id === myNodeId || activeRoles.has(n.role)),
    [validNodes, activeRoles, myNodeId],
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
          <div className="map-page__header-left">
            <h1 className="map-page__title">Mapa de la red</h1>
            {state.status === "ready" && (
              <p className="map-page__subtitle">
                {producerCount} productorxs · {consumerCount} consumidorxs
              </p>
            )}
          </div>
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
                >
                  {ROLE_LABELS[role]}
                </button>
              );
            })}
          </div>
        </header>

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
            <div className="map-page__empty-icon-circle" aria-hidden="true">
              <MapIcon size={28} />
            </div>
            <h2 className="map-page__empty-title">
              Todavía no hay productorxs ni consumidorxs
            </h2>
            <p className="map-page__empty-desc">
              Cuando registres productorxs y consumidorxs van a aparecer acá en
              el mapa.
            </p>
            <Link to="/upload" className="map-page__empty-cta">
              Registrar primer productor
            </Link>
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
              <aside className="map-page__legend" aria-label="Leyenda">
                {ALL_ROLES.map((role) => (
                  <div key={role} className="map-page__legend-item">
                    <span
                      className="map-page__legend-dot"
                      style={{ background: ROLE_COLORS[role] }}
                      aria-hidden="true"
                    />
                    <span>{ROLE_LABELS[role]}</span>
                  </div>
                ))}
              </aside>
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
                <InvalidateOnMount />
                {visibleNodes.map((node) => (
                  <Marker
                    key={node.id}
                    position={[node.latitude, node.longitude]}
                    icon={makePinIcon(node.role, node.id === myNodeId)}
                  >
                    <Popup>
                      <NodePopup node={node} isMe={node.id === myNodeId} />
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

function NodePopup({ node, isMe }) {
  return (
    <div className="map-popup">
      <h3 className="map-popup__name">
        {node.display_name}
        {isMe && <span className="map-popup__me-tag"> · vos</span>}
      </h3>
      <span
        className="map-popup__role"
        style={{
          background: `${ROLE_COLORS[node.role]}22`,
          color: ROLE_COLORS[node.role],
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
