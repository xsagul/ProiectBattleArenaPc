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
 const auto experiment_counter=WorkerCounterNow();
 const auto experiment_origin=*origin;
 return double(experiment_counter-experiment_origin) * g_workerSecondsPerTick;
}
