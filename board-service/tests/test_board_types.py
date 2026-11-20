import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

SERVICE = Path(__file__).resolve().parents[1]
RESEARCH = "FACT,OBSERVED,FAIL,TASK,DONE,KEY,VERIFIED,CHALLENGE,ALTERNATIVE,REPORT"
PROBE = """
import json, sys
sys.path.insert(0, sys.argv[1])
from shared_lessons import TYPES
from verifier import verify_note
notes = json.loads(sys.argv[2])
print(json.dumps({"types": TYPES, "results": [verify_note(note) for note in notes]}))
"""


def probe(types, *notes):
    env = {k: v for k, v in os.environ.items() if k != "BOARD_TYPES"}
    if types is not None:
        env["BOARD_TYPES"] = types
    run = subprocess.run([sys.executable, "-c", PROBE, str(SERVICE), json.dumps(notes)],
                         env=env, capture_output=True, text=True)
    if run.returncode != 0:
        raise AssertionError(run.stderr)
    return json.loads(run.stdout)


class BoardTypesTest(unittest.TestCase):
    def test_default_board_keeps_its_five_types(self):
        result = probe(None, {"type": "CLAIM", "content": "x"}, {"type": "TASK", "content": "t1 worker2 isolated: x"})
        self.assertEqual(result["types"], ["FACT", "OBSERVED", "FAIL", "CLAIM", "PATCH_SUMMARY"])
        self.assertEqual(result["results"], [[{"type": "CLAIM", "content": "x"}, "ok:1/1"], [None, "ok:0/1"]])

    def test_research_board_takes_its_types_and_checks_their_form(self):
        cases = [
            ({"type": "TASK", "content": "t1 worker2 isolated: H100 prices"}, True),
            ({"type": "TASK", "content": "t12 team-worker3 collaborative: settle G4"}, True),
            ({"type": "TASK", "content": "worker2: H100 prices"}, False),
            ({"type": "TASK", "content": "t1 worker2 alone: H100 prices"}, False),
            ({"type": "DONE", "content": "t1: 3 prices"}, True),
            ({"type": "DONE", "content": "done with prices"}, False),
            ({"type": "KEY", "content": "G41: the rental figure"}, True),
            ({"type": "VERIFIED", "content": "G41: quote found"}, True),
            ({"type": "CHALLENGE", "content": "the quote is wrong"}, False),
            ({"type": "ALTERNATIVE", "content": "G41: $2.49"}, True),
            ({"type": "REPORT", "content": "v1: first", "detail": "# Report\n"}, True),
            ({"type": "REPORT", "content": "v1: first"}, False),
            ({"type": "REPORT", "content": "first", "detail": "# Report\n"}, False),
            ({"type": "FACT", "content": "Lambda H100 $2.99"}, True),
            ({"type": "CLAIM", "content": "prices"}, False),
        ]
        result = probe(RESEARCH, *(note for note, _ in cases))
        self.assertEqual(result["types"], RESEARCH.split(","))
        for (note, admitted), (clean, reason) in zip(cases, result["results"]):
            with self.subTest(note=note):
                self.assertEqual(clean is not None, admitted, reason)
        reasons = dict(zip([n["content"] for n, _ in cases], [r for _, r in result["results"]]))
        self.assertIn("TASK must read `t<n> worker<n> isolated:", reasons["worker2: H100 prices"])
        self.assertEqual(reasons["v1: first"], "REPORT needs the whole report in `detail`")

    def test_unknown_types_stop_the_service(self):
        with self.assertRaises(AssertionError) as caught:
            probe("FACT,NOTE")
        self.assertIn("unknown board type(s) in BOARD_TYPES: NOTE", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
