import unittest

from yt2feishu.captions import format_timestamp, parse_json3, parse_vtt


class CaptionParsingTests(unittest.TestCase):
    def test_parse_json3_dedupes_and_cleans_text(self):
        payload = """
        {
          "events": [
            {"tStartMs": 1000, "dDurationMs": 500, "segs": [{"utf8": "Hello"}, {"utf8": " world"}]},
            {"tStartMs": 1500, "dDurationMs": 500, "segs": [{"utf8": "Hello world"}]},
            {"tStartMs": 2000, "dDurationMs": 500, "segs": [{"utf8": "<b>Next</b> line"}]}
          ]
        }
        """

        cues = parse_json3(payload)

        self.assertEqual([cue.text for cue in cues], ["Hello world", "Next line"])
        self.assertEqual(cues[0].start_ms, 1000)

    def test_parse_vtt_reads_timestamped_cues(self):
        payload = """WEBVTT

00:00:01.000 --> 00:00:02.000
<c>Hello</c> there

00:00:03.500 --> 00:00:04.000
Next&nbsp;cue
"""

        cues = parse_vtt(payload)

        self.assertEqual([cue.text for cue in cues], ["Hello there", "Next cue"])
        self.assertEqual(cues[1].start_ms, 3500)

    def test_format_timestamp_uses_short_form_before_one_hour(self):
        self.assertEqual(format_timestamp(65_000), "01:05")
        self.assertEqual(format_timestamp(3_665_000), "01:01:05")


if __name__ == "__main__":
    unittest.main()

