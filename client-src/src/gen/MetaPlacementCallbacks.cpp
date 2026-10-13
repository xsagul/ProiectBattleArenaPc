// match: 26f0c0 ??$MetaConstruct@UClass_bafabcc8@@@@YAXPAX@Z
// match: 2d0b90 ??$MetaConstruct@UCollectiblesEsportsTeamData@@@@YAXPAX@Z
// match: 2d09e0 ??$MetaConstruct@UGDSMapObjectBannerInfo@@@@YAXPAX@Z
// match: 2d0a90 ??$MetaConstruct@UHasReceivedAnimEmoteEventBoolDriver@@@@YAXPAX@Z
// match: 2d0ae0 ??$MetaConstruct@UIsLocalPlayerBoolDriver@@@@YAXPAX@Z
// match: 2d0b30 ??$MetaConstruct@UIsMovingBoolDriver@@@@YAXPAX@Z
// match: 2d0c40 ??$MetaConstruct@USummonerIconData@@@@YAXPAX@Z
// match: 2d0d00 ??$MetaVirtual2@USummonerIconData@@@@YAXPAX@Z
#include "BinClasses.h"
template<> void MetaConstruct<Class_bafabcc8>(void* p) { new (p) Class_bafabcc8; }
template<> void MetaConstruct<CollectiblesEsportsTeamData>(void* p) { new (p) CollectiblesEsportsTeamData; }
template<> void MetaConstruct<GDSMapObjectBannerInfo>(void* p) { new (p) GDSMapObjectBannerInfo; }
template<> void MetaConstruct<HasReceivedAnimEmoteEventBoolDriver>(void* p) { new (p) HasReceivedAnimEmoteEventBoolDriver; }
template<> void MetaConstruct<IsLocalPlayerBoolDriver>(void* p) { new (p) IsLocalPlayerBoolDriver; }
template<> void MetaConstruct<IsMovingBoolDriver>(void* p) { new (p) IsMovingBoolDriver; }
template<> void MetaConstruct<SummonerIconData>(void* p) { new (p) SummonerIconData; }
template<> void MetaVirtual2<SummonerIconData>(void* p) { auto icon=static_cast<SummonerIconData*>(p); g_2aa7460->Register(icon->iconId,icon); }
