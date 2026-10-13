-- aphelioscrescendummanager: written by tools/bb_write16.py from the replays (217 instances, 6 games)
--   given by the cast of ApheliosW (0.88)
--   slot 0 = ApheliosCrescendumQ while it lasts (1.00)
BuffName = "aphelioscrescendummanager"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "ApheliosCrescendumQ", TargetVar = "Owner"}}
}
