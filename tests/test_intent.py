from sim_racecenter_agent.core.intent import classify_intent


def test_intent_leader():
    assert classify_intent("Who's leading now?") == "LEADER"


def test_intent_battle():
    assert classify_intent("any close battles?") == "BATTLE"
    assert classify_intent("Closest battle?") == "BATTLE"


def test_intent_other():
    assert classify_intent("random unrelated question") == "OTHER"
