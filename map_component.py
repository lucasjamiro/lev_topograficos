import os
import streamlit.components.v1 as components

_RELEASE = True

if not _RELEASE:
    _maplibre_component = components.declare_component(
        "maplibre_component",
        url="http://localhost:3001",
    )
else:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "maplibre_component")
    _maplibre_component = components.declare_component(
        "maplibre_component",
        path=build_dir
    )

def maplibre_component(
    points,
    traverse_lines=None,
    radiation_lines=None,
    dash_traverse=True,
    locked=False,
    center=None,
    zoom=16,
    current_layer="streets",
    height=500,
    key=None
):
    """
    Renders MapLibre interactive map component.

    Parameters:
    - points: list of dicts with keys: label, lat, lon, color ('red'|'blue'|'green'), shape ('triangle'|'square'|'circle'), category ('survey'|'radiation'), index
    - traverse_lines: list of [lat, lon] tuples/lists
    - radiation_lines: list of dicts with keys: start: [lat, lon], end: [lat, lon]
    - dash_traverse: boolean
    - locked: boolean
    - center: [lat, lon]
    - zoom: int/float
    - current_layer: 'streets' | 'satellite' | 'vector'
    - height: int
    - key: str
    """
    if center is None:
        center = [-25.4484, -49.2310]

    return _maplibre_component(
        points=points,
        traverse_lines=traverse_lines or [],
        radiation_lines=radiation_lines or [],
        dash_traverse=dash_traverse,
        locked=locked,
        center=center,
        zoom=zoom,
        current_layer=current_layer,
        height=height,
        key=key,
        default=None
    )
