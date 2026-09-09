from collections import Counter
from math import ceil
from statistics import fmean

from rupturelab.experiments.models import (
    PhaseName,
    PhaseResult,
    RequestMeasurement,
)


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)
    rank = max(1, ceil(percentile_value * len(ordered)))

    return ordered[rank - 1]


def summarize_phase(
    phase: PhaseName,
    measurements: list[RequestMeasurement],
) -> PhaseResult:
    latencies = [measurement.duration_ms for measurement in measurements]

    status_codes = Counter(
        str(measurement.status_code)
        for measurement in measurements
        if measurement.status_code is not None
    )

    successful = sum(measurement.successful for measurement in measurements)

    transport_errors = sum(measurement.error is not None for measurement in measurements)

    faulted = sum(measurement.fault is not None for measurement in measurements)

    return PhaseResult(
        phase=phase,
        request_count=len(measurements),
        successful_requests=successful,
        failed_requests=len(measurements) - successful,
        transport_errors=transport_errors,
        faulted_requests=faulted,
        status_codes=dict(status_codes),
        average_latency_ms=round(fmean(latencies), 3) if latencies else 0.0,
        p95_latency_ms=round(percentile(latencies, 0.95), 3),
        measurements=measurements,
    )
