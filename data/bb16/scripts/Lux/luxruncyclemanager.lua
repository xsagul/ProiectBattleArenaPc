-- luxruncyclemanager: written by tools/bb_write16.py from the replays (10 instances, 10 games)
--   slot 52 = Perks_ArcaneComet_Mis_Idle while it lasts (0.90)
BuffName = "luxruncyclemanager"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "Perks_ArcaneComet_Mis_Idle", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
