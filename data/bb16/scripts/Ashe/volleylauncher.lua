-- volleylauncher: written by tools/bb_write16.py from the replays (36 instances, 6 games)
--   slot 1 = Volley while it lasts (1.00)
BuffName = "volleylauncher"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "Volley", TargetVar = "Owner"}}
}
