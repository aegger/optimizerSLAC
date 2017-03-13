# -*- coding: utf-8 -*-
"""
Machine interface file for the LCLS to ocelot optimizer

Tyler Cope, 2016
"""

import numpy as np
import epics
import time
import sys
import math

class LCLSMachineInterface():
        """ Start machine interface class """

        def __init__(self):
                """ Initialize parameters for the scanner class. """
                self.secs_to_ave = 2         #time to integrate gas detector
		self.initErrorCheck() #Checks for errors and trimming

        #=================================================================# 
        # -------------- Original interface file functions -------------- #
        #=================================================================# 

	def initErrorCheck(self):
                """
                Initialize PVs and setting used in the errorCheck method.
                """
                #setup pvs to check
                self.error_bcs      = "BCS:MCC0:1:BEAMPMSV"
                self.error_mps      = "SIOC:SYS0:ML00:CALCOUT989"
                self.error_gaurdian = "SIOC:SYS0:ML00:AO466"
                self.error_und_tmit = "BPMS:UND1:3290:TMITTH"

                #pv to bypass the error pause
                self.error_bypass  = "SIOC:SYS0:ML00:CALCOUT990"
                self.error_tripped = "SIOC:SYS0:ML00:CALCOUT991"

                #set the unlatch pv to zero
                epics.caput(self.error_bypass, 0)
                epics.caput(self.error_tripped,0)	

	def errorCheck(self):
                """
                Method that check the state of BCS, MPS, Gaurdian, UND-TMIT and pauses GP if there is a problem.
                """
		while 1:
                        #check for bad state
			if epics.caget(self.error_bypass)     == 1:
				out_msg="Bypass flag is TRUE"
                        elif epics.caget(self.error_bcs)      != 1:
                                out_msg="BCS tripped"
                        elif epics.caget(self.error_mps)      != 0:
                                out_msg="MPS tripped"
                        elif epics.caget(self.error_gaurdian) != 0:
                                out_msg="Gaurdian tripped"
		
                        #elif epics.caget(self.error_und_tmit) < 5.0e7:
                        #        out_msg="UND Tmit Low"
                        else:
                                out_msg='Everything Okay'

                        #exit if the stop button is set
                        #if not self.mi.getter.caget("SIOC:SYS0:ML03:AO702"):
			if not epics.caget("SIOC:SYS0:ML03:AO702"):
                                break

                        #set the error check message
                        epics.caput ("SIOC:SYS0:ML00:CA000",out_msg)
                        print out_msg

                        #break out if error check is bypassed
                        if (out_msg=="Bypass flag is TRUE"):
                                break

                        #break out if everything is okay
                        if (out_msg=="Everything Okay"):
                                epics.caput(self.error_tripped,0)
                                break
				#return
                        else:
                                epics.caput(self.error_tripped,1)
                        time.sleep(0.1)

        def get_sase(self, datain, points=None):
                """
                Returns data for the ojective function (sase) from the selected detector PV.

                At lcls the repetition is  120Hz and the readout buf size is 2800.
                The last 120 entries correspond to pulse energies over past 1 second.

                Args:
                        seconds (float): Variable input on how many seconds to average data

                Returns:
                        Float of SASE or other detecor measurment
                """       
                try: #try to average over and array input
			dataout = np.mean(datain[-(points):])
			sigma   = np.std( datain[-(points):])
                except: #if average fails use the scaler input
                        print "Detector is not a waveform PV, using scalar value"
                        dataout = datain
                        sigma   = -1
                return dataout, sigma

	def get(self, pv):
		return epics.PV(str(pv), connection_timeout = 0.1).get()
	
	def put(self, pv, val):
		epics.caput(str(pv), val)

        def get_value(self, device_name):
                """
                Getter function for lcls.

                Args:
                        device_name (str): String of the pv name used in caget

                Returns:
                        Data from caget, variable data type depending on PV
                """
                return epics.caget(str(device_name))
        
        def set_value(self, device_name, val):
                """
                Setter function for lcls.
                
                Args:
                        device_name (str): String of the pv name used in caput 
                        val (variable): Value to caput to device, variable data type depending on PV
                """
                epics.caput(device_name, val)

		#mu = mu
		#sig = math.sqrt(abs(mu))
		#y = (float(x)-mu)/(sig)
			
	def get_energy(self):
                return epics.caget("BEND:DMP1:400:BDES")
            

        #=======================================================# 
        # -------------- Normalization functions -------------- #
        #=======================================================# 

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
		val = epics.caget(device)
                tol = (val*percent)
                lim_lo = val-tol
                lim_hi = val+tol
                limits = [lim_lo,lim_hi]
		return limits
    
        def get_start_values(self,devices,percent=0.25):
                """
                Function to initialize the starting values for get_limits method.

                Called from tuning file or GUI

                Args:
                        devices ([str]): PV list of devices
                        percent (float): Percent around the mean to generate limits

                """
                self.start_values={}
                self.norm_minmax={}
                for d in devices:
                        val = epics.caget(str(d))
                        self.start_values[str(d)] = val
                        tol = abs(val*percent)
                        lim_lo = val-tol
                        lim_hi = val+tol
                        limits = [lim_lo,lim_hi]
                        self.norm_minmax[str(d)] = [lim_lo,lim_hi]

