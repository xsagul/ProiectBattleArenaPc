// The C free entry point folds with ordinary operator delete in this client.
// same: 9bb930 _free
void Pool_Free(void*); // rva 0x9d42e0

extern "C" void free(void* p)
{
    Pool_Free(p);
}
