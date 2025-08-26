from sim_racecenter_agent.core.intent import classify_intent


def test_classify_driver_search():
    assert classify_intent("is there a jimmy in this race?") == "DRIVER_SEARCH"
    assert classify_intent("any driver named bob") == "DRIVER_SEARCH"
    assert classify_intent("do we have someone quick") == "DRIVER_SEARCH"
