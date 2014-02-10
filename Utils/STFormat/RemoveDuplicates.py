import sys

def removeDuplicateEvents(document):
#     eventMap = {}
#     for event in document.events:
#         if event.id in eventMap:
#             raise Exception("Duplicate id " + str(event.id) + " in document " + str(document.id))
#         eventMap[event.id] = event
    modified = True
    while modified:
        modified = False
        
        # Find duplicates
        duplicateOf = {}
        eventByContent = {} 
        for event in document.events:
            content = event.toString().split("\t", 1)[1]
            if content in eventByContent:
                print >> sys.stderr, "Removing duplicate ST event " + event.id + " " + content + " from document " + str(document.id)
                duplicateOf[event] = eventByContent[content]
            else:
                eventByContent[content] = event
        
        if len(duplicateOf) == 0:
            break
            
        # Remove events
        eventsToKeep = []
        for event in document.events:
            if event not in duplicateOf:
                eventsToKeep.append(event)
            else:
                modified = True
        document.events = eventsToKeep
        
        # Re-map arguments
        for event in document.events:
            for argument in event.arguments:
                if argument.target in duplicateOf:
                    argument.target = duplicateOf[argument.target]
                    modified = True
    