--[[
  VoxelForge — World Populator Template
  ======================================
  Attach this script to any entity in a scene.  On Start() it reads
  the VoxelForge API (via a socket / HTTP) and can spawn new entities
  at runtime.

  In headless / offline mode it reads scene data from the ECS directly
  and prints a manifest so the generator can build the next frame.

  Usage (attach to an empty entity in the scene):
    Entity → Add Component → LuaScript
    Script Path: Assets/Game/Scripts/templates
    Script Name: world_populator.lua
--]]

-- ─── Config (edit before running) ──────────────────────────────────────────
local WORLD_SEED  = 42
local BIOME       = "grassland"   -- grassland | desert | snow | ocean | forest
local GRID_W      = 4             -- how many building slots in X
local GRID_H      = 4             -- how many building slots in Y
local SLOT_SIZE   = 12            -- voxels between building origins

-- ─── State ──────────────────────────────────────────────────────────────────
local entities_spawned = 0

-- ─── Helpers ────────────────────────────────────────────────────────────────

local function spawn_prefab(name, path, x, y, z)
    local eid = ECS.SpawnPrefab(path, name)
    if eid and eid >= 0 then
        Transform.SetPosition(eid, x, y, z)
        entities_spawned = entities_spawned + 1
    else
        print("[Populator] Failed to spawn prefab: " .. path)
    end
    return eid
end

-- ─── Lifecycle ──────────────────────────────────────────────────────────────

function Start()
    print("[Populator] World seed=" .. WORLD_SEED .. " biome=" .. BIOME)
    print("[Populator] Spawning " .. (GRID_W * GRID_H) .. " building slots …")

    -- Simple deterministic procedural placement using the seed
    math.randomseed(WORLD_SEED)

    for gx = 0, GRID_W - 1 do
        for gy = 0, GRID_H - 1 do
            local x = gx * SLOT_SIZE
            local y = gy * SLOT_SIZE
            local z = 14    -- surface height (matches terrain max_depth)

            -- 50% chance a building is present in this slot
            if math.random() > 0.5 then
                local prefab_path = "Assets/Game/Prefabs"
                local prefab_name = "newPrefab"
                spawn_prefab("building_" .. gx .. "_" .. gy,
                             prefab_path .. "/" .. prefab_name .. ".prefab",
                             x, y, z)
            end
        end
    end

    print("[Populator] Spawned " .. entities_spawned .. " entities")
end

function Update()
    -- Nothing to do each frame; population is one-shot on start.
end

function End()
    print("[Populator] World populator shutting down.")
end
