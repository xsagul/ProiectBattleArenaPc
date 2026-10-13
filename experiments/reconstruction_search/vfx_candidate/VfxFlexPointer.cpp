#include "VfxOwnedClasses.h"
VfxOwnedPointer<FlexValueVector3>::~VfxOwnedPointer() { delete value; }
