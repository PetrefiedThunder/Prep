import logging

from modules.voice_coach.coach import VoiceCoach


def test_voice_coach_logs_output(caplog):
    coach = VoiceCoach(tone="gentle")
    with caplog.at_level(logging.INFO):
        output = coach.coach("Keep chopping")
    assert output == "Just a tip: Keep chopping"
    assert "Just a tip: Keep chopping" in caplog.text
