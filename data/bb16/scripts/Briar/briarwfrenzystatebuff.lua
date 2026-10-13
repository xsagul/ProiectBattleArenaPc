-- briarwfrenzystatebuff: written by tools/bb_write16.py from the replays (232 instances, 3 games)
--   given by the cast of BriarW (0.80)
--   slot 1 = BriarWAttackSpell while it lasts (1.00)
BuffName = "briarwfrenzystatebuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "BriarWAttackSpell", TargetVar = "Owner"}}
}
