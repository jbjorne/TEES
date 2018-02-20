from ExampleWriters.EntityExampleWriter import EntityExampleWriter
from Detectors.KerasTokenDetector import KerasTokenDetector
import Utils.InteractionXML.ResolveEPITriggerTypes

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
            if entity.get("given") == "True" and self.styles.get("all_tokens"):
                continue
            
            eType = entity.get("type")
            if eType == "Entity" and self.styles.get("genia_task1"):
                continue
            elif self.styles.get("epi_merge_negated"):
                types.add(Utils.InteractionXML.ResolveEPITriggerTypes.getEPIBaseType(eType))
            else:
                types.add(eType)
            entityIds.add(entity.get("id"))
        if len(types) == 0 and useNeg:
            types.add("neg")
        return sorted(types), sorted(entityIds)