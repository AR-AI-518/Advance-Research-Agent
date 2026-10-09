import logging
import json
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName
        }

        if hasattr(record, "extract_data"):
            log_obj.update(record.extract_data)

        return json.dumps(log_obj)


def setup_logging():
    logger = logging.getLogger("observ")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger


class MetricsCollection:
    def __init__(self):
        self.metrics = {
            "total_request": 0,
            "total_error": 0,
            "latency_sum": 0.0,
            "latency_count": 0,
            "input_token": 0,
            "output_token": 0,
            "cache_hit": 0,
            "cache_miss": 0
        }

    def record_request(
        self,
        latency: float,
        input_token: int,
        output_token: int,
        error: bool = False,
        cache_hit: bool = False
    ):
        self.metrics["total_request"] += 1
        self.metrics["latency_sum"] += latency
        self.metrics["latency_count"] += 1
        self.metrics["input_token"] += input_token
        self.metrics["output_token"] += output_token

        if error:
            self.metrics["total_error"] += 1

        if cache_hit:
            self.metrics["cache_hit"] += 1
        else:
            self.metrics["cache_miss"] += 1

    def summarize(self) -> dict:
        avg_latency = (
            self.metrics["latency_sum"] / self.metrics["latency_count"]
            if self.metrics["latency_count"] > 0
            else 0
        )

        error_rate = (
            self.metrics["total_error"] / self.metrics["total_request"]
            if self.metrics["total_request"] > 0
            else 0
        )

        cache_hit_rate = (
            self.metrics["cache_hit"] / self.metrics["total_request"]
            if self.metrics["total_request"] > 0
            else 0
        )

        return {
            "total_request": self.metrics["total_request"],
            "total_error": self.metrics["total_error"],
            "avg_latency": avg_latency,
            "error_rate": error_rate,
            "cache_hit_rate": cache_hit_rate,
            "input_token": self.metrics["input_token"],
            "output_token": self.metrics["output_token"]
        }
