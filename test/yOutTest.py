#!/usr/local/lcls/package/python/current/bin/python
"""
This file is used to generate a y(t) function that feeds into ocelot
Used to test optimization algs on a function
Can do different function like sqrt(t), t**2, or whatever

TMC, 4/25/16
"""
import epics
import numpy as np
import time
import math
import matplotlib.pyplot as plt

def func(t):
        """ Returns t evaluated at a function """
        offset = epics.caget("SIOC:SYS0:ML00:CALCOUT992")
        #out = offset+math.sqrt(t)
        #out = offset+((t**2)-(t**3))*2
        out = offset+t
        noise = (np.random.random()-0.5)/2
        #out = out+noise
        return out

def loop():
        
        """
        Runs a loop over a vector
        Evaluates the vec[i] with func(t) and sets the output ot a PV
        """
        pv = "SIOC:SYS0:ML00:CALCOUT993"
        iters = 1500
        vec = np.linspace(0,400,iters)
        val_out = []
        t = 0.1
        for i in range(iters):
                val = func(vec[i])
                pc = round(float(i)/iters,2)*100
                print pv,'->',val,'---',pc
                val_out.append(val)
                epics.caput(pv,val)
                time.sleep(t)

        return val_out

if __name__ == "__main__":
        loop()
