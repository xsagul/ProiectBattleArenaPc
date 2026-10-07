// Reconstructed Object2da850 (singleton object with GlobalInstance base).
// Constructor at rva 0x2d5050 (zone A); deleting destructor at rva 0x2dab80 (zone B).
// match: 2dab80 ??_GObject2da850@@UAEPAXI@Z
// match: 2d5050 ??0Object2da850@@QAE@I@Z
#include "ZoneB_GlobalInstance.h"


struct Object2da850 : GlobalInstance<Object2da850>
{
    u32 val4;
    u32 val8;

    Object2da850(u32 unused = 0);
    virtual ~Object2da850() override;
};

Object2da850::Object2da850(u32 unused)
{
    val8 = 1;
    val4 = 1;
}


Object2da850::~Object2da850() = default;


template <>
Object2da850* GlobalInstance<Object2da850>::instance = nullptr;

void ForceEmitDeletingDtor(Object2da850* p)
{
    delete p;
}

Object2da850* Create()
{
    return new Object2da850();
}



