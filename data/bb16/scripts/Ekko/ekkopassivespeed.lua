-- ekkopassivespeed: written by tools/bb_write16.py from the replays (369 instances, 18 games)
--   slot 45 = EkkoPassiveSpeed while it lasts (1.00)
BuffName = "ekkopassivespeed"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "EkkoPassiveSpeed", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
