"""Display the base layer, buildings and addresses from ~/Downloads/gis_hub.json on a map centered on them
(Voila / ipyleaflet).
Buildings (building_layer) and addresses are matched by address_id:
  · matched buildings are teal and clickable: a click turns the building yellow and shows
    "Added PV to address: …" with its building_type; a second click removes it again
  · buildings without a matching address are hatched purple and cannot be selected
The base layer is drawn as purple polygons underneath, addresses as small red circles (click: address under the map).
The shell is displayed immediately; the file is read and the map built once the browser is ready."""
import json
import math
from pathlib import Path

from IPython.core.display_functions import display
from ipyleaflet import Map, GeoJSON, basemaps
from ipywidgets import widgets, HTML
from ipystream.voila.utils_browser_ready import on_browser_ready

GIS_HUB_PATH = Path("~/Downloads/gis_hub.json").expanduser()
ADDRESS_ID = "address_id"              # key shared by building_layer feature properties and addresses
MAP_W_PX, MAP_H_PX = 900, 600          # width only feeds the first-guess zoom
FIT_PADDING = 0.92                     # keep a small margin around the features
HATCH_SPACING_M = 1.5                  # distance between hatch lines of unmatched buildings, metres
TEAL, RED, PURPLE, YELLOW = "#0f9d8f", "#d62728", "#7b3fbf", "#ffd400"
TEXT_STYLE = "font-family:sans-serif;font-size:13px"


def _id_key(v):
    """address_id as a comparable string: 12.0, "12" and 12 all give "12"."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    try:
        f = float(v)
        return str(int(f)) if f.is_integer() else str(v).strip()
    except (TypeError, ValueError):
        return str(v).strip()


def _as_features(layer):
    """A FeatureCollection, a single Feature or a bare geometry → list of Features with a drawable footprint."""
    if not layer:
        return []
    t = layer.get("type")
    feats = (layer.get("features") or [] if t == "FeatureCollection"
             else [layer] if t == "Feature"
    else [{"type": "Feature", "properties": {}, "geometry": layer}])
    return [f for f in feats if _points(f.get("geometry"))]


def _load(path):
    """(base, matched buildings, unmatched buildings, addresses) as FeatureCollections.
    A building is matched when an address has the same address_id; its feature then carries that address's
    text and building_type, and an index "_i" used to select it."""
    hub = json.loads(path.read_text())
    raw = hub.get("addresses") or []
    by_id = {}
    for a in raw:
        k = _id_key(a.get(ADDRESS_ID))
        if k is not None:
            by_id.setdefault(k, a)

    matched, unmatched = [], []
    for f in _as_features(hub.get("building_layer")):
        a = by_id.get(_id_key((f.get("properties") or {}).get(ADDRESS_ID)))
        if a is None:
            unmatched.append({"type": "Feature", "geometry": f["geometry"], "properties": {}})
            continue
        matched.append({"type": "Feature", "geometry": f["geometry"], "properties": {
            "_i": len(matched), ADDRESS_ID: a.get(ADDRESS_ID), "address": a.get("address") or "(no address)",
            "building_type": a.get("building_type")}})

    addresses = [{"type": "Feature", "properties": {"address": a.get("address") or "(no address)",
                                                    "building_ground_area": a.get("building_ground_area"),
                                                    "building_type": a.get("building_type")},
                  "geometry": {"type": "Point", "coordinates": [a["lon"], a["lat"]]}}
                 for a in raw if a.get("lon") is not None and a.get("lat") is not None]
    fc = lambda feats: {"type": "FeatureCollection", "features": feats}
    return fc(_as_features(hub.get("base_layer"))), fc(matched), fc(unmatched), fc(addresses)


def _points(geom):
    """Every [lon, lat] vertex of a Point / Polygon / MultiPolygon (other geometries are ignored)."""
    t, c = (geom or {}).get("type"), (geom or {}).get("coordinates") or []
    if t == "Point":
        return [c] if len(c) >= 2 else []
    rings = c if t == "Polygon" else [r for poly in c for r in poly] if t == "MultiPolygon" else []
    return [p for ring in rings for p in ring if p and len(p) >= 2]


def _hatch(features, spacing_m=HATCH_SPACING_M):
    """45° hatch segments [[lon, lat], [lon, lat]] clipped to the outer ring of each (Multi)Polygon."""
    lines = []
    for f in features:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"] if g["type"] == "MultiPolygon" else []
        for poly in polys:
            ring = [p[:2] for p in (poly[0] if poly else []) if p and len(p) >= 2]
            if len(ring) < 3:
                continue
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            kx, ky = 111_320 * math.cos(math.radians(ring[0][1])), 110_540
            pts = [(lon * kx, lat * ky) for lon, lat in ring]
            us = [x - y for x, y in pts]
            u = math.floor(min(us) / spacing_m) * spacing_m + spacing_m
            while u < max(us):                       # line x − y = u
                xs = []
                for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                    a1, a2 = x1 - y1 - u, x2 - y2 - u
                    if (a1 > 0) != (a2 > 0):
                        xs.append(x1 + a1 / (a1 - a2) * (x2 - x1))
                xs.sort()
                for xa, xb in zip(xs[::2], xs[1::2]):
                    lines.append([[xa / kx, (xa - u) / ky], [xb / kx, (xb - u) / ky]])
                u += spacing_m
    return lines


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


def _build_map(base, matched, unmatched, addresses):
    """Map + Center button + selection readout. Returns the widgets to show."""
    center, guess, span = _center_zoom(base["features"] + matched["features"] + unmatched["features"]
                                       + addresses["features"])
    view = {"zoom": guess}                 # the fitted zoom, shared with the Center button
    m = Map(center=center, zoom=guess, zoom_snap=0.25, zoom_delta=0.5, basemap=basemaps.OpenStreetMap.Mapnik,
            scroll_wheel_zoom=True, double_click_zoom=False,
            layout=widgets.Layout(width="100%", height=f"{MAP_H_PX}px"))

    # Base layer first so everything else is drawn (and clickable) on top of it.
    if base["features"]:
        m.add_layer(GeoJSON(data=base, style={"color": PURPLE, "weight": 2, "opacity": 0.9, "fillColor": PURPLE,
                                              "fillOpacity": 0.12}))

    # Buildings without an address match: purple outline + hatching, not clickable.
    if unmatched["features"]:
        m.add_layer(GeoJSON(data=unmatched, style={"color": PURPLE, "weight": 1.2, "opacity": 0.9,
                                                   "fillColor": PURPLE, "fillOpacity": 0.1}))
        m.add_layer(GeoJSON(data={"type": "Feature", "properties": {}, "geometry": {
            "type": "MultiLineString", "coordinates": _hatch(unmatched["features"])}},
                            style={"color": PURPLE, "weight": 1, "opacity": 0.9, "interactive": False}))

    # Matched buildings: teal and clickable; the selected ones are redrawn in yellow on top.
    buildings = GeoJSON(data=matched, style={"color": TEAL, "weight": 1.5, "opacity": 0.8, "fillColor": TEAL,
                                             "fillOpacity": 0.15}, hover_style={"fillOpacity": 0.4})
    chosen = GeoJSON(data={"type": "FeatureCollection", "features": []},
                     style={"color": "#b38f00", "weight": 2, "opacity": 1, "fillColor": YELLOW, "fillOpacity": 0.85},
                     hover_style={"fillOpacity": 1})
    m.add_layer(buildings)
    m.add_layer(chosen)

    selected = HTML(f"<div style='{TEXT_STYLE};color:#8a94a0;margin:8px 0 0'>Click a teal building to add PV "
                    f"(it turns yellow) · hatched purple buildings have no matching address.</div>")
    picked = set()                         # "_i" of the yellow buildings

    def _on_building_click(feature=None, properties=None, **_kw):
        props = properties or (feature or {}).get("properties") or {}
        i = props.get("_i")
        if i is None:
            return
        added = i not in picked
        (picked.add if added else picked.discard)(i)
        chosen.data = {"type": "FeatureCollection", "features": [f for f in matched["features"]
                                                                 if f["properties"]["_i"] in picked]}
        colour = "#8a6d00" if added else "#6b7280"
        selected.value = (f"<div style='{TEXT_STYLE};margin:8px 0 0'>"
                          f"<span style='color:{colour};font-weight:700'>"
                          f"{'Added PV to' if added else 'Removed PV from'} address:</span> "
                          f"<b>{props.get('address', '')}</b>"
                          f"<span style='color:#6b7280'>  ·  {props.get('building_type') or '–'}"
                          f"  ·  {ADDRESS_ID} {props.get(ADDRESS_ID)}  ·  {len(picked)} building(s) with PV</span></div>")

    buildings.on_click(_on_building_click)
    chosen.on_click(_on_building_click)

    # Addresses on top of the buildings so their circles stay clickable.
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
    btn_center = widgets.Button(description="Center map", icon="crosshairs", tooltip="Recenter on the map content",
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
            base, matched, unmatched, addresses = _load(GIS_HUB_PATH)
        except Exception as exc:
            header.value = (f"<b style='color:#b3312c'>⚠ Could not read {GIS_HUB_PATH}: "
                            f"{type(exc).__name__}: {exc}</b>")
            body.layout.min_height = None
            return
        body.children = _build_map(base, matched, unmatched, addresses)
        header.value = (f"<div style='{TEXT_STYLE};margin:0 0 6px'>{len(base['features'])} base polygon(s) · "
                        f"{len(matched['features'])} building(s) with a matching address · "
                        f"{len(unmatched['features'])} without (hatched) · "
                        f"{len(addresses['features'])} address(es) from <code>{GIS_HUB_PATH}</code></div>")

    on_browser_ready(_init_app)