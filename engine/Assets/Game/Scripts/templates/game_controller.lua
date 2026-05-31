--[[
  VoxelForge — Game Controller Template
  ======================================
  Drop this on any entity to give it a complete top-down game loop:
    * WASD / arrow keys to move
    * Mouse scroll to zoom
    * E to pick up / interact with nearby objects
    * Space to jump (if entity has RigidBody with useGravity)
    * ESC to pause

  The controller reads the scene's entity list to find interactable
  objects (entities tagged "interactable" in their name).

  This script uses the Lua wrappers exposed by the engine:
    Transform, VoxelPhysics, RigidBody, UI
--]]

-- ─── Constants ──────────────────────────────────────────────────────────────
local MOVE_SPEED   = 12.0
local JUMP_FORCE   = 8.0
local ZOOM_SPEED   = 0.1
local INTERACT_DIST = 4.0
local GRAVITY      = -9.8

-- ─── State ──────────────────────────────────────────────────────────────────
local player      = nil   -- entity ID of the controlled character
local paused      = false
local score       = 0
local hud_msg     = ""
local hud_timer   = 0.0

-- ─── Helpers ────────────────────────────────────────────────────────────────

-- Print a timed HUD message
local function show_hud(msg, duration)
    hud_msg   = msg
    hud_timer = duration or 2.0
end

-- Distance between two entities
local function entity_dist(a, b)
    local pa = Transform.GetPosition(a)
    local pb = Transform.GetPosition(b)
    local dx, dy = pa.x - pb.x, pa.y - pb.y
    return math.sqrt(dx*dx + dy*dy)
end

-- Find entities whose name contains a substring
local function find_entities_named(substr)
    local result = {}
    for _, eid in ipairs(ECS.GetAllEntities()) do
        local name = ECS.GetEntityName(eid) or ""
        if name:find(substr) then
            table.insert(result, eid)
        end
    end
    return result
end

-- ─── Lifecycle ──────────────────────────────────────────────────────────────

function Start()
    -- This script's entity IS the player
    player = self

    -- Ensure physics is set up on the player
    if not RigidBody.HasRigidBody(player) then
        RigidBody.AddRigidBody(player)
    end
    RigidBody.SetMass(player, 1.0)
    RigidBody.SetUseGravity(player, true)
    RigidBody.SetIsStatic(player, false)

    show_hud("VoxelForge — Use WASD to move, E to interact", 4.0)
    print("[GameController] Started on entity " .. tostring(player))
end

-- ─── Main update loop ───────────────────────────────────────────────────────

function Update()
    if paused then
        if Input.GetKeyDown("Escape") then paused = false end
        return
    end

    local dt = Time.DeltaTime()

    -- Pause
    if Input.GetKeyDown("Escape") then
        paused = true
        return
    end

    -- ─── Movement ───────────────────────────────────────────────────────────
    local vel = RigidBody.GetVelocity(player)
    local dx, dy = 0, 0

    if Input.GetKey("W") or Input.GetKey("Up")    then dy =  MOVE_SPEED end
    if Input.GetKey("S") or Input.GetKey("Down")  then dy = -MOVE_SPEED end
    if Input.GetKey("A") or Input.GetKey("Left")  then dx = -MOVE_SPEED end
    if Input.GetKey("D") or Input.GetKey("Right") then dx =  MOVE_SPEED end

    RigidBody.SetVelocity(player, dx, dy, vel.z)

    -- ─── Jump ───────────────────────────────────────────────────────────────
    if Input.GetKeyDown("Space") then
        local pos = Transform.GetPosition(player)
        -- Simple ground check: if entity is close to Z=0 or any solid below
        if pos.z <= 1.0 then
            RigidBody.SetVelocity(player, dx, dy, JUMP_FORCE)
        end
    end

    -- ─── Camera follow ──────────────────────────────────────────────────────
    local pos = Transform.GetPosition(player)
    -- Isometric offset
    Camera.SetPosition(pos.x - 40, pos.y - 40, pos.z + 60)

    -- ─── Interaction ────────────────────────────────────────────────────────
    if Input.GetKeyDown("E") then
        local interactables = find_entities_named("chest")
        for _, eid in ipairs(interactables) do
            if entity_dist(player, eid) < INTERACT_DIST then
                score = score + 10
                ECS.DestroyEntity(eid)
                show_hud("Chest opened! Score: " .. score, 2.0)
                break
            end
        end
    end

    -- ─── HUD timer ──────────────────────────────────────────────────────────
    if hud_timer > 0 then
        hud_timer = hud_timer - dt
        UI.DrawText(hud_msg, 20, 20, 1, 1, 0, 1)
    end

    UI.DrawText("Score: " .. score, 20, Screen.Height - 40, 1, 1, 1, 1)

    if paused then
        UI.DrawText("PAUSED — Press ESC to resume",
                     Screen.Width/2 - 100, Screen.Height/2, 1, 1, 1, 1)
    end
end

function End()
    print("[GameController] Entity destroyed. Final score: " .. score)
end
