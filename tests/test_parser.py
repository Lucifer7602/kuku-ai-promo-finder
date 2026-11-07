import unittest
from promofinder.parser import parse_screenplay, to_seconds, to_timestamp
from promofinder.scorer import score_window

SAMPLE = '''EPISODE NUMBER: Episode 1
EPISODE LOGLINE: A fictional bride discovers a secret.
CONTINUITY NOTES: Synthetic test only.
--- SCRIPT START ---
SCENE 01
Scene start: 00:00.00
Scene end: 00:40.00
**CAMERA:**
Start: (00:00.00) | End: (00:03.00)
A door bursts open in a dramatic reveal.

**ACTION:**
Start: (00:00.00) | End: (00:03.00)
A guard rushes into the room and points a sword.

**HEROINE (Shocked):**
Start: (00:00.50) | End: (00:03.00)
"Who are you?"

**VILLAIN (Cold):**
Start: (00:36.00) | End: (00:39.00)
"You are not safe here."

**CAMERA:**
Start: (00:39.00) | End: (00:40.00)
The shot freezes on the locked door before a cut to black.
--- SCRIPT END ---
'''


class ParserTests(unittest.TestCase):
    def test_timestamp_roundtrip(self):
        self.assertAlmostEqual(to_seconds("01:02.50"), 62.5)
        self.assertEqual(to_timestamp(62.5), "01:02.50")

    def test_parses_episode_and_event_types(self):
        episodes = parse_screenplay(SAMPLE)
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0].number, 1)
        self.assertGreaterEqual(len(episodes[0].events), 4)
        self.assertIn("camera", {event.kind for event in episodes[0].events})
        self.assertIn("dialogue", {event.kind for event in episodes[0].events})

    def test_candidate_duration_constraints(self):
        episode = parse_screenplay(SAMPLE)[0]
        candidate = score_window(episode, 0.0, 40.0)
        self.assertIsNotNone(candidate)
        self.assertGreaterEqual(candidate.duration, 20.0)
        self.assertLessEqual(candidate.duration, 60.0)
        self.assertIsNone(score_window(episode, 0.0, 19.0))


if __name__ == "__main__":
    unittest.main()
