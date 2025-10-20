import logging

from modules.voice_coach.coach import VoiceCoach


def test_coach_logs_message(caplog):
    logger = logging.getLogger("test.voice_coach")
    coach = VoiceCoach(tone="gentle", logger=logger)
    with caplog.at_level(logging.INFO, logger="test.voice_coach"):
        result = coach.coach("Chop onions")
    assert result == "Just a tip: Chop onions"
    assert result in caplog.text

