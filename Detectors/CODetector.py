from EventDetector import EventDetector
from ExampleBuilders.PhraseTriggerExampleBuilder import PhraseTriggerExampleBuilder
from ExampleWriters.PhraseTriggerExampleWriter import PhraseTriggerExampleWriter

class CODetector(EventDetector):
    def __init__(self):
        EventDetector.__init__(self)
        self.triggerDetector.exampleBuilder = PhraseTriggerExampleBuilder
        self.triggerDetector.exampleWriter = PhraseTriggerExampleWriter()