-- lucianpassivebuff: written by tools/bb_write16.py from the replays (872 instances, 4 games)
--   slot 54 = LucianPassiveAttack while it lasts (1.00)
BuffName = "lucianpassivebuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 54, SlotType = ExtraSlots, SpellName = "LucianPassiveAttack", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
