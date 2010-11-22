def validateREL(documents):
    for document in documents:
        if len(document.events) > 0:
            print >> sys.stderr, "Warning, events for REL task"
        for relation in relations:
            assert len(relation.arguments) == 2
            pass