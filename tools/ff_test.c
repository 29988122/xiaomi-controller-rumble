/* SPDX-License-Identifier: GPL-2.0-or-later
 * Freestanding AArch64 evdev rumble test. No Android app or shared libc required.
 * Every uploaded effect is bounded to 400 ms by the kernel FF subsystem.
 */
#include <linux/types.h>
#define _IOC_TYPECHECK(type) (sizeof(type))
#include <linux/ioctl.h>
#include <linux/input.h>
#include <asm/unistd.h>

_Static_assert(sizeof(struct input_event) == 24, "Requires AArch64 input ABI");
_Static_assert(sizeof(struct ff_effect) == 48, "Unexpected FF effect ABI");
_Static_assert(EVIOCSFF == 0x40304580, "Unexpected evdev upload ioctl");
_Static_assert(EVIOCRMFF == 0x40044581, "Unexpected evdev erase ioctl");

static long call(long nr, long a, long b, long c, long d)
{
    register long x8 __asm__("x8") = nr;
    register long x0 __asm__("x0") = a;
    register long x1 __asm__("x1") = b;
    register long x2 __asm__("x2") = c;
    register long x3 __asm__("x3") = d;
    __asm__ volatile("svc 0" : "+r"(x0) : "r"(x8), "r"(x1), "r"(x2), "r"(x3) : "memory", "cc");
    return x0;
}

static void clear(void *ptr, unsigned long n)
{
    unsigned char *p = ptr;
    while (n--) *p++ = 0;
}

static void say(const char *s)
{
    unsigned long n = 0;
    while (s[n]) ++n;
    call(__NR_write, 1, (long)s, n, 0);
}

static void number(long n)
{
    char buf[32];
    unsigned long i = sizeof(buf);
    int negative = n < 0;
    if (negative) n = -n;
    buf[--i] = '\n';
    do { buf[--i] = '0' + n % 10; n /= 10; } while (n);
    if (negative) buf[--i] = '-';
    call(__NR_write, 1, (long)(buf + i), sizeof(buf) - i, 0);
}

static void wait_ms(unsigned long ms)
{
    struct { long sec; long nsec; } t = {ms / 1000, (ms % 1000) * 1000000}, rem;
    while (call(__NR_nanosleep, (long)&t, (long)&rem, 0, 0) == -4) t = rem;
}

static int pulse(int fd, unsigned int strong, unsigned int weak)
{
    struct ff_effect effect;
    struct input_event event;
    long result, stopped, erased;
    clear(&effect, sizeof(effect));
    effect.type = FF_RUMBLE;
    effect.id = -1;
    effect.u.rumble.strong_magnitude = strong;
    effect.u.rumble.weak_magnitude = weak;
    effect.replay.length = 400;
    result = call(__NR_ioctl, fd, EVIOCSFF, (long)&effect, 0);
    if (result < 0) { say("EVIOCSFF error: "); number(result); return 1; }
    clear(&event, sizeof(event));
    event.type = EV_FF;
    event.code = effect.id;
    event.value = 1;
    result = call(__NR_write, fd, (long)&event, sizeof(event), 0);
    if (result != sizeof(event)) {
        say("EV_FF write error: "); number(result);
        call(__NR_ioctl, fd, EVIOCRMFF, effect.id, 0);
        return 1;
    }
    wait_ms(500);
    event.value = 0;
    stopped = call(__NR_write, fd, (long)&event, sizeof(event), 0);
    erased = call(__NR_ioctl, fd, EVIOCRMFF, effect.id, 0);
    if (stopped != sizeof(event)) {
        say("EV_FF stop error: "); number(stopped); return 1;
    }
    if (erased < 0) { say("EVIOCRMFF error: "); number(erased); return 1; }
    return 0;
}

int main(long argc, char **argv)
{
    long fd;
    int result;
    if (argc != 2) { say("Usage: ff_test /dev/input/eventN\n"); return 2; }
    fd = call(__NR_openat, -100, (long)argv[1], 2 | 02000000, 0);
    if (fd < 0) { say("open error: "); number(fd); return 1; }
    say("FF_RUMBLE: left once, right twice, 400 ms each.\n");
    wait_ms(1000);
    result = pulse(fd, 80 * 256, 0);
    if (!result) { wait_ms(800); result = pulse(fd, 0, 80 * 256); }
    if (!result) { wait_ms(400); result = pulse(fd, 0, 80 * 256); }
    call(__NR_close, fd, 0, 0, 0);
    if (!result) say("Kernel FF upload/play/stop/erase succeeded; confirm physical rumble.\n");
    return result;
}

__asm__(".global _start\n_start:\nldr x0, [sp]\nadd x1, sp, #8\nbl main\nmov x8, #93\nsvc #0\n");
