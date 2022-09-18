import torch
import tqdm

from nerfacc import volumetric_rendering_pipeline

device = "cuda:0"


def sigma_fn(frustum_starts, frustum_ends, ray_indices):
    return torch.rand_like(frustum_ends[:, :1])


def rgb_sigma_fn(frustum_starts, frustum_ends, ray_indices):
    return torch.rand((frustum_ends.shape[0], 3), device=device), torch.rand_like(
        frustum_ends
    )


def test_rendering():
    scene_aabb = torch.tensor([0, 0, 0, 1, 1, 1], device=device).float()
    scene_resolution = [128, 128, 128]
    scene_occ_binary = torch.ones((128 * 128 * 128), device=device).bool()
    rays_o = torch.rand((10000, 3), device=device)
    rays_d = torch.randn((10000, 3), device=device)
    rays_d = rays_d / rays_d.norm(dim=-1, keepdim=True)
    render_bkgd = torch.ones(3, device=device)

    for step in tqdm.tqdm(range(1000)):
        volumetric_rendering_pipeline(
            sigma_fn,
            rgb_sigma_fn,
            rays_o,
            rays_d,
            scene_aabb,
            scene_resolution,
            scene_occ_binary,
            render_bkgd,
            render_step_size=1e-3,
            near_plane=0.0,
            stratified=False,
        )


if __name__ == "__main__":
    test_rendering()
