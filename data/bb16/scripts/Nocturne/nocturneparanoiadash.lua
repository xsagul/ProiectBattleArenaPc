-- nocturneparanoiadash: written by tools/bb_write16.py from the replays (29 instances, 3 games)
--   slot 3 =  while it lasts (1.00)
--   slot 3 = NocturneParanoia while it lasts (1.00)
--   spent by the holder's hit (1.00)
--   its hit is nocturneparanoia2 (0.45)
BuffName = "nocturneparanoiadash"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "\u0005", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "NocturneParanoia", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "nocturneparanoia2", OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
