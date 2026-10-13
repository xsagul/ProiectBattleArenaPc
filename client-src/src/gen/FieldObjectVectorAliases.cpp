// Assignment of the vector at +0x10 of FieldObj_7ec350.
// The high capacity bit marks external storage; element destruction uses virtual slot 3.
// match: 7eadb0 ??4FieldVector7eadb0@@
#include "FieldObjectAliases.h"
#include <new>

FieldVector7eadb0& FieldVector7eadb0::operator=(const FieldVector7eadb0& other)
{
    for (auto p = data, end = data + count; p < end; ++p)
        p->~FieldElement7b89e0();
    count = 0;
    u32 newCount = other.count;
    if ((capacity & 0x7fffffff) < newCount)
    {
        if ((int)capacity >= 0)
            ::operator delete(data);
        data = (FieldElement7b89e0*)::operator new(newCount * sizeof(FieldElement7b89e0));
        capacity = newCount;
    }
    auto p = data;
    auto end = data + newCount;
    count = newCount;
    auto from = other.data;
    for (; p < end; ++p, ++from)
        new (p) FieldElement7b89e0(*from);
    return *this;
}
