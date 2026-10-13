local L0_1, L1_1, L2_1, L3_1
L0_1 = {}
L1_1 = {}
L2_1 = BBApplyDamage
L1_1.Function = L2_1
L2_1 = {}
L2_1.AttackerVar = "Owner"
L2_1.TargetVar = "Owner"
L2_1.Damage = 1000
L3_1 = TRUE_DAMAGE
L2_1.DamageType = L3_1
L3_1 = DAMAGESOURCE_INTERNALRAW
L2_1.SourceDamageType = L3_1
L2_1.PercentOfAttack = 1
L2_1.SpellDamageRatio = 1
L1_1.Params = L2_1
L0_1[1] = L1_1
OnBuffDeactivateBuildingBlocks = L0_1
