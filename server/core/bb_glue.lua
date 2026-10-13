-- The bridge between Riot's BuildingBlocks scripts and our engine (core/bb.py).
--
-- A block is {Function = BBName, Params = {...}, SubBlocks = {...}} and runs as BBName(ctx, params, subblocks)
-- (Riot's ExecuteBuildingBlocks, in BuildingBlocksBase.lua). The blocks Riot wrote in Lua come with
-- BuildingBlocksBase; the engine's own blocks (BBApplyDamage, BBSpellBuffAdd ...) are made here from one generic
-- adapter: it reads the block's parameters the way every Riot block names them -
--     X            a value written in the block
--     XVar         the name of a variable holding it, in the table XVarTable (GetTable(ctx, XVarTable)) or the
--                  context itself
--     XByLevel     a value per level: XByLevel[ctx.Level]
-- and hands the engine (Python: Engine(name, values, names)) plain values; what the engine gives back is written
-- into the variables the block names for its results (key K -> the variable params[K .. 'Var'] in
-- params[K .. 'VarTable']); a block that runs its sub-blocks for each unit of a list (ForEachUnitInTargetArea ...)
-- returns __each = {units}: the sub-blocks run once per unit, with the unit in params.IteratorVar.

Glue_ScriptEnvs = {}

function Glue_LoadScript(name, code)
    local f, err = loadstring(code, name)
    if f == nil then
        return err
    end
    local env = setmetatable({}, {__index = _G})
    setfenv(f, env)
    local ok, e = pcall(f)
    if not ok then
        return e
    end
    Glue_ScriptEnvs[name] = env
    return nil
end

function Glue_ScriptHas(name, event)
    local env = Glue_ScriptEnvs[name]
    return env ~= nil and rawget(env, event) ~= nil
end

function Glue_ScriptGet(name, key)
    local env = Glue_ScriptEnvs[name]
    if env == nil then return nil end
    return rawget(env, key)
end

-- run one event of a script with a context (a table the engine made: Owner, Target, Caster, Attacker, Level,
-- InstanceVars, CharVars ...); returns the context (the script's results, e.g. ReturnValue)
function Glue_RunScriptEvent(name, event, ctx)
    local env = Glue_ScriptEnvs[name]
    if env == nil then return ctx end
    local blocks = rawget(env, event)
    if blocks == nil then return ctx end
    ExecuteBuildingBlocks(blocks, ctx)
    return ctx
end

local function resolve(ctx, params)
    local values, names = {}, {}
    for k, v in pairs(params) do
        if type(k) == 'string' then
            local base = string.match(k, '^(.-)VarTable$')
            if base == nil then
                base = string.match(k, '^(.-)Var$')
                if base ~= nil then
                    names[base] = v
                    local t = GetTable(ctx, params[k .. 'Table'], false)
                    if t ~= nil and v ~= nil and t[v] ~= nil then
                        values[base] = t[v]
                    end
                else
                    base = string.match(k, '^(.-)ByLevel$')
                    if base ~= nil then
                        if values[base] == nil and ctx.Level ~= nil and type(v) == 'table' then
                            values[base] = v[ctx.Level]
                        end
                    elseif values[k] == nil then
                        values[k] = v
                    end
                end
            end
        end
    end
    return values, names
end

function MakeEngineBlock(name)
    _G[name] = function(ctx, params, sub)
        local values, names = resolve(ctx, params or {})
        values.__spell = ctx.__script
        if params ~= nil and params.BuffVarsTable ~= nil then
            values.__buffvars = Glue_TableOf(ctx, params.BuffVarsTable)
        end
        local out = Engine(name, values, names)
        if out == nil then return end
        for k, v in pairs(out) do
            if k ~= '__each' and params[k .. 'Var'] ~= nil then
                local t = GetTable(ctx, params[k .. 'VarTable'], true)
                t[params[k .. 'Var']] = v
            end
        end
        if out.__each ~= nil and sub ~= nil then
            local it = params.IteratorVar
            for _, u in ipairs(out.__each) do
                if it ~= nil then ctx[it] = u end
                ExecuteBuildingBlocks(sub, ctx)
            end
        end
    end
end

-- the scripts' lasting variables live here, in Lua: a buff instance's InstanceVars, a unit's CharVars (keys are the
-- engine's ids); Glue_Run builds the context of one event around them
Glue_Instances, Glue_Chars = {}, {}

function Glue_Run(name, event, ctx, iid, cid, init)
    if iid ~= nil then
        if Glue_Instances[iid] == nil then
            Glue_Instances[iid] = {}
            if init ~= nil then
                for k, v in pairs(init) do Glue_Instances[iid][k] = v end
            end
        end
        ctx.InstanceVars = Glue_Instances[iid]
    else
        ctx.InstanceVars = ctx.InstanceVars or {}
    end
    if cid ~= nil then
        Glue_Chars[cid] = Glue_Chars[cid] or {}
        ctx.CharVars = Glue_Chars[cid]
    end
    ctx.NextBuffVars = {}
    ctx.__script = ctx.__script or name
    ctx.SpellVars = ctx.SpellVars or {}
    ctx.WorldVars = Glue_World or {}
    Glue_World = ctx.WorldVars
    Glue_RunScriptEvent(name, event, ctx)
    return ctx.ReturnValue
end

function Glue_Drop(iid)
    Glue_Instances[iid] = nil
end

-- the variables a block hands on to the buff it adds (BuffVarsTable = 'NextBuffVars'), as a plain table
function Glue_TableOf(ctx, name)
    local t = GetTable(ctx, name, false)
    local out = {}
    if t ~= nil then
        for k, v in pairs(t) do
            if type(v) ~= 'table' and type(v) ~= 'function' then out[k] = v end
        end
    end
    return out
end
