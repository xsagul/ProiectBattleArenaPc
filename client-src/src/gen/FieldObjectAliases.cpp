// The typed object assignment shares the client body already lifted in Small_7e0000.cpp.
// Every alias is checked against the compiled body and relocation targets.
// match: 7ec350 ??4FieldObj_7ec350@@
#include "FieldObjectAliases.h"

FieldObj_7ec350& FieldObj_7ec350::operator=(const FieldObj_7ec350& other)
{
    member04 = other.member04;
    member08 = other.member08;
    member0c = other.member0c;
    vector10 = other.vector10;
    member1c = other.member1c;
    member20 = other.member20;
    member24 = other.member24;
    member28 = other.member28;
    member2c = other.member2c;
    return *this;
}
