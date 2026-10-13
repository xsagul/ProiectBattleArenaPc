-- rakanerecast: written by tools/bb_write16.py from the replays (247 instances, 8 games)
--   slot 2 = RakanEReCast while it lasts (1.00)
BuffName = "rakanerecast"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "RakanEReCast", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "RakanE", TargetVar = "Owner"}}
}
