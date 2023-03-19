#pragma once

#include <torch/extension.h>

#include "data_spec.hpp"

namespace {
namespace device {

struct PackedRaySegmentsSpec {
    PackedRaySegmentsSpec(RaySegmentsSpec& spec) :
        edges(spec.edges.defined() ? spec.edges.data_ptr<float>() : nullptr),
        is_left(spec.is_left.defined() ? spec.is_left.data_ptr<bool>() : nullptr),
        is_right(spec.is_right.defined() ? spec.is_right.data_ptr<bool>() : nullptr),
        chunk_starts(spec.chunk_starts.defined() ? spec.chunk_starts.data_ptr<int64_t>() : nullptr),
        chunk_cnts(spec.chunk_cnts.data_ptr<int64_t>()),
        ray_ids(spec.ray_ids.defined() ? spec.ray_ids.data_ptr<int64_t>() : nullptr),
        n_edges(spec.edges.defined() ? spec.edges.numel() : 0),
        n_rays(spec.chunk_cnts.size(0))
    { }

    float* edges;
    bool* is_left;
    bool* is_right;
    int64_t* chunk_starts;
    int64_t* chunk_cnts;  // should always be defined
    int64_t* ray_ids;   // TODO: uint32_t should be enough

    int64_t n_edges;
    int64_t n_rays;
};

struct PackedMultiScaleGridSpec {
    PackedMultiScaleGridSpec(MultiScaleGridSpec& spec) :
        data(spec.data.data_ptr<float>()),
        binary(spec.binary.data_ptr<bool>()),
        base_aabb(spec.base_aabb.data_ptr<float>()),
        levels(spec.data.size(0)),
        resolution{
            (int)spec.data.size(1), 
            (int)spec.data.size(2), 
            (int)spec.data.size(3)} 
    { }
    float* data;
    bool* binary;
    float* base_aabb;
    int levels;
    int3 resolution;
};

struct PackedRaysSpec {
    PackedRaysSpec(RaysSpec& spec) :
        origins(spec.origins.data_ptr<float>()),
        dirs(spec.dirs.data_ptr<float>()),
        N(spec.origins.size(0))
    { }
    const float *origins;
    const float *dirs;
    const int64_t N;
};

struct SingleRaySpec {
    __device__ SingleRaySpec(
        PackedRaysSpec& rays, int64_t id, float tmin, float tmax) :
        origin{
            rays.origins[id * 3], 
            rays.origins[id * 3 + 1], 
            rays.origins[id * 3 + 2]},
        dir{
            rays.dirs[id * 3], 
            rays.dirs[id * 3 + 1], 
            rays.dirs[id * 3 + 2]},
        inv_dir{
            1.0f / rays.dirs[id * 3], 
            1.0f / rays.dirs[id * 3 + 1], 
            1.0f / rays.dirs[id * 3 + 2]},
        tmin{tmin},
        tmax{tmax}
    { }
    float3 origin;
    float3 dir;
    float3 inv_dir;
    float tmin;
    float tmax;
};

struct AABBSpec {
    __device__ AABBSpec(float *aabb) :
        min{aabb[0], aabb[1], aabb[2]},
        max{aabb[3], aabb[4], aabb[5]}
    { }
    __device__ AABBSpec(float3 min, float3 max) :
        min{min.x, min.y, min.z},
        max{max.x, max.y, max.z}
    { }
    float3 min;
    float3 max;
};


}  // namespace device
}  // namespace