"""Bounded JSON temporaries and one heavy workspace operation per store."""
import asyncio
import functools
import hashlib
import json
import logging
import resource
import sys
import time


def json_bytes(value, **options):
    parts = []
    length = 0
    for part in json.JSONEncoder(**options).iterencode(value):
        parts.append(part)
        length += len(part)
        if length >= 65536:
            yield ''.join(parts).encode('utf-8')
            parts.clear()
            length = 0
    if parts:
        yield ''.join(parts).encode('utf-8')


def json_size(value, **options):
    return sum(map(len, json_bytes(value, **options)))


def json_digest(value, **options):
    digest = hashlib.sha256()
    for part in json_bytes(value, **options):
        digest.update(part)
    return digest.hexdigest()


def retained_size(value):
    """Diagnostic only: count reachable containers once; never change eviction policy."""
    seen = set()
    def size(obj):
        identity = id(obj)
        if identity in seen:
            return 0
        seen.add(identity)
        total = sys.getsizeof(obj)
        if isinstance(obj, dict):
            total += sum(size(k) + size(v) for k, v in obj.items())
        elif isinstance(obj, (list, tuple, set, frozenset)):
            total += sum(size(v) for v in obj)
        elif hasattr(obj, '__dict__'):
            total += size(vars(obj))
        return total
    return size(value)


async def run_cpu(function, *args):
    # Cancellation must not release the memory gate while the worker still runs.
    task = asyncio.create_task(asyncio.to_thread(function, *args))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError as cancelled:
        # A second disconnect/cancellation must not cancel the worker's Task.
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        try:
            result = task.result()
            if hasattr(result, 'close'):
                result.close()
        finally:
            raise cancelled


def workspace_gate(store):
    lock = getattr(store, '_workspace_memory_lock', None)
    if lock is None:
        lock = store._workspace_memory_lock = asyncio.Lock()
    def decorate(function):
        @functools.wraps(function)
        async def guarded(*args, **kwargs):
            queued = time.monotonic()
            async with lock:
                started = time.monotonic()
                try:
                    return await function(*args, **kwargs)
                finally:
                    logging.getLogger(__name__).info(
                        'workspace_memory operation=%s wait_ms=%d elapsed_ms=%d peak_rss_kib=%d cache_retained_bytes=%d',
                        function.__name__, (started-queued)*1000,
                        (time.monotonic()-started)*1000,
                        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        store.retained_bytes() if hasattr(store, 'retained_bytes') else 0)
        return guarded
    return decorate
