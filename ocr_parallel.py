"""Bounded CPU/GPU OCR scheduling; respect the user's worker count."""
import os
from concurrent.futures import wait, FIRST_COMPLETED


def available_memory_gb():
    if os.name != 'nt':
        return 0
    import ctypes
    class MemoryStatus(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(name, ctypes.c_ulonglong) for name in ('total_phys','avail_phys','total_page','avail_page','total_virtual','avail_virtual','extended')]
    status=MemoryStatus();status.length=ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return 0
    return status.avail_phys / 1024**3


def choose_workers(requested, pages):
    if requested not in (1, 2):
        raise ValueError('OCR workers must be 1 or 2.')
    return min(requested, max(1, pages))


def bounded_results(executor, function, tasks, limit):
    """Yield completed jobs, preparing no more than limit in-flight pages."""
    iterator = iter(enumerate(tasks))
    active = {}
    exhausted = False
    while active or not exhausted:
        while len(active) < limit and not exhausted:
            try:
                index, args = next(iterator)
            except StopIteration:
                exhausted = True
                break
            try:
                active[executor.submit(function, *args)] = index
            except Exception as exc:
                yield index, None, exc
        if not active:
            continue
        ready, _ = wait(active, return_when=FIRST_COMPLETED)
        for future in ready:
            index = active.pop(future)
            try:
                value = future.result()
            except Exception as exc:
                yield index, None, exc
            else:
                yield index, value, None
