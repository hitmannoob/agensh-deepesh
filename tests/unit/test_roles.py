from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agensh import roles  # noqa: E402


def entry(gid, kind, author, content):
    return {'_label': f'G{gid}', 'type': kind, 'thread_id': f'team-worker{author}', 'content': content}


class RolesTest(unittest.TestCase):
    def test_one_reviewer_per_four_workers_from_the_end(self):
        self.assertEqual([roles.reviewers(n) for n in (2, 3, 4, 7, 8, 12)],
                         [[], [3], [4], [7], [7, 8], [10, 11, 12]])
        self.assertEqual(roles.builders(2), [2])
        self.assertEqual(roles.builders(4), [2, 3])
        self.assertEqual(roles.builders(8), [2, 3, 4, 5, 6])

    def test_task_names_a_worker_by_number_or_full_name(self):
        self.assertEqual(roles.task_worker('t1 worker3 isolated: prices', 4), 3)
        self.assertEqual(roles.task_worker('t2 team-worker2 collaborative: settle G4', 4), 2)
        self.assertIsNone(roles.task_worker('t3 worker9 isolated: prices', 4))
        self.assertIsNone(roles.task_worker('t4 worker1 isolated: prices', 4))
        self.assertIsNone(roles.task_worker('prices for worker2', 4))

    def test_wakeups_route_entries_to_who_acts_on_them(self):
        entries = [
            entry(1, 'TASK', 1, 't1 worker2 isolated: prices'),
            entry(2, 'FACT', 2, 'Lambda H100 $2.99'),
            entry(3, 'DONE', 2, 't1: 3 prices'),
            entry(4, 'KEY', 1, 'G2: rental figure'),
            entry(5, 'CHALLENGE', 4, 'G2: wrong SKU'),
            entry(6, 'ALTERNATIVE', 3, 'G2: $2.49'),
            entry(7, 'VERIFIED', 4, 'G2: quote found'),
            entry(8, 'TASK', 1, 't2 worker3 collaborative: settle G2'),
        ]
        notices = roles.wakeups(entries, 4, after=0)
        self.assertEqual({worker: [label for _, label, _, _ in items] for worker, items in notices.items()},
                         {2: ['G1'], 1: ['G3', 'G5', 'G6'], 4: ['G4'], 3: ['G8']})
        self.assertEqual(roles.wakeups(entries, 4, after=7), {3: [('TASK', 'G8', 'team-worker1',
                                                                   't2 worker3 collaborative: settle G2')]})
        self.assertEqual(roles.last_label(entries), 8)

    def test_without_reviewers_key_claims_go_to_the_builders(self):
        notices = roles.wakeups([entry(1, 'KEY', 1, 'G9: the answer')], 2, after=0)
        self.assertEqual(list(notices), [2])

    def test_no_one_is_woken_by_their_own_entry(self):
        notices = roles.wakeups([entry(1, 'DONE', 1, 't1: done'), entry(2, 'KEY', 4, 'G1: x')], 4, after=0)
        self.assertEqual(notices, {})


if __name__ == '__main__':
    unittest.main()
