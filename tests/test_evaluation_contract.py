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
