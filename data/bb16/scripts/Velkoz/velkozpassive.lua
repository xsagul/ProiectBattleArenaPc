-- velkozpassive: written by tools/bb_write16.py from the replays (6 instances, 6 games)
--   slot 52 = Perks_ArcaneComet_Mis_Idle while it lasts (1.00)
BuffName = "velkozpassive"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "Perks_ArcaneComet_Mis_Idle", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
