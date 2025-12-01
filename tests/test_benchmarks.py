import os
import time

from wattameter.benchmark import utils as bench_utils
from wattameter.benchmark import update_time as bench_update
from wattameter.benchmark import overhead as bench_overhead


def test_estimate_dt_basic():
    # create a function whose value changes every 3 calls
    state = {"calls": 0}

    def f():
        state["calls"] += 1
        return state["calls"] // 3

    # run with a small number of trials and a tiny sleep to keep test fast
    res = bench_utils.estimate_dt(f, n_trials=4, sleep_dt=0.0, ntmax=100)

    # estimate_dt should return a list of positive floats (n_trials entries)
    assert isinstance(res, list)
    assert len(res) == 4
    for v in res:
        assert v > 0


def test__benchmark_metric_prints_stats(monkeypatch, capsys):
    # Force estimate_dt to return deterministic values
    monkeypatch.setattr(
        bench_update,
        "estimate_dt",
        lambda f, n_trials, ntmax: [0.1, 0.1, 0.1],
    )

    # Patch time.perf_counter to make mean_freq calculation deterministic
    perf = [0.0, 1.0]

    def fake_perf():
        return perf.pop(0) if perf else 2.0

    monkeypatch.setattr(time, "perf_counter", fake_perf)

    # Provide a dummy getter
    def getter():
        return 42

    # Call internal function; it should not raise and should print frequency info
    bench_update._benchmark_metric("DummyMetric", getter, "unit")

    captured = capsys.readouterr()
    assert "Mean update frequency" in captured.out
    # metric name is printed lowercased inside the helper
    assert "dummymetric" in captured.out


def test_benchmark_static_overhead_monkeypatched_main(monkeypatch):
    # Replace the main function in the overhead module with a quick no-op
    monkeypatch.setattr(bench_overhead, "main", lambda: None)

    # Ensure cwd is restored after call
    cwd_before = os.getcwd()
    static = bench_overhead.benchmark_static_overhead()

    assert isinstance(static, float)
    assert os.getcwd() == cwd_before


def test_benchmark_dynamic_overhead_fast(monkeypatch):
    # Replace main with a no-op so the spawned process does nothing
    monkeypatch.setattr(bench_overhead, "main", lambda: None)

    # Replace multiprocessing.Process with a dummy that mimics API
    class DummyProcess:
        def __init__(self, *args, **kwargs):
            self.pid = None

        def start(self):
            return None

        def join(self):
            return None

        def is_alive(self):
            return True

    monkeypatch.setattr("multiprocessing.Process", lambda *a, **k: DummyProcess())

    # Patch time.sleep to no-op to avoid long waits
    monkeypatch.setattr(time, "sleep", lambda s: None)

    # Call the dynamic benchmark; it should run quickly and not raise
    bench_overhead.benchmark_dynamic_overhead(cpu_stress_test=False, gpu_burn_dir=None)
