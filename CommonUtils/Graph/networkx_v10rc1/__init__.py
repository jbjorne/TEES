# Since networkx is an integral part of many programs, and its interface
# and functionality can change between releases, it is added here so that
# programs can import explicitly the version they need. A networkx already
# installed as part of the python installation should not affect using
# this alternative version.

# Importing should work like this: import Graph.networkx_v10rc1 as nx

import sys, os

# NetworkX imports itself. Even though manipulating the path causes
# this wrapper to make networkx load modules for this specific version,
# if networkx is already loaded, these modules might fail to load.
# Therefore, networkx is first removed from the list of modules
for key in sorted(sys.modules.keys()):
    if key[0:8] == "networkx":
        del sys.modules[key]

# Manipulate path to make sure that networkx's own internal imports
# will import stuff from the networkx subdirectory located in this
# directory.
thispath = os.path.split(os.path.abspath(__file__))[0] # current path
sys.path = [thispath] + sys.path # add to system path
from networkx import * # get everything from networkx
sys.path = sys.path[1:] # back to original path

# NetworkX imports itself. This may interfere with using another version
# of the library, so remove all of these imports
#for key in sorted(sys.modules.keys()):
#    if key[0:8] == "networkx":
#        del sys.modules[key]