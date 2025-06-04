class VoiceCoach:
    def __init__(self, tone: str = "neutral"):
        self.tone = tone

    def coach(self, message: str) -> str:
        if self.tone == "gentle":
            prefix = "Just a tip: "
        elif self.tone == "direct":
            prefix = "Heads up: "
        else:
            prefix = ""
        output = prefix + message
        print(output)
        return output
