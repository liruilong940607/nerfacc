from typing import Callable, List, Optional, Tuple, Union

import torch
from torch import Tensor

from ..grid import traverse_grids
from ..rendering import (
    render_visibility_from_alpha,
    render_visibility_from_density,
)
from .base import AbstractTransEstimator


class OccupancyGrid(AbstractTransEstimator):
    """Occupancy grid transmittance estimator."""

    DIM: int = 3

    def __init__(
        self,
        roi_aabb: Union[List[int], Tensor],
        resolution: Union[int, List[int], Tensor] = 128,
        levels: int = 1,
        **kwargs,
    ) -> None:
        super().__init__()

        if "contraction_type" in kwargs:
            raise ValueError(
                "`contraction_type` is not supported anymore for nerfacc >= 0.4.0."
            )

        # check the resolution is legal
        if isinstance(resolution, int):
            resolution = [resolution] * self.DIM
        if isinstance(resolution, (list, tuple)):
            resolution = torch.tensor(resolution, dtype=torch.int32)
        assert isinstance(resolution, Tensor), f"Invalid type: {resolution}!"
        assert resolution.shape[0] == self.DIM, f"Invalid shape: {resolution}!"

        # check the roi_aabb is legal
        if isinstance(roi_aabb, (list, tuple)):
            roi_aabb = Tensor(roi_aabb, dtype=torch.float32)
        assert isinstance(roi_aabb, Tensor), f"Invalid type: {roi_aabb}!"
        assert roi_aabb.shape[0] == self.DIM * 2, f"Invalid shape: {roi_aabb}!"

        # multiple levels of aabbs
        aabbs = torch.stack(
            [_enlarge_aabb(roi_aabb, 2**i) for i in range(levels)], dim=0
        )

        # total number of voxels
        self.cells_per_lvl = int(resolution.prod().item())
        self.levels = levels

        # Buffers
        self.register_buffer("resolution", resolution)  # [3]
        self.register_buffer("aabbs", aabbs)  # [n_aabbs, 6]
        self.register_buffer(
            "occs", torch.zeros(self.levels * self.cells_per_lvl)
        )
        self.register_buffer(
            "binaries",
            torch.zeros([levels] + resolution.tolist(), dtype=torch.bool),
        )

        # Grid coords & indices
        grid_coords = _meshgrid3d(resolution).reshape(
            self.cells_per_lvl, self.DIM
        )
        self.register_buffer("grid_coords", grid_coords, persistent=False)
        grid_indices = torch.arange(self.cells_per_lvl)
        self.register_buffer("grid_indices", grid_indices, persistent=False)

    @torch.no_grad()
    def sampling(
        self,
        # rays
        rays_o: Tensor,  # [n_rays, 3]
        rays_d: Tensor,  # [n_rays, 3]
        # sigma/alpha function for skipping invisible space
        sigma_fn: Optional[Callable] = None,
        alpha_fn: Optional[Callable] = None,
        near_plane: Optional[float] = None,
        far_plane: Optional[float] = None,
        # rendering options
        render_step_size: float = 1e-3,
        early_stop_eps: float = 1e-4,
        alpha_thre: float = 0.0,
        stratified: bool = False,
        cone_angle: float = 0.0,
    ) -> Tuple[Tensor, Tensor, Tensor]:
        if stratified:
            near_plane += torch.rand(()).item() * render_step_size
        intervals, samples = traverse_grids(
            rays_o,
            rays_d,
            self.binaries,
            self.aabbs,
            near_plane,
            far_plane,
            render_step_size,
            cone_angle,
        )
        t_starts = intervals.edges[intervals.is_left]
        t_ends = intervals.edges[intervals.is_right]
        ray_indices = samples.ray_ids

        # skip invisible space
        if (alpha_thre > 0.0 or early_stop_eps > 0.0) and (
            sigma_fn is not None or alpha_fn is not None
        ):
            alpha_thre = min(alpha_thre, self.occs.mean().item())

            # Compute visibility of the samples, and filter out invisible samples
            if sigma_fn is not None:
                sigmas = sigma_fn(t_starts, t_ends, ray_indices)
                assert (
                    sigmas.shape == t_starts.shape
                ), "sigmas must have shape of (N,)! Got {}".format(sigmas.shape)
                masks = render_visibility_from_density(
                    t_starts=t_starts,
                    t_ends=t_ends,
                    sigmas=sigmas,
                    chunk_starts=samples.chunk_starts,
                    chunk_cnts=samples.chunk_cnts,
                    early_stop_eps=early_stop_eps,
                    alpha_thre=alpha_thre,
                )
            elif alpha_fn is not None:
                alphas = alpha_fn(t_starts, t_ends, ray_indices)
                assert (
                    alphas.shape == t_starts.shape
                ), "alphas must have shape of (N,)! Got {}".format(alphas.shape)
                masks = render_visibility_from_alpha(
                    alphas=alphas,
                    chunk_starts=samples.chunk_starts,
                    chunk_cnts=samples.chunk_cnts,
                    early_stop_eps=early_stop_eps,
                    alpha_thre=alpha_thre,
                )
            ray_indices, t_starts, t_ends = (
                ray_indices[masks],
                t_starts[masks],
                t_ends[masks],
            )
        return ray_indices, t_starts, t_ends

    @torch.no_grad()
    def update_every_n_steps(
        self,
        step: int,
        occ_eval_fn: Callable,
        occ_thre: float = 1e-2,
        ema_decay: float = 0.95,
        warmup_steps: int = 256,
        n: int = 16,
    ) -> None:
        """Update the grid every n steps during training.

        Args:
            step: Current training step.
            occ_eval_fn: A function that takes in sample locations :math:`(N, 3)` and
                returns the occupancy values :math:`(N, 1)` at those locations.
            occ_thre: Threshold used to binarize the occupancy grid. Default: 1e-2.
            ema_decay: The decay rate for EMA updates. Default: 0.95.
            warmup_steps: Sample all cells during the warmup stage. After the warmup
                stage we change the sampling strategy to 1/4 uniformly sampled cells
                together with 1/4 occupied cells. Default: 256.
            n: Update the grid every n steps. Default: 16.
        """
        if not self.training:
            raise RuntimeError(
                "You should only call this function only during training. "
                "Please call _update() directly if you want to update the "
                "field during inference."
            )
        if step % n == 0 and self.training:
            self._update(
                step=step,
                occ_eval_fn=occ_eval_fn,
                occ_thre=occ_thre,
                ema_decay=ema_decay,
                warmup_steps=warmup_steps,
            )

    @torch.no_grad()
    def _get_all_cells(self) -> List[Tensor]:
        """Returns all cells of the grid."""
        return [self.grid_indices] * self.levels

    @torch.no_grad()
    def _sample_uniform_and_occupied_cells(self, n: int) -> List[Tensor]:
        """Samples both n uniform and occupied cells."""
        lvl_indices = []
        for lvl in range(self.levels):
            uniform_indices = torch.randint(
                self.cells_per_lvl, (n,), device=self.device
            )
            occupied_indices = torch.nonzero(self.binaries[lvl].flatten())[:, 0]
            if n < len(occupied_indices):
                selector = torch.randint(
                    len(occupied_indices), (n,), device=self.device
                )
                occupied_indices = occupied_indices[selector]
            indices = torch.cat([uniform_indices, occupied_indices], dim=0)
            lvl_indices.append(indices)
        return lvl_indices

    @torch.no_grad()
    def _update(
        self,
        step: int,
        occ_eval_fn: Callable,
        occ_thre: float = 0.01,
        ema_decay: float = 0.95,
        warmup_steps: int = 256,
    ) -> None:
        """Update the occ field in the EMA way."""
        # sample cells
        if step < warmup_steps:
            lvl_indices = self._get_all_cells()
        else:
            N = self.cells_per_lvl // 4
            lvl_indices = self._sample_uniform_and_occupied_cells(N)

        for lvl, indices in enumerate(lvl_indices):
            # infer occupancy: density * step_size
            grid_coords = self.grid_coords[indices]
            x = (
                grid_coords + torch.rand_like(grid_coords, dtype=torch.float32)
            ) / self.resolution
            # voxel coordinates [0, 1]^3 -> world
            x = self.aabbs[lvl, :3] + x * (
                self.aabbs[lvl, 3:] - self.aabbs[lvl, :3]
            )
            occ = occ_eval_fn(x).squeeze(-1)
            # ema update
            cell_ids = lvl * self.cells_per_lvl + indices
            self.occs[cell_ids] = torch.maximum(
                self.occs[cell_ids] * ema_decay, occ
            )
            # suppose to use scatter max but emperically it is almost the same.
            # self.occs, _ = scatter_max(
            #     occ, indices, dim=0, out=self.occs * ema_decay
            # )
        self.binaries = (
            self.occs > torch.clamp(self.occs.mean(), max=occ_thre)
        ).view(self.binaries.shape)


def _meshgrid3d(
    res: Tensor, device: Union[torch.device, str] = "cpu"
) -> Tensor:
    """Create 3D grid coordinates."""
    assert len(res) == 3
    res = res.tolist()
    return torch.stack(
        torch.meshgrid(
            [
                torch.arange(res[0], dtype=torch.long),
                torch.arange(res[1], dtype=torch.long),
                torch.arange(res[2], dtype=torch.long),
            ],
            indexing="ij",
        ),
        dim=-1,
    ).to(device)


def _enlarge_aabb(aabb, factor: float) -> Tensor:
    center = (aabb[:3] + aabb[3:]) / 2
    extent = (aabb[3:] - aabb[:3]) / 2
    return torch.cat([center - extent * factor, center + extent * factor])
