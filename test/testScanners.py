#!/usr/local/lcls/package/python/current/bin/python
"""
# Used to test the scanner objects from scannerThreads.py
#
# TMC, 4/22/16
"""
import numpy as np
import scannerThreads as s
def test():
        """ Functino to test GP """
        pvs = ["SIOC:SYS0:ML00:CALCOUT000","SIOC:SYS0:ML00:CALCOUT999","SIOC:SYS0:ML00:CALCOUT998","SIOC:SYS0:ML00:CALCOUT997"]
        det = "GDET:FEE1:241:ENRCHSTBR"
        GPS = s.GpScanner(parent=None)
        GPS.daemon = True
        GPS.setup(pvs,det)
        #GPS.start()
        #GPS.run()

if __name__ == "__main__":
        test()
