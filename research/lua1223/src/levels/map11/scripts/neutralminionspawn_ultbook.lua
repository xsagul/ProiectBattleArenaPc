local L0_1, L1_1
L0_1 = DoLuaShared
L1_1 = "SR_NeutralMinionSpawn"
L0_1(L1_1)

function L0_1()
  local L0_2, L1_2
  L0_2 = 34
  START_OF_GAME_ADDITIONAL_DELAY_CRAB = L0_2
  L0_2 = MINION_SPAWN_START_TIME
  L0_2 = 900 - L0_2
  BARON_SPAWN_TIME = L0_2
  L0_2 = MINION_SPAWN_START_TIME
  L0_2 = 360 - L0_2
  HERALD_SPAWN_TIME = L0_2
  L0_2 = MINION_SPAWN_START_TIME
  L0_2 = 210 - L0_2
  DRAGON_SPAWN_TIME = L0_2
  L0_2 = 270
  BARON_SPAWN_RATE = L0_2
  L0_2 = 210
  ELEMENTAL_DRAGON_SPAWN_RATE = L0_2
  L0_2 = 270
  HERALD_SPAWN_RATE = L0_2
end

OverrideNeutralMinionSpawnDefaults = L0_1

function L0_1()
  local L0_2, L1_2, L2_2
  L0_2 = NeutralMinionCamps
  L0_2 = L0_2[2]
  L1_2 = START_OF_GAME_MONSTER_SPAWN_DELAY
  L2_2 = CAMP_TIME_OFFSET
  L2_2 = L2_2 * 2
  L1_2 = L1_2 + L2_2
  L0_2.GroupDelaySpawnTime = L1_2
  L0_2 = NeutralMinionCamps
  L0_2 = L0_2[3]
  L1_2 = START_OF_GAME_MONSTER_SPAWN_DELAY
  L2_2 = CAMP_TIME_OFFSET
  L2_2 = L2_2 * 1
  L1_2 = L1_2 + L2_2
  L0_2.GroupDelaySpawnTime = L1_2
  L0_2 = NeutralMinionCamps
  L0_2 = L0_2[8]
  L1_2 = START_OF_GAME_MONSTER_SPAWN_DELAY
  L2_2 = CAMP_TIME_OFFSET
  L2_2 = L2_2 * 2
  L1_2 = L1_2 + L2_2
  L0_2.GroupDelaySpawnTime = L1_2
  L0_2 = NeutralMinionCamps
  L0_2 = L0_2[9]
  L1_2 = START_OF_GAME_MONSTER_SPAWN_DELAY
  L2_2 = CAMP_TIME_OFFSET
  L2_2 = L2_2 * 1
  L1_2 = L1_2 + L2_2
  L0_2.GroupDelaySpawnTime = L1_2
  L0_2 = NeutralMinionCamps
  L0_2 = L0_2[17]
  L0_2.StopSpawnTime = 885
end

NeutralMinionOverride = L0_1
L0_1 = NeutralMinionSpawnInit
L0_1()
