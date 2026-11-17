"""Behavioral checks beyond the public hand-built vectors."""
import copy
from types import SimpleNamespace
import pytest
from lab9 import gate, stats
from lab9.graders import ReplyLedgerConsistent
from lab9.trace_case import investigate

pytestmark = pytest.mark.student

@pytest.fixture(autouse=True)
def preserve_shape_registry():
    from lab8.shapes import SHAPES
    original = dict(SHAPES)
    try:
        yield
    finally:
        SHAPES.clear()
        SHAPES.update(original)


@pytest.mark.parametrize("text,amount,expected", [
    ("Đã hoàn 35.000đ",35000,True), ("Đã hoàn phí 35,000 VND",35000,True),
    ("Đã hoàn 35 000 đồng",35000,True), ("Đã hoàn 35.000đ",20000,False),
    ("Đã hoàn 0đ",35000,False), ("Đã hoàn cho đơn O-808",35000,False)])
def test_lab9_reply_amount_formats(text,amount,expected):
    trial={"events":[{"kind":"reply","payload":{"text":text}}],
           "snapshot":{"refund_vnd":amount},"result":{"status":"resolved"}}
    assert ReplyLedgerConsistent().evaluate(SimpleNamespace(output=trial)).value is expected

def test_lab9_first_wrong_step_ticket_override():
    bad=investigate("seeded_regression","C-002",11)["trial"]
    good=investigate("fixed","C-002",11)["trial"]
    assert [e["kind"] for e in bad["events"]][:3]==["handoff","investigator","model_override"]
    assert bad["snapshot"]["refund_vnd"]==20000 and not bad["lab8_pass"]
    assert good["snapshot"]["refund_vnd"]==0 and good["lab8_pass"]
    assert not any(e["kind"]=="model_override" for e in good["events"])

@pytest.mark.parametrize("args",[(0,0,1),(5,-1,2),(5,6,1),(5,2,0),(3,1,4),(5.,2,1),(True,0,1)])
def test_lab9_both_estimators_reject_invalid(args):
    for fn in (stats.pass_at_k,stats.pass_hat_k):
        with pytest.raises(ValueError): fn(*args)

def test_lab9_integrity_duplicate_and_errors_on_green_run():
    from tests.test_lab9_advanced import ROWS,SPEC,_report
    base=_report(copy.deepcopy(ROWS),{"pass_rate":1.})
    dup=copy.deepcopy(base);dup["rows"][-1]=copy.deepcopy(dup["rows"][0])
    assert gate.integrity_check(dup,base,SPEC)
    crash=copy.deepcopy(base);crash["evaluator_failures"]=["grader crashed"]
    assert gate.integrity_check(crash,base,SPEC)
    tags=copy.deepcopy(base);tags["rows"][0]["slices"]=[]
    assert gate.integrity_check(tags,base,SPEC)
    forged=copy.deepcopy(base);forged["metrics"]["pass_rate"]=.5
    assert gate.integrity_check(forged,base,SPEC)
