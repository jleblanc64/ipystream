"""Display the buildings and addresses from ~/Downloads/gis_hub.json on a map centered on them (Voila / ipyleaflet).
Buildings are drawn as polygons, addresses as small red circles; clicking a circle shows its address under the map.
The shell is displayed immediately; the file is read and the map built once the browser is ready."""
import json
import math
from pathlib import Path

from IPython.core.display_functions import display
from ipyleaflet import Map, GeoJSON, basemaps
from ipywidgets import widgets, HTML
from ipystream.voila.utils_browser_ready import on_browser_ready

GIS_HUB_PATH = Path("~/Downloads/gis_hub.json").expanduser()
MAP_W_PX, MAP_H_PX = 900, 600          # width only feeds the first-guess zoom
FIT_PADDING = 0.92                     # keep a small margin around the buildings
TEAL, RED = "#0f9d8f", "#d62728"
TEXT_STYLE = "font-family:sans-serif;font-size:13px"


def _load(path):
    """(buildings, addresses) as two FeatureCollections. Buildings with an empty footprint are dropped;
    addresses become Point features carrying the address text."""
    hub = json.loads(path.read_text())
    buildings = [f for f in (hub.get("building_layer") or {}).get("features", []) if _points(f.get("geometry"))]
    addresses = [{"type": "Feature", "properties": {"address": a.get("address") or "(no address)",
                                                    "building_ground_area": a.get("building_ground_area"),
                                                    "building_type": a.get("building_type")},
                  "geometry": {"type": "Point", "coordinates": [a["lon"], a["lat"]]}}
                 for a in hub.get("addresses") or [] if a.get("lon") is not None and a.get("lat") is not None]
    return ({"type": "FeatureCollection", "features": buildings},
            {"type": "FeatureCollection", "features": addresses})


def _points(geom):
    """Every [lon, lat] vertex of a Point / Polygon / MultiPolygon (other geometries are ignored)."""
    t, c = (geom or {}).get("type"), (geom or {}).get("coordinates") or []
    if t == "Point":
        return [c] if len(c) >= 2 else []
    rings = c if t == "Polygon" else [r for poly in c for r in poly] if t == "MultiPolygon" else []
    return [p for ring in rings for p in ring if p and len(p) >= 2]


def _center_zoom(features):
    """Center, a first-guess zoom and the (lon, lat) span of the bounding box. The guess is
    refined by _fit_once as soon as the browser reports the map's real visible bounds."""
    pts = [p for f in features for p in _points(f.get("geometry"))]
    if not pts:
        return (46.8, 8.2), 8, None    # nothing drawable: show Switzerland
    lons, lats = [p[0] for p in pts], [p[1] for p in pts]
    lat_c, lon_c = (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2
    dlon, dlat = max(max(lons) - min(lons), 1e-6), max(max(lats) - min(lats), 1e-6)
    z_lon = math.log2(360 * MAP_W_PX / (256 * dlon))
    z_lat = math.log2(360 * MAP_H_PX * math.cos(math.radians(lat_c)) / (256 * dlat))
    return (lat_c, lon_c), max(1, min(19, min(z_lon, z_lat))), (dlon, dlat)


def _build_map(buildings, addresses):
    """Map + Center button + clicked-address readout. Returns the widgets to show."""
    center, guess, span = _center_zoom(buildings["features"] + addresses["features"])
    view = {"zoom": guess}                 # the fitted zoom, shared with the Center button
    m = Map(center=center, zoom=guess, zoom_snap=0.25, zoom_delta=0.5, basemap=basemaps.OpenStreetMap.Mapnik,
            scroll_wheel_zoom=True, layout=widgets.Layout(width="100%", height=f"{MAP_H_PX}px"))
    m.add_layer(GeoJSON(data=buildings, style={"color": TEAL, "weight": 1.5, "opacity": 0.8, "fillColor": TEAL,
                                               "fillOpacity": 0.08}, hover_style={"fillOpacity": 0.3}))

    # Addresses on top of the buildings so their circles stay clickable.
    selected = HTML(f"<div style='{TEXT_STYLE};color:#8a94a0;margin:8px 0 0'>Click a red circle to see its address.</div>")
    points = GeoJSON(data=addresses, point_style={"radius": 5, "color": RED, "weight": 1, "fillColor": RED,
                                                  "fillOpacity": 0.9}, hover_style={"radius": 7})

    def _on_address_click(feature=None, properties=None, **_kw):
        props = properties or (feature or {}).get("properties") or {}
        area, btype = props.get("building_ground_area"), props.get("building_type")
        area_txt = f"{float(area):,.0f} m²" if area is not None else "–"
        selected.value = (f"<div style='{TEXT_STYLE};margin:8px 0 0'>📍 <b>{props.get('address', '')}</b>"
                          f"<span style='color:#6b7280'>  ·  ground area {area_txt}  ·  {btype or '–'}</span></div>")

    points.on_click(_on_address_click)
    m.add_layer(points)

    def _fit_once(change):
        """First bounds report from the browser: the visible span at the current zoom tells exactly
        how much further in we can go (each zoom level halves the span). Snapped down to 0.25."""
        b = change["new"]
        if not span or not b or len(b) != 2:
            return
        m.unobserve(_fit_once, names="bounds")
        (s, w), (n, e) = b
        ratio = min(abs(e - w) / span[0], abs(n - s) / span[1]) * FIT_PADDING
        if ratio > 0:
            view["zoom"] = max(1, min(19, math.floor((m.zoom + math.log2(ratio)) * 4) / 4))
            m.center, m.zoom = center, view["zoom"]

    m.observe(_fit_once, names="bounds")
    btn_center = widgets.Button(description="Center map", icon="crosshairs", tooltip="Recenter on the buildings",
                                layout=widgets.Layout(width="130px", margin="8px 0 0 0"))

    def _recenter(_b=None):
        m.center, m.zoom = center, view["zoom"]

    btn_center.on_click(_recenter)
    return [m, selected, btn_center]


def run():
    # Phase 1: bare shell, displayed immediately.
    header = HTML(f"<div style='{TEXT_STYLE};margin:0 0 6px'>Loading <code>{GIS_HUB_PATH}</code>…</div>")
    body = widgets.VBox(layout=widgets.Layout(min_height=f"{MAP_H_PX}px"))
    display(header, body)

    def _init_app():
        # Phase 2, once the browser is ready: read the file and build the map.
        try:
            buildings, addresses = _load(GIS_HUB_PATH)
        except Exception as exc:
            header.value = (f"<b style='color:#b3312c'>⚠ Could not read {GIS_HUB_PATH}: "
                            f"{type(exc).__name__}: {exc}</b>")
            body.layout.min_height = None
            return
        body.children = _build_map(buildings, addresses)
        header.value = (f"<div style='{TEXT_STYLE};margin:0 0 6px'>{len(buildings['features'])} building(s) · "
                        f"{len(addresses['features'])} address(es) from <code>{GIS_HUB_PATH}</code></div>")

    on_browser_ready(_init_app)