from localscribe.monitoring.backpressure import BackpressureState


def test_levels():
    s = BackpressureState(queue_depth=1, queue_capacity=10)
    assert s.level() == "ok"
    s2 = BackpressureState(queue_depth=9, queue_capacity=10)
    assert s2.level() == "critical"
    assert len(s2.policy_steps()) == 6
