import sys, os
sys.path.append(os.path.normpath(os.path.abspath(os.path.dirname(__file__))+"/../.."))
import Utils.Settings as Settings
import Utils.Parameters as Parameters
import types
from UnixConnection import UnixConnection
from LSFConnection import LSFConnection
from SLURMConnection import SLURMConnection
#import LSF.LSFConnection

def getConnection(connection): #, account=None, workDirBase=None, remoteSettingsPath=None):
    if connection == None: # return a "dummy" local connection
        return getConnection("connection=Unix:jobLimit=1")
    elif type(connection) in types.StringTypes and hasattr(Settings, connection): # connection is a Settings key
        print >> sys.stderr, "Using connection", connection
        return getConnection(getattr(Settings, connection))
        #return getConnection(*getattr(Settings, connection))
    else: # connection is a parameter string or dictionary
        defaultParams = dict.fromkeys(["connection", "account", "workdir", "settings", "memory", "cores", "modules", "wallTime", "jobLimit", "preamble", "debug"])
        defaultParams["debug"] = False
        connection = Parameters.get(connection, valueListKey="connection", valueTypes={"debug":[bool]}, defaults=defaultParams)
        if connection["connection"] == None:
            connection["connection"] = "Unix"
        if connection["account"] == None:
            assert connection["workdir"] == None
            #assert remoteSettingsPath == None
            print >> sys.stderr, "New local connection", Parameters.toString(connection)
        else: 
            print >> sys.stderr, "New remote connection:", Parameters.toString(connection)
        # Make the connection
        exec "ConnectionClass = " + connection["connection"] + "Connection"
        connectionArgs = {}
        for key in connection:
            if key != "connection" and connection[key] != None:
                connectionArgs[key] = connection[key]
        return ConnectionClass(**connectionArgs)
#        if connection == "Unix":
#            return UnixConnection(account, workDirBase, remoteSettingsPath)
#        elif connection == "LSF":
#            return LSFConnection(account, workDirBase, remoteSettingsPath)
#        elif connection == "SLURM":
#            return SLURMConnection(account, workDirBase, remoteSettingsPath)
#        else:
#            assert False, connection
