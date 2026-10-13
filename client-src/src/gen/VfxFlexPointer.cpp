// match: a64b00 ??1?$VfxOwnedPointer@UFlexValueVector3@@@@QAE@XZ
#include "BinClasses.h"
VfxOwnedPointer<FlexValueVector3>::~VfxOwnedPointer() { delete value; }
