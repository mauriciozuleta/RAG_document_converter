"""Bounded OCR scheduling with conservative Windows memory limits."""
import os
from concurrent.futures import wait, FIRST_COMPLETED


def available_memory_gb():
    if os.name != 'nt':
        return 0
    import ctypes
    class MemoryStatus(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in
            ('total_phys', 'avail_phys', 'total_page', 'avail_page', 'total_virtual', 'avail_virtual', 'extended')]
    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return 0
    return status.avail_phys / 1024**3


def choose_workers(requested, pages):
    if requested not in (1, 2):
        raise ValueError('OCR workers must be 1 or 2.')
    if os.environ.get('PDF_RAG_OCR_DEVICE', 'cpu').startswith('gpu'):
        return 1
    if requested == 1 or pages < 2:
        return 1
    available = available_memory_gb()
    if available < 12 or (os.cpu_count() or 1) < 8:
        print(f'[INFO] Using one OCR worker: {available:.1f} GB free RAM; two workers require 12 GB free and 8 logical CPUs.', flush=True)
        return 1
    return 2


def bounded_results(executor, function, tasks, limit):
    """Yield completed jobs without enqueueing an entire large document."""
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
