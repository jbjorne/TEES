from ExampleWriters.EntityExampleWriter import EntityExampleWriter
from Detectors.KerasTokenDetector import KerasTokenDetector

class KerasEntityDetector(KerasTokenDetector):
    def __init__(self):
        KerasTokenDetector.__init__(self)
        self.tag = "entity-"
        self.useNonGiven = False
        self.defaultExtra = {"xtype":"token"}
        self.exampleWriter = EntityExampleWriter()
    
    def getEntityTypes(self, entities, useNeg=False):
        types = set()
        entityIds = set()
        for entity in entities:
            eType = entity.get("type")
            if entity.get("given") == "True" and self.styles.get("all_tokens"):
                continue
            if eType == "Entity" and self.styles.get("genia_task1"):
                continue
            else:
                types.add(eType)
                entityIds.add(entity.get("id"))
        if len(types) == 0 and useNeg:
            types.add("neg")
        return sorted(types), sorted(entityIds)