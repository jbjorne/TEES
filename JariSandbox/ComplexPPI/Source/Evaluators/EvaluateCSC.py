if __name__=="__main__":
    import sys, os
    sys.path.append("..")
    from Utils.ProgressCounter import ProgressCounter
    from Utils.Parameters import splitParameters
    from optparse import OptionParser
    import Core.ExampleUtils as ExampleUtils
    from Core.IdSet import IdSet
    import Utils.TableUtils as TableUtils
    optparser = OptionParser(usage="%prog [options]\nCalculate f-score and other statistics.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Input file in csv-format", metavar="FILE")
    optparser.add_option("-p", "--parameters", default=None, dest="parameters", help="Input file in csv-format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file for the statistics")
    optparser.add_option("-e", "--evaluator", default="BinaryEvaluator", dest="evaluator", help="Prediction evaluator class")
    (options, args) = optparser.parse_args()
    
    # Read input data
    fieldnames = ["class","prediction","id","fold","c"]
    rows = TableUtils.readCSV(options.input, fieldnames)
    folds = sorted(list(TableUtils.getValueSet(rows, "fold")))
    for fold in folds:
        foldRows = TableUtils.selectRowsCSV(rows, {"fold":fold})
        cParameters = sorted(list(TableUtils.getValueSet(foldRows, "c")))
        for cParameter in cParameters:
            paramRows = TableUtils.selectRowsCSV(rows, {"c":cParameter})
            evaluator = Evaluator.calculateFromCSV(paramRows)
            (cParameter, evaluator)