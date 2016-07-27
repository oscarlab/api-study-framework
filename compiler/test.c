#include <stdint.h>

static inline void cpuid(int code, uint32_t *a, uint32_t *d)
{
	asm volatile("cpuid":"=a"(*a),"=d"(*d):"a"(code):"ecx","ebx");
}

#define cpuid_macro(code, a, d) \
	do { asm volatile("cpuid":"=a"(a),"=d"(d):"a"(code):"ecx","ebx"); } while (0)

int main (int argc, const char ** argv)
{
	uint32_t a, d;
	asm volatile("cpuid":"=a"(a),"=d"(d):"ai"(0):"ecx","ebx");
	__asm__ __volatile__("cpuid\r\ncpuid;cpuid":"=a"(a),"=d"(d):"ai"(0):"ecx","ebx");
	cpuid(0, &a, &d);
	cpuid_macro(0, a, d);
	return 0;
}
