import logging

from modules.voice_coach.coach import VoiceCoach


def test_voice_coach_logs_output(caplog):
    coach = VoiceCoach(tone="gentle")
    with caplog.at_level(logging.INFO):
        output = coach.coach("Keep chopping")
    assert output == "Just a tip: Keep chopping"
    assert "Just a tip: Keep chopping" in caplog.text
def test_coach_logs_message(caplog):
    logger = logging.getLogger("test.voice_coach")
    coach = VoiceCoach(tone="gentle", logger=logger)
    with caplog.at_level(logging.INFO, logger="test.voice_coach"):
        result = coach.coach("Chop onions")
    assert result == "Just a tip: Chop onions"
    assert result in caplog.text

