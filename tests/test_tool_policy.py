import pathlib
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
from tool_policy import ToolPolicy


def docs():
    return [dict(doc_id="old",title="Road salt",buyer="Council A",suppliers=["Supplier X"],award_date="2023-01-01"),
            dict(doc_id="new",title="Road salt",buyer="Council A",suppliers=["Supplier Y"],award_date="2024-01-01")]


def test_supplier_identity_disambiguates_duplicate_title():
    policy=ToolPolicy(docs())
    route,ranking=policy.route("Value of 'Road salt' for Council A, awarded to Supplier Y?")
    assert route=="structured" and [d for d,_ in ranking]==["new"]


def test_absent_exact_title_abstains_instead_of_guessing():
    policy=ToolPolicy(docs())
    assert policy.route("Value of 'Missing contract' from Council A?")==("abstain",[])


def test_description_question_routes_to_retrieval():
    policy=ToolPolicy(docs())
    assert policy.route("Who is buying maintenance for a large fleet?")==("retrieve",None)


def test_date_disambiguates_without_seeing_labels():
    policy=ToolPolicy(docs())
    route,ranking=policy.route("Who won 'Road salt' for Council A on 2024-01-01?")
    assert route=="structured" and [d for d,_ in ranking]==["new"]
