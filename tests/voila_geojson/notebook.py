"""Display the building polygons from ~/Downloads/geoadmin.geojson on a map centered on them (Voila / ipyleaflet)."""
import json
import math
from pathlib import Path

from IPython.core.display_functions import display
from ipyleaflet import Map, GeoJSON, basemaps
from ipywidgets import widgets, HTML

GEOJSON_PATH = Path("~/Downloads/geoadmin.geojson").expanduser()
MAP_W_PX, MAP_H_PX = 900, 600          # width only feeds the first-guess zoom
FIT_PADDING = 0.92                     # keep a small margin around the buildings
TEAL = "#0f9d8f"


def _load(path):
    """Return the file as a FeatureCollection, whatever GeoJSON shape it has."""
    data = json.loads(path.read_text())
    if data.get("type") == "FeatureCollection":
        return data
    if data.get("type") == "Feature":
        return {"type": "FeatureCollection", "features": [data]}
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": data}]}


def _points(geom):
    """Every [lon, lat] vertex of a Polygon / MultiPolygon (other geometries are ignored)."""
    t, c = (geom or {}).get("type"), (geom or {}).get("coordinates") or []
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


def run():
    try:
        fc = _load(GEOJSON_PATH)
    except Exception as exc:
        return display(HTML(f"<b style='color:#b3312c'>⚠ Could not read {GEOJSON_PATH}: {type(exc).__name__}: {exc}</b>"))

    center, guess, span = _center_zoom(fc["features"])
    view = {"zoom": guess}                 # the fitted zoom, shared with the Center button
    m = Map(center=center, zoom=guess, zoom_snap=0.25, zoom_delta=0.5, basemap=basemaps.OpenStreetMap.Mapnik,
            scroll_wheel_zoom=True, layout=widgets.Layout(width="100%", height=f"{MAP_H_PX}px"))
    m.add_layer(GeoJSON(data=fc, style={"color": TEAL, "weight": 1.5, "opacity": 0.8, "fillColor": TEAL, "fillOpacity": 0.08},
                        hover_style={"fillOpacity": 0.3}))

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
    btn_center = widgets.Button(description="Center map", icon="crosshairs", tooltip="Recenter on the polygons",
                                layout=widgets.Layout(width="130px", margin="8px 0 0 0"))

    def _recenter(_b=None):
        m.center, m.zoom = center, view["zoom"]

    btn_center.on_click(_recenter)
    display(HTML(f"<div style='font-family:sans-serif;font-size:13px;margin:0 0 6px'>"
                 f"{len(fc['features'])} feature(s) from <code>{GEOJSON_PATH}</code></div>"), m, btn_center)