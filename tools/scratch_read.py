import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import match_func as M

src = os.path.join(os.path.dirname(__file__), '..', 'client-src', 'src', 'LnpMessage_Read.cpp')
orig = open(src, encoding='utf-8').read()

def test_impl(code):
    try:
        header, _ = orig.split('bool LnpMessage::Read(LnpBuffer& in, const LnpMessage& previous)')
        new_content = header + code
        open(src, 'w', encoding='utf-8').write(new_content)
        fname, size, same, first, report = M.compare(src, '?Read@LnpMessage', 0x2dcd40, ['-O2', '-std:c++17'])
        print(f'same={same}/{size}, first={first}')
        if report:
            print(report[:600])
        return first is None
    finally:
        open(src, 'w', encoding='utf-8').write(orig)

# Let's test what causes in.size to be in ebp
tests = [
    # 1. const reference or local size
    '''bool LnpMessage::Read(LnpBuffer& in, const LnpMessage& previous)
{
    const u16 inSize = in.size;
    u16 header;
    bool ok = in.position + 2 <= inSize;
    if (ok) {
        header = *(u16*)(in.data + in.position);
        in.position += 2;
    } else {
        header = 0;
    }
    bool fragment = header & 1;
    header >>= 1;
    bool nextNumber = header & 1;
    header >>= 1;
    bool sameChannel = header & 1;
    header >>= 1;
    if (sameChannel)
        channel = previous.channel;
    else {
        if (in.position + 1 <= inSize) {
            channel = *(u8*)(in.data + in.position);
            in.position += 1;
        } else ok = false;
    }
    if (nextNumber)
        number = previous.number + 1;
    else {
        if (in.position + 2 <= inSize) {
            number = *(u16*)(in.data + in.position);
            in.position += 2;
        } else ok = false;
    }
    if (fragment)
    {
        ok &= in.Read(fragmentId);
        ok &= in.Read(fragmentCount);
        ok &= in.Read(fragmentIndex);
    }
    ok &= in.ReadBuffer(&payload, header);
    text30 = "";
    return ok;
}''',
]

for t in tests:
    test_impl(t)

