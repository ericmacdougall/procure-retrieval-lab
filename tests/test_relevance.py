import pathlib
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
from relevance import identity,equivalent_groups,repair_questions


def doc(i,title="Springvale Scaffolding",buyer="Council Limited",supplier="Red Sky Scaffold Ltd",date="2024-03-01"):
    return dict(doc_id=i,title=title,buyer=buyer,suppliers=[supplier],amounts=[100.],currency="GBP",contract_start="2024-04-01",contract_end="2024-12-01",award_date=date)


def test_legal_name_punctuation_aliases_and_record_versions():
    assert identity("J.R.M Electrical Contractors Limited")==identity("JRM Electrical Contractors")
    a=doc("a",title="Springvale Scaffolding - AWARD")
    b=doc("b",buyer="Council",supplier="Red Sky Scaffolding")
    assert equivalent_groups([a,b])["a"]==["a","b"]


def test_different_contract_period_is_never_collapsed():
    a=doc("a");b=doc("b");b["contract_end"]="2025-12-01"
    assert equivalent_groups([a,b])["a"]==["a"]


def test_renewal_suffix_and_inc_are_aliases_only_with_identical_contract_facts():
    a=doc("a",title="Identity Management Product - Subscription Renewal",supplier="Example")
    b=doc("b",title="Identity Management Product",supplier="Example, Inc")
    assert equivalent_groups([a,b])["a"]==["a","b"]
    b["amounts"]=[101.]
    assert equivalent_groups([a,b])["a"]==["a"]


def test_qualifier_not_copied_from_the_requested_award_date_answer():
    q=dict(id="q",text="When awarded?",slice="factoid-date",split="dev",gold_doc_ids=["a"],meta=dict(field="award_date"))
    a=doc("a",title="Contract award notification")
    repaired,_,_=repair_questions([q],[a],set())
    assert a["award_date"] not in repaired[0]["text"]


def test_no_answer_cannot_hide_an_available_equivalent_record():
    q=dict(id="q",text="Find record",slice="no-answer",split="dev",gold_doc_ids=[],meta=dict(withheld_doc="a"))
    repaired,_,excluded=repair_questions([q],[doc("a"),doc("b")],{"a"})
    assert repaired==[] and excluded[0]["reason"]=="no_answer_has_available_equivalent_contract_record"
