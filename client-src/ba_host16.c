/* ba_host16: our code inside the 16.20 game process (64-bit), loaded as DINPUT8.dll from
 * game16 (the exe imports DINPUT8!DirectInput8Create, so Windows loads us before the
 * packer's entry point runs). Never put this file in the live install.
 *
 * Step 1: stop once at the game's original entry point (rva OEP_RVA, found in the memory
 * image) with a hardware breakpoint on the main thread and write the whole image to
 * ba16_oep.bin: sections decrypted by the packer, data still untouched by the game.
 *
 * build: x86_64-w64-mingw32-clang -O2 -shared -o game16/DINPUT8.dll \
 *        client-src/ba_host16.c client-src/ba_host16.def
 */
#include <windows.h>
#include <tlhelp32.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#define OEP_RVA 0x196287c

static HANDLE g_log = INVALID_HANDLE_VALUE;
static BYTE *g_base;
static DWORD g_size;
static char g_dir[MAX_PATH];
static HMODULE g_real;

static void logf(const char *fmt, ...)
{
    char buf[1024];
    va_list ap;
    DWORD n;
    va_start(ap, fmt);
    n = (DWORD)vsnprintf(buf, sizeof buf, fmt, ap);
    va_end(ap);
    if (g_log != INVALID_HANDLE_VALUE)
        WriteFile(g_log, buf, n, &n, NULL);
}

static void dump_image(const char *name)
{
    char path[MAX_PATH];
    static BYTE zero[0x1000];
    HANDLE f;
    BYTE *p = g_base, *end = g_base + g_size;
    DWORD w, readable = 0, skipped = 0;
    snprintf(path, sizeof path, "%s\\%s", g_dir, name);
    f = CreateFileA(path, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, 0, NULL);
    if (f == INVALID_HANDLE_VALUE)
        return;
    while (p < end) {
        MEMORY_BASIC_INFORMATION mbi;
        BYTE *stop;
        int ok;
        if (!VirtualQuery(p, &mbi, sizeof mbi))
            break;
        stop = (BYTE *)mbi.BaseAddress + mbi.RegionSize;
        if (stop > end)
            stop = end;
        ok = mbi.State == MEM_COMMIT && !(mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD));
        logf("  region %08llx %08llx prot %lx %s\r\n", (unsigned long long)(p - g_base),
             (unsigned long long)(stop - p), mbi.Protect, ok ? "read" : "skip");
        for (; p < stop; p += 0x1000) {
            WriteFile(f, ok ? p : zero, 0x1000, &w, NULL);
            if (ok) readable++; else skipped++;
        }
    }
    CloseHandle(f);
    logf("dump %s: %lu pages read, %lu skipped\r\n", name, readable, skipped);
}

/* Probes: up to four code addresses (rva, hex, one per line in ba16_probes.txt beside the exe) watched on
 * the main thread with the debug registers; nothing in the game's code is changed. Each hit logs the
 * registers, where the call came from and the bytes the first three arguments point at. */
static DWORD g_probe[4];
static int g_nprobes, g_hits[4], g_light[4], g_want_dump;
static volatile LONG g_entered;

static void log_bytes(const char *what, DWORD64 p)
{
    char line[160];
    int i, n = 0;
    if (p < 0x10000 || IsBadReadPtr((void *)p, 32))
        return;
    for (i = 0; i < 32; i++)
        n += snprintf(line + n, sizeof line - n, "%02x", ((BYTE *)p)[i]);
    logf("    %s -> %s\r\n", what, line);
}

static void probe_hit(int i, CONTEXT *c)
{
    DWORD64 ret = 0;
    if (g_light[i]) { /* "<rva> light" in ba16_probes.txt: one short line per hit, no limit to speak of */
        if (++g_hits[i] <= 200000)
            logf("p %x rdx %llx\r\n", g_probe[i], c->Rdx);
        return;
    }
    if (++g_hits[i] > 60)
        return;
    if (!IsBadReadPtr((void *)c->Rsp, 8))
        ret = *(DWORD64 *)c->Rsp;
    logf("probe %x hit %d: rcx %llx rdx %llx r8 %llx r9 %llx rax %llx from rva %llx\r\n", g_probe[i], g_hits[i],
         c->Rcx, c->Rdx, c->R8, c->R9, c->Rax, ret - (DWORD64)g_base);
    log_bytes("rcx", c->Rcx);
    log_bytes("rdx", c->Rdx);
    if (c->Rdx >= 0x10000 && !IsBadReadPtr((void *)c->Rdx, 8))
        log_bytes("[rdx]", *(DWORD64 *)c->Rdx);
    log_bytes("r8", c->R8);
}

static void load_probes(void)
{
    char path[MAX_PATH], line[64];
    FILE *f;
    snprintf(path, sizeof path, "%s\\ba16_probes.txt", g_dir);
    f = fopen(path, "r");
    while (f && g_nprobes < 4 && fgets(line, sizeof line, f))
        if (sscanf(line, "%lx", &g_probe[g_nprobes]) == 1) {
            g_light[g_nprobes] = strstr(line, "light") != NULL;
            g_nprobes++;
        }
    if (f)
        fclose(f);
    snprintf(path, sizeof path, "%s\\ba16_want_oep_dump", g_dir);
    g_want_dump = GetFileAttributesA(path) != INVALID_FILE_ATTRIBUTES;
}

static LONG CALLBACK on_exception(EXCEPTION_POINTERS *e)
{
    CONTEXT *c = e->ContextRecord;
    if (e->ExceptionRecord->ExceptionCode == EXCEPTION_ACCESS_VIOLATION) {
        /* where the game faults: instruction, address touched, and the code addresses on its stack */
        static LONG seen;
        if (InterlockedIncrement(&seen) <= 6) {
            DWORD64 *sp = (DWORD64 *)c->Rsp;
            int i, n = 0;
            logf("access violation at rva %llx (rip %llx) touching %llx, thread %lu; rcx %llx rdx %llx rax %llx\r\n",
                 c->Rip - (DWORD64)g_base, c->Rip, (DWORD64)e->ExceptionRecord->ExceptionInformation[1],
                 GetCurrentThreadId(), c->Rcx, c->Rdx, c->Rax);
            for (i = 0; i < 400 && n < 14 && !IsBadReadPtr(sp + i, 8); i++)
                if (sp[i] >= (DWORD64)g_base + 0x1000 && sp[i] < (DWORD64)g_base + 0x19fd000) {
                    logf("    stack +%x: rva %llx\r\n", i * 8, sp[i] - (DWORD64)g_base);
                    n++;
                }
        }
        return EXCEPTION_CONTINUE_SEARCH;
    }
    if (e->ExceptionRecord->ExceptionCode != EXCEPTION_SINGLE_STEP)
        return EXCEPTION_CONTINUE_SEARCH;
    if ((BYTE *)e->ExceptionRecord->ExceptionAddress != g_base + OEP_RVA) {
        int i;
        for (i = 0; i < g_nprobes; i++)
            if ((BYTE *)e->ExceptionRecord->ExceptionAddress == g_base + g_probe[i]) {
                probe_hit(i, c);
                c->Dr6 = 0;
                c->EFlags |= 0x10000; /* resume flag: run the instruction instead of stopping on it again */
                return EXCEPTION_CONTINUE_EXECUTION;
            }
        logf("single step elsewhere: %p thread %lu\r\n", e->ExceptionRecord->ExceptionAddress, GetCurrentThreadId());
        return EXCEPTION_CONTINUE_SEARCH;
    }
    logf("at entry: rip %llx rsp %llx rcx %llx rdx %llx r8 %llx r9 %llx thread %lu\r\n",
         c->Rip, c->Rsp, c->Rcx, c->Rdx, c->R8, c->R9, GetCurrentThreadId());
    g_entered = 1;
    if (g_want_dump)
        dump_image("ba16_oep.bin");
    /* from here on the four debug registers of the main thread watch the probes of ba16_probes.txt */
    c->Dr0 = c->Dr1 = c->Dr2 = c->Dr3 = 0;
    c->Dr6 = 0;
    c->Dr7 = 0;
    if (g_nprobes > 0) { c->Dr0 = (DWORD64)(g_base + g_probe[0]); c->Dr7 |= 1; }
    if (g_nprobes > 1) { c->Dr1 = (DWORD64)(g_base + g_probe[1]); c->Dr7 |= 4; }
    if (g_nprobes > 2) { c->Dr2 = (DWORD64)(g_base + g_probe[2]); c->Dr7 |= 0x10; }
    if (g_nprobes > 3) { c->Dr3 = (DWORD64)(g_base + g_probe[3]); c->Dr7 |= 0x40; }
    return EXCEPTION_CONTINUE_EXECUTION;
}

/* The breakpoint is set from a second thread: debug registers written by the main thread
 * on itself during DLL load did not survive until the entry point (measured: armed, never hit). */
static DWORD WINAPI arm_entry_breakpoint(void *arg)
{
    DWORD tid = (DWORD)(ULONG_PTR)arg, i;
    HANDLE th = OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_SET_CONTEXT, FALSE, tid);
    static const BYTE entry_code[4] = {0x48, 0x83, 0xec, 0x28};
    CONTEXT c;
    int ok;
    memset(&c, 0, sizeof c);
    c.ContextFlags = CONTEXT_DEBUG_REGISTERS;
    if (g_want_dump) {
        /* Stop at the entry point itself. Not reliable: in about half of the match-mode runs the
         * registers were gone again before the entry was reached (measured), so it is only used
         * when the entry image is wanted (file ba16_want_oep_dump); the probes follow from there. */
        c.Dr0 = (DWORD64)(g_base + OEP_RVA);
        c.Dr7 = 1; /* local enable 0, execute, 1 byte */
        SuspendThread(th);
        ok = SetThreadContext(th, &c);
        ResumeThread(th);
        logf("entry breakpoint at %p set on thread %lu: %d\r\n", g_base + OEP_RVA, tid, ok);
    } else {
        /* Probes only: wait until the packer has decrypted the code, then set them. */
        for (i = 0; i < 30000 && memcmp(g_base + OEP_RVA, entry_code, 4); i++)
            Sleep(1);
        Sleep(300);
        if (g_nprobes > 0) { c.Dr0 = (DWORD64)(g_base + g_probe[0]); c.Dr7 |= 1; }
        if (g_nprobes > 1) { c.Dr1 = (DWORD64)(g_base + g_probe[1]); c.Dr7 |= 4; }
        if (g_nprobes > 2) { c.Dr2 = (DWORD64)(g_base + g_probe[2]); c.Dr7 |= 0x10; }
        if (g_nprobes > 3) { c.Dr3 = (DWORD64)(g_base + g_probe[3]); c.Dr7 |= 0x40; }
        logf("code decrypted after %lu ms; %d probes\r\n", i, g_nprobes);
        /* every thread of the process gets the probes, new threads within half a second */
        {
            static DWORD armed[512];
            int narmed = 0, round;
            for (round = 0; round < 240 && g_nprobes; round++) {
                HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
                THREADENTRY32 te;
                te.dwSize = sizeof te;
                if (snap != INVALID_HANDLE_VALUE && Thread32First(snap, &te)) {
                    do {
                        int k, seen = 0;
                        HANDLE t;
                        if (te.th32OwnerProcessID != GetCurrentProcessId() || te.th32ThreadID == GetCurrentThreadId())
                            continue;
                        for (k = 0; k < narmed; k++)
                            seen |= armed[k] == te.th32ThreadID;
                        if (seen || narmed >= 512)
                            continue;
                        t = OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_SET_CONTEXT, FALSE, te.th32ThreadID);
                        if (!t)
                            continue;
                        SuspendThread(t);
                        ok = SetThreadContext(t, &c);
                        ResumeThread(t);
                        CloseHandle(t);
                        armed[narmed++] = te.th32ThreadID;
                    } while (Thread32Next(snap, &te));
                }
                if (snap != INVALID_HANDLE_VALUE)
                    CloseHandle(snap);
                if (round == 0)
                    logf("probes set on %d threads\r\n", narmed);
                Sleep(500);
            }
        }
    }
    CloseHandle(th);
    return 0;
}

HRESULT WINAPI DirectInput8Create(HINSTANCE inst, DWORD ver, REFIID iid, void **out, void *outer)
{
    typedef HRESULT(WINAPI *fn_t)(HINSTANCE, DWORD, REFIID, void **, void *);
    fn_t fn;
    if (!g_real) {
        char path[MAX_PATH];
        GetSystemDirectoryA(path, sizeof path);
        strcat(path, "\\dinput8.dll");
        g_real = LoadLibraryA(path);
    }
    fn = (fn_t)GetProcAddress(g_real, "DirectInput8Create");
    return fn ? fn(inst, ver, iid, out, outer) : E_FAIL;
}

BOOL WINAPI DllMain(HINSTANCE self, DWORD reason, void *reserved)
{
    char path[MAX_PATH], *slash;
    IMAGE_NT_HEADERS *nt;
    (void)reserved;
    if (reason != DLL_PROCESS_ATTACH)
        return TRUE;
    GetModuleFileNameA(self, g_dir, sizeof g_dir);
    slash = strrchr(g_dir, '\\');
    if (slash)
        *slash = 0;
    if (strstr(g_dir, "Riot Games")) /* the live install is not ours to work in */
        return TRUE;
    snprintf(path, sizeof path, "%s\\ba16.log", g_dir);
    g_log = CreateFileA(path, GENERIC_WRITE, FILE_SHARE_READ, NULL, CREATE_ALWAYS, 0, NULL);
    g_base = (BYTE *)GetModuleHandleA(NULL);
    nt = (IMAGE_NT_HEADERS *)(g_base + ((IMAGE_DOS_HEADER *)g_base)->e_lfanew);
    g_size = nt->OptionalHeader.SizeOfImage;
    logf("ba_host16 loaded: base %p size %lx thread %lu, .text starts %02x %02x %02x %02x\r\n", g_base, g_size,
         GetCurrentThreadId(), g_base[0x1000], g_base[0x1001], g_base[0x1002], g_base[0x1003]);
    load_probes();
    AddVectoredExceptionHandler(1, on_exception);
    CreateThread(NULL, 0, arm_entry_breakpoint, (void *)(ULONG_PTR)GetCurrentThreadId(), 0, NULL);
    return TRUE;
}
