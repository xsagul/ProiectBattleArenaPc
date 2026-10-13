#include <stdint.h>
int64_t WorkerCounterNow(); // rva 0x9cbbc0: separately compiled counter reader
extern double g_workerSecondsPerTick;
struct WorkerClockProbe
{
    const int64_t* origin;
    double Now();
};
double WorkerClockProbe::Now()
{
    return double(WorkerCounterNow() - *origin) * g_workerSecondsPerTick;
}
