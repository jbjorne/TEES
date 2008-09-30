class Evaluator:
    def compare(self, evaluator):
        raise NotImplementedError
    
    def average(evaluators):
        raise NotImplementedError
    average = staticmethod(average)
    
    def pool(evaluators):
        raise NotImplementedError
    pool = staticmethod(pool)
    
    def _calculate(self, predictions):
        raise NotImplementedError
    
    def toStringConcise(self, indent="", title=None):
        raise NotImplementedError
    
    def toDict(self):
        raise NotImplementedError
    
    def saveCSV(self, filename):
        raise NotImplementedError