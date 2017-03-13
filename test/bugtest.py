#!/usr/local/lcls/package/python/current/bin/python
#
# Mitches script to debug ocelot where model parameters fail to load
#
# TMC, 4/22/16
#
import numpy as np
import pandas as pd
import scipy
import scipy.io

seed_file = 'simSeed.mat'
hyp_file = 'simHyps'

from GP.GPtools import *
from GP.OnlineGP import OGP
import GP.BayesOptimization as BOpt
from scannerThreads import GpScanner
from scannerThreads import GpInterfaceWrapper
from mint.lcls_interface import LCLSMachineInterface, LCLSDeviceProperties

def testFunc():

        """ Function to try and find a bug in the model load function """

        numBV = 50
        xi = .01
        bnds = None

        thing = GpScanner()
        pvs = ["SIOC:SYS0:ML00:CALCOUT000","SIOC:SYS0:ML00:CALCOUT999","SIOC:SYS0:ML00:CALCOUT998","SIOC:SYS0:ML00:CALCOUT997"]

        #thing.setup(pvs, 'GDET:FEE1:241:ENRCHSTBR')
        thing.pvs = pvs
        thing.objective_func_pv = 'GDET:FEE1:241:ENRCHSTBR'
        total_delay = .2
        mi = LCLSMachineInterface()
        mi.setUpDetector(pvs,detector=thing.objective_func_pv)
        mi.setup_data_record(pvs)
        dp = LCLSDeviceProperties()
        dp.get_start_values(pvs)
        interface = GpInterfaceWrapper(pvs,mi,dp,total_delay)
        s_data = thing.loadSeedData(thing.seed_file)

        hyps = thing.loadHyperParams(thing.hyp_file)
        thing.model = OGP(len(pvs),hyps,maxBV=50)

        filename = '/u1/lcls/matlab/data/2016/2016-04/2016-04-25/OcelotScan-2016-04-25-181811.mat'
        model_file = scipy.io.loadmat(filename)['data']
        thing.model.alpha        = model_file['alpha'].flatten(0)[0]
        thing.model.C            = model_file['C'].flatten(0)[0]
        thing.model.BV           = model_file['BV'].flatten(0)[0]
        thing.model.covar_params = model_file['covar_params'].flatten(0)[0]
        thing.model.KB           = model_file['KB'].flatten(0)[0]
        thing.model.KBinv        = model_file['KBinv'].flatten(0)[0]
        thing.model.weighted     = model_file['weighted'].flatten(0)[0]

        thing.model.covar_params = (thing.model.covar_params[0][0], thing.model.covar_params[1][0])
        print type(thing.model.covar_params)
        print thing.model.covar_params
        thing.model.predict(np.array(s_data[0,:-1],ndmin=2))

        thing.opt = BOpt.BayesOpt(thing.model,interface,prior_data=pd.DataFrame(s_data))

if __name__ == "__main__":
        testFunc()
