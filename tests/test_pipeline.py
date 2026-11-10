"""Pipeline unit tests on tiny synthetic documents: chunking, BM25, fusion, rewrite."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from chunking import windows, chunk_doc
from bm25 import BM25
import fusion
from rewrite import rewrite


def doc(i, title, desc="x " * 10):
    return dict(doc_id="D%d" % i, title=title, buyer="Buyer", suppliers=["Sup"], n_awards=1, amounts=[10.0], total_value=10.0,
                currency="GBP", award_date="2024-01-01", contract_start="2024-02-01", contract_end=None, category="goods",
                cpv_text="", method="", description=desc)


def test_windows_cover_and_overlap():
    w = windows(list(range(10)), 4, 2)
    assert w[0] == [0, 1, 2, 3] and w[1] == [2, 3, 4, 5] and w[-1][-1] == 9
    assert windows(list(range(3)), 4, 2) == [[0, 1, 2]]


def test_field_chunks_have_title_prefix():
    ch = chunk_doc(doc(1, "Road salt"), mode="field")
    assert [g for g, _ in ch] == ["head", "body", "terms"]
    assert ch[1][1].startswith("Title: Road salt.")


def test_bm25_ranks_matching_doc_first():
    texts = ["road salt winter supply", "school catering services", "software licences renewal"]
    bm = BM25(texts)
    s = bm.scores("salt supply")
    assert s.argmax() == 0 and s[1] == 0 and s[2] == 0


def test_rrf_known_values():
    a = [("x", 3), ("y", 2)]
    b = [("y", 9), ("x", 1)]
    f = dict(fusion.rrf([a, b], k=60))
    assert abs(f["x"] - (1 / 61 + 1 / 62)) < 1e-12 and abs(f["y"] - (1 / 62 + 1 / 61)) < 1e-12
    w = fusion.weighted([a, b], [1.0, 0.0])
    assert w[0][0] == "x"


def test_rewrite_strips_boilerplate():
    assert rewrite("What was the awarded value of the contract 'Road salt' from Council X?") == "road salt from council x"
