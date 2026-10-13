-- briarwfrenzybuff: written by tools/bb_write16.py from the replays (231 instances, 3 games)
--   given by the cast of BriarW (0.80)
--   slot 1 = BriarWAttackSpell while it lasts (1.00)
BuffName = "briarwfrenzybuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "BriarWAttackSpell", TargetVar = "Owner"}}
}
