// rva 0x2d5ae0 and 0x2d9820: the constructor and the move assignment of a worker command, written by the compiler.
// match: 2d5ae0 ??0LnpCommand@@QAE@XZ
// match: 2d9820 ??4LnpCommand@@QAEAAU0@$$QAU0@@Z
#include "LnpCommand.h"

LnpCommand::LnpCommand() = default;

LnpCommand& LnpCommand::operator=(LnpCommand&& other) = default;
