import json
import logging
import sys
import time
from contextlib import contextmanager
from typing import Optional
 
 
class StructuredLogger:
    def __init__(self, name: str = "ekp"):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.INFO)
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)
            file_handler = logging.FileHandler("ekp_events.log")
            file_handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(file_handler)
 
    def event(self, stage, latency_ms, success, tenant_id=None, error_reason=None, **extra):
        record = {
            "ts": time.time(),
            "stage": stage,
            "latency_ms": round(latency_ms, 2),
            "success": success,
            "tenant_id": tenant_id,
            "error_reason": error_reason,
            **extra,
        }
        self._logger.info(json.dumps(record))
 
 
log = StructuredLogger()
 
 
@contextmanager
def timed_stage(stage: str, tenant_id: Optional[str] = None, **extra):
    start = time.perf_counter()
    ctx = {}
    try:
        yield ctx
        latency_ms = (time.perf_counter() - start) * 1000
        log.event(stage, latency_ms, success=True, tenant_id=tenant_id, **extra, **ctx)
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        log.event(stage, latency_ms, success=False, tenant_id=tenant_id,
                   error_reason=f"{type(e).__name__}: {e}", **extra)
        raise
