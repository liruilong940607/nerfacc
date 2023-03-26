"""
Copyright (c) 2022 Ruilong Li, UC Berkeley.
"""
from ._contraction import ContractionType, contract, contract_inv
from ._grid import Grid, OccupancyGrid, query_grid
from ._intersection import ray_aabb_intersect
from ._pack import pack_data, pack_info, unpack_data, unpack_info
from ._ray_marching import ray_marching
from .version import __version__
from ._vol_rendering import (
    accumulate_along_rays,
    render_transmittance_from_alpha,
    render_transmittance_from_density,
    render_visibility,
    render_weight_from_alpha,
    render_weight_from_density,
    rendering,
)

__all__ = [
    "__version__",
    # occ grid
    "Grid",
    "OccupancyGrid",
    "query_grid",
    "ContractionType",
    # contraction
    "contract",
    "contract_inv",
    # marching
    "ray_aabb_intersect",
    "_ray_marching",
    # rendering
    "accumulate_along_rays",
    "render_visibility",
    "render_weight_from_alpha",
    "render_weight_from_density",
    "render_transmittance_from_density",
    "render_transmittance_from_alpha",
    # "rendering",
    # pack
    "pack_data",
    "unpack_data",
    "unpack_info",
    "pack_info",
]
