from ExampleWriters.ModifierExampleWriter import ModifierExampleWriter
from Detectors.KerasTokenDetector import KerasTokenDetector

class KerasModifierDetector(KerasTokenDetector):
    def __init__(self):
        KerasTokenDetector.__init__(self)
        self.tag = "modifier-"
        self.exampleType = "entity"
        self.useNonGiven = True
        self.defaultExtra = {"xtype":"task3", "t3type":"multiclass"}
        self.exampleWriter = ModifierExampleWriter()
    
    def getEntityTypes(self, entities, useNeg=False):
        types = set()
        entityIds = set()
        assert len(entities) == 1
        for entity in entities:
            if entity.get("negation") == "True":
                types.add("negation")
            if entity.get("speculation") == "True":
                types.add("speculation")
            entityIds.add(entity.get("id"))
        if len(types) == 0 and useNeg:
            types.add("neg")
        return sorted(types), sorted(entityIds)