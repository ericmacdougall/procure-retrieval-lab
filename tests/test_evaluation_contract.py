import pathlib
import sys
import pytest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
from harness import evaluate


def question(qid="q"):
    return dict(id=qid,gold_doc_ids=["d"])


def test_missing_ranking_is_not_silently_dropped():
    with pytest.raises(ValueError,match="length"):
        evaluate([question("a"),question("b")],[[('d',1.)]])


def test_duplicate_question_id_cannot_inflate_or_overwrite_denominator():
    with pytest.raises(ValueError,match="unique"):
        evaluate([question(),question()],[[('d',1.)],[('d',1.)]])


@pytest.mark.parametrize("rank",[[('d',1.),('d',.5)],[('d',float('nan'))],[('d',float('inf'))]])
def test_duplicate_or_nonfinite_ranking_is_rejected(rank):
    with pytest.raises(ValueError):
        evaluate([question()],[rank])


def test_equivalent_notice_satisfies_fact_without_rewarding_redundant_copies():
    q=dict(id="q",gold_doc_ids=["a","b"],relevance_groups=[["a","a2"],["b","b2"]])
    first=evaluate([q],[[('a2',4.),('a',3.),('b2',2.)]])[0]["q"]
    assert first["recall@1"]==.5 and first["recall@5"]==1.
    assert first["ndcg@10"]==1.
    only_one=evaluate([q],[[('a2',4.),('a',3.)]])[0]["q"]
    assert only_one["recall@5"]==.5 and only_one["ndcg@10"]<1.
