from EventDetector import EventDetector
from ExampleBuilders.PhraseTriggerExampleBuilder import PhraseTriggerExampleBuilder
from ExampleWriters.PhraseTriggerExampleWriter import PhraseTriggerExampleWriter

class CODetector(EventDetector):
    """
    A specialized EventDetector for the CO-task. The CODetector predicts
    triggers that consist of a phrase, as opposed to the normal EventDetector
    that detects triggers that consist of only a single word.
    """
    def __init__(self):
        EventDetector.__init__(self)
        self.triggerDetector.exampleBuilder = PhraseTriggerExampleBuilder
        self.triggerDetector.exampleWriter = PhraseTriggerExampleWriter()