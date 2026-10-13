-- lissandrarenemy: written by tools/bb_write16.py from the replays (35 instances, 4 games)
--   given by the cast of LissandraR (0.94)
--   slot 48 = LissandraREnemy while it lasts (1.00)
BuffName = "lissandrarenemy"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 48, SlotType = ExtraSlots, SpellName = "LissandraREnemy", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
