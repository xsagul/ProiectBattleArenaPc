-- ornnpitembuy: written by tools/bb_write16.py from the replays (46 instances, 5 games)
--   slot 52 = OrnnPAllyItemGive while it lasts (1.00)
BuffName = "ornnpitembuy"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "OrnnPAllyItemGive", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
