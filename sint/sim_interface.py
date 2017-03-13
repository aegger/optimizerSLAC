# -*- coding: utf-8 -*-
"""
simulation interface

based on LCLSMachineInterface - Machine interface file for the LCLS to ocelot optimizer

"""

import numpy as np
#import epics
import time
import sys
import math
from corrplot_interface import CorrplotInterface


class SimulationInterface:
    """ Start acquisition interface class """

    #_____________________________________________
    def __init__(self, corrplot_path = '/u1/lcls/matlab/data/2016/2016-10/2016-10-20/CorrelationPlot-QUAD_IN20_511_BCTRL-2016-10-20-053315.mat'):
	""" Initialize parameters for the scanner class. """
	self.secs_to_ave = 2         #time to integrate gas detector
	
	self.nsamples = 120;
	self.simmode = 1; # 0: binormal distribution
			  # 1: correlation plot fit
	self.corrplot_path = corrplot_path;
	
	#if(self.simmode == 1 or True):
	self.sim = CorrplotInterface(self.corrplot_path)
	self.getter = self     #getter class for channel access
	self.pvs = self.sim.pvs # pv names stored here
	self.detector = self.pvs[-1]
	
	# reference for goal
	self.pvs_optimum_value = np.array([self.sim.mean_xm, self.sim.mean_ym, self.sim.mean_amp])
	self.detector_optimum_value = self.pvs_optimum_value[-1]
    
    
    ############################################################
    # main public member functions
    
    
    #_____________________________________________
    # Get fcn takes 1 pv string or a list of pvs
    # In a real machine setting, this fcn should check the machine status before returning values
    def get_value(self, variable_names):
    
        # if a list of names, return a list of values
        #if hasattr(variable_names, '__iter__'):
        #    print 'getting a value', self.sim.get1(var)
        #    return np.array([self.sim.get1(var) for var in variable_names])
        #return self.sim.get1(var)    
        # if one variable, return one value
        #else:
        return self.sim.get1(variable_names)
    
    #_____________________________________________
    # Get fcn takes 1 pv string or a list of pvs
    # In a real machine setting, this fcn should check the machine status and wait for devices to settle before returning values
    def set_value(self, variable_names, values):
        
        # if a list of names, return a list of values
        #if hasattr(variable_names, '__iter__') and hasattr(values, '__iter__'):
        #    if len(variable_names) == len(values):
        #        for i in range(len(variable_names)):
        #            self.sim.set1(variable_names[i], values[i])
        #    else:
        #        print "SimulationInterface.get - ERROR: Inputs must have same number of entries."
        #    
        #elif hasattr(variable_names, '__iter__') or hasattr(values, '__iter__'):
        #    print "SimulationInterface.get - ERROR: Inputs must both be listable."
        
        # if one variable, set one value
        #else:
        #    print 'setting a value', values
        self.sim.set1(variable_names, values)
    
    #def initErrorCheck(self): # not needed (call errorCheck or something or do this in the setup from the constructor
	    #"""
	    #Initialize PVs and setting used in the errorCheck method.
	    #"""
	    #return

    def get(self, pv):
        #return self.get_value(pv)
        print 'getting', pv, self.sim.get1(pv)
        return self.sim.get1(pv)

    def get_energy(self):
        return 7

    def put(self, pv, val):
        print 'setting', pv, self.sim.set1(pv, val)

    def errorCheck(self):
    #def get_status(self): # how is errorCheck used? maybe you want a get_status fcn instead: OK, WAIT, BREAK
	    """
	    Method that check the state of BCS, MPS, Gaurdian, UND-TMIT and pauses GP if there is a problem.
	    """
	    return

    #def get_sase(self):
    #def get_objective(self, nsamples = 100, returnErrorQ = False): # where is it best to set this up?
    def get_sase(self, data, points = None, returnErrorQ = False):
	    """
	    Returns an average for the objective function from the selected detector PV.

	    Args:
		    nsamples (int): integer number of samples to average over
		    returnErrorQ (bool): option to return stdev too

	    Returns:
		    Float of detector measurment mean (and optionally standard deviation)
		    
            Ideas:  - option to do median & median deviation
                    - perhaps we'd prefer to specify a precision tolerance? i.e. sample until abs(mean(data[-n:]) - mean(data[-(n-1):])) / std(data[-n:]) < tolerance  or  abs(data[-n] / n) / std(data) < tolerance
            
	    """
	    
	    # acquire data
	    #data = np.array([self.get_value(self.detector) for i in range(nsamples)])
	    
	    # perform stats
            try:
                datamean = np.mean(data)
                datadev  = np.std(data)
            except:
                datamean = data
                datadev = data
            print datamean, datadev
            
            # record stats
	    #self.record_data(datamean,datadev) # do we want the ctrl interface to record?
	    
	    # return stats
	    if returnErrorQ:
                return np.array([datamean, datadev])
            else:
                return datamean, datadev
    
    def get_limits(self, device,percent=0.25):
	    """ 
	    Function to get device limits.
	    Executes on every iteration of the optimizer function evaluation.
	    Currently does not work with the normalization scheme.
	    Defaults to + 25% of the devices current values.

	    Args:
		    device (str): PV name of the device to get a limit for
		    percent (float): Generates a limit based on the percent away from the devices current value
	    """
	    #val = self.start_values[device]
	    #tol = abs(val*percent)
	    #lim_lo = val-tol
	    #lim_hi = val+tol
	    #limits = [lim_lo,lim_hi]
	    #print device, 'LIMITS ->',limits
	    #return limits
	    #Dosnt work with normalizaiton, big limits
	    return [-10000,10000] # looks like this function doesn't do anything


    # looks redundant
    #def get_start_values(self,devices,percent=0.25):
	    #"""
	    #Function to initialize the starting values for get_limits methomethodd.

	    #Called from tuning file or GUI

	    #Args:
		    #devices ([str]): PV list of devices
		    #percent (float): Percent around the mean to generate limits

	    #"""
	    #self.start_values={}
	    #self.norm_minmax={}
	    #for d in devices:
		    #val = self.getter.caget(str(d))
		    #self.start_values[str(d)] = val
		    #tol = abs(val*percent)
		    #lim_lo = val-tol
		    #lim_hi = val+tol
		    #limits = [lim_lo,lim_hi]
		    #self.norm_minmax[str(d)] = [lim_lo,lim_hi]

