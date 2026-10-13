-- nunuesnowballfightbuff: written by tools/bb_write16.py from the replays (244 instances, 4 games)
--   slot 2 = NunuESnowballBurstFire while it lasts (1.00)
BuffName = "nunuesnowballfightbuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "NunuESnowballBurstFire", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "NunuE", TargetVar = "Owner"}}
}
