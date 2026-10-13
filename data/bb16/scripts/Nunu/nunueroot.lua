-- nunueroot: written by tools/bb_write16.py from the replays (106 instances, 4 games)
--   given when nunuesnowballfightbuff is spent (1.00)
--   slot 2 = NunuE while it lasts (1.00)
BuffName = "nunueroot"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "NunuE", TargetVar = "Owner"}}
}
