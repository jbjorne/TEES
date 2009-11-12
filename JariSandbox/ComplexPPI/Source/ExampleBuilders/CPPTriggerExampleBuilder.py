import subprocess
import Settings

# Wrapper for the C++ version
class CPPTriggerExampleBuilder:
    @classmethod
    def run(cls, input, output, parse, tokenization, style, idFileTag=None, gazetteer=None):
        args = []
        args += [Settings.CPPTriggerExampleBuilder]
        args += ["-i", input]
        args += ["-o", output]
        args += ["-c", idFileTag + ".class_names" ]
        args += ["-f", idFileTag + ".feature_names" ]
        args += ["-p", parse ]
        args += ["-t", tokenization ]
        print args
        rv = subprocess.call(args)
        assert(rv == 0)