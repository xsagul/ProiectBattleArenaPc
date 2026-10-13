local L0_1, L1_1, L2_1, L3_1
L0_1 = "3065_Spirit_Visage.dds"
BuffTextureName = L0_1
L0_1 = "Spirit Visage"
BuffName = L0_1
L0_1 = {}
L1_1 = {}
L2_1 = BBIncStat
L1_1.Function = L2_1
L2_1 = {}
L3_1 = IncPercentCooldownMod
L2_1.Stat = L3_1
L2_1.TargetVar = "Owner"
L2_1.Delta = -0.1
L1_1.Params = L2_1
L0_1[1] = L1_1
BuffOnUpdateStatsBuildingBlocks = L0_1
