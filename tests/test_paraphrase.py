import pathlib
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
import paraphrase


def test_named_entity_copy_does_not_fail_semantic_rewording():
    q=dict(slice="paraphrase-heavy",must_keep=[],text_template="Which contract notice covers this requirement: The Department of Health and Social Care has appointed a contractor to survey staff")
    p="Which notice concerns the Department of Health and Social Care hiring a specialist to question its workforce?"
    assert paraphrase.validate(q,p)==[]


def test_generic_requirement_copy_still_rejected():
    q=dict(slice="paraphrase-heavy",must_keep=[],text_template="Which contract notice covers this requirement: provide cleaning services for office buildings and routine maintenance across all sites")
    p="Find a notice to provide cleaning services for office buildings and routine maintenance across all sites."
    assert "copied_4gram" in paraphrase.validate(q,p)
