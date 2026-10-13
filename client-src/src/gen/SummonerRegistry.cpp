// same: f95b0 ??$_Find_lower_bound@I@?$_Tree@V?$_Tmap_traits@IPAUSummonerIconData@@U?$less@I@std@@V?$allocator@U?$pair@$$CBIPAUSummonerIconData@@@std@@@3@$0A@@std@@@std@@IBE?AU?$_Tree_find_result@PAU?$_Tree_node@U?$pair@$$CBIPAUSummonerIconData@@@std@@PAX@std@@@1@ABI@Z
// same: 124b60 ?_Insert_node@?$_Tree_val@U?$_Tree_simple_types@U?$pair@$$CBIPAUSummonerIconData@@@std@@@std@@@std@@QAEPAU?$_Tree_node@U?$pair@$$CBIPAUSummonerIconData@@@std@@PAX@2@U?$_Tree_id@PAU?$_Tree_node@U?$pair@$$CBIPAUSummonerIconData@@@std@@PAX@std@@@2@QAU32@@Z
// same: 125680 ?_Throw_tree_length_error@std@@YAXXZ
// match: 63c7c0 ?Register@SummonerRegistry@@QAEXIPAUSummonerIconData@@@Z
#include "BinClasses.h"
void SummonerRegistry::Register(u32 id,SummonerIconData* icon) { icons[id]=icon; }
SummonerIconData* SummonerRegistry::Find(u32 id) { auto p=icons.find(id); return p==icons.end()?nullptr:p->second; }
