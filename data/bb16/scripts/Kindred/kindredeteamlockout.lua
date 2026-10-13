-- kindredeteamlockout: written by tools/bb_write16.py from the replays (219 instances, 4 games)
--   given by the cast of KindredEWrapper (0.98)
--   slot 47 = KindredE while it lasts (0.98)
BuffName = "kindredeteamlockout"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 47, SlotType = ExtraSlots, SpellName = "KindredE", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
