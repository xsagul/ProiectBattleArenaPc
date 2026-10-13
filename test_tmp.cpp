
typedef unsigned int uint32_t;
typedef unsigned char uint8_t;
extern const void* g_vtable157adfc;
struct Object2f2780 {
    const void* vtable;
    uint32_t val4;
    uint8_t val8;
    uint32_t val0c;
    void* Clone(void* dst) const;
};

    void* Object2f2780::Clone(void* dst) const {
        auto* p = (Object2f2780*)dst;
        p->vtable = &g_vtable157adfc;
        p->val4 = this->val4;
        p->val8 = this->val8;
        p->val0c = this->val0c;
        return p;
    }
    
