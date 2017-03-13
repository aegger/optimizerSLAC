#!/usr/local/lcls/package/python/current/bin/python
"""
# Used to quickly set the DEV pvs back to a reasonable value that matches LTU match quads values
#
# TMC, 4/18/16
"""
import epics
def setdevs():
        """ Set development PVs so values are close to the quads """

        #q1,q2,q3,q4 = (epics.caget("QUAD:LTU1:620:BCTRL"),epics.caget("QUAD:LTU1:640:BCTRL"),epics.caget("QUAD:LTU1:660:BCTRL"),epics.caget("QUAD:LTU1:680:BCTRL"))

        q1 = -79.7640302
        q2 = 79.67962984
        q3 = -83.36844826
        q4 = 68.4844249

        print q1,q2,q3,q4

        epics.caput("SIOC:SYS0:ML00:CALCOUT997",q1) # QUAD:LTU1:620:BCTRL
        epics.caput("SIOC:SYS0:ML00:CALCOUT998",q2) # QUAD:LTU1:640:BCTRL
        epics.caput("SIOC:SYS0:ML00:CALCOUT999",q3) # QUAD:LTU1:660:BCTRL
        epics.caput("SIOC:SYS0:ML00:CALCOUT000",q4) # QUAD:LTU1:680:BCTRL

if __name__ == "__main__":
        setdevs()
