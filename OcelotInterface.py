#!/usr/local/lcls/package/python/current/bin/python
"""
Ocelot GUI, interface for running and testing accelerator optimization methods

This file primarily contains the code for the UI and GUI
The scanner classes are contained in an external file, scannerThreads.py
The resetpanel widget is also contained in a separate module, resetpanel

Tyler Cope, 2016
"""
#QT imports
from PyQt4.QtGui import QApplication, QFrame, QGraphicsWidget, QPixmap, QMessageBox
from PyQt4.QtCore import QTimer, QObject
from PyQt4 import QtGui, QtCore, Qt

#normal imports
import numpy as np
import sys
import os
import time
import pyqtgraph as pg
import pandas as pd

#Ocelot files
from mint.lcls_interface import LCLSMachineInterface
from mint.mint import OptControl, Optimizer, Action, GaussProcess, Simplex

#logbook imports
from re import sub
from xml.etree import ElementTree
from shutil import copy
from datetime import datetime
from os import system
import Image

#local imports
from mint.opt_objects import *
from mint import opt_objects as obj
import sint.corrplot_interface
from sint.sim_interface import SimulationInterface

#for command line options
import argparse

#GUI layout file
from UIOcelotInterface import Ui_Form

#slac python toolbox imports
import matlog

class OcelotInterfaceWindow(QFrame):
        """ Main class for the GUI application """
	def __init__(self):
                """ 
                Initialize the GUI and QT UI aspects of the application.
                Initialize the scan parameters.
                Connect start and logbook buttons on the scan panel.
                Initialize the plotting.
                Make the timer object that updates GUI on clock cycle durring a scan.
                """
		# initialize
		QFrame.__init__(self)
		self.ui = Ui_Form()
		self.ui.setupUi(self)

                #Make OcelotInterface parent of resetpanel widget
		self.ui.widget.set_parent(self)
		
		#Check for devmode --s from command line, set proper mi.
		self.devmodeCheck()
		
		#method to get defaults for all the scan parameters
                self.setScanParameters()

                #Instantiate machine specific methods 
		self.opt_control = OptControl()

		#Clear out callback PV
		self.callbackPV = None
		
		#Set GP options box disabled
		self.ui.groupBox_2.setEnabled(False)

                #set rate callback
		#ratepv = self.mi.get('EVNT:SYS0:1:LCLSBEAMRATE')
		#ratepv.add_callback(self.setRate)
		
                #set message callback
		#messpv = self.mi.get('SIOC:SYS0:ML00:CA000')
		#messpv.add_callback(self.messageOut)

		#opening message
		#self.ui.messages.setText('Hello, I am the Optimizer Interface')

                #scan panel button connections
		self.ui.startButton.clicked.connect(self.startScan)

                #logbooking
		self.ui.logButton.clicked.connect(lambda:self.logTextVerbose())

		#dropdown for scan device sets
		self.ui.deviceList.activated.connect(self.selectQuads)
		
		#dropdown to select optimizer
		self.ui.select_optimizer.activated.connect(self.scanMethodSelect)

		#clear table button
		self.ui.remDevice.clicked.connect(self.emptyTable)
		
		#add device from dropdown
		self.ui.addDevice.clicked.connect(self.addList)

                #launch heatmap button
		self.ui.heatmapButton.clicked.connect(self.launchHeatMap)

                #help and documentation launch button
                self.ui.helpButton.clicked.connect(lambda: os.system("firefox file:///usr/local/lcls/tools/python/toolbox/OcelotInterface/docs/build/html/index.html"))

                #ocelot edm panel for development
                self.ui.devButton.clicked.connect(lambda: os.system("edm -x /home/physics/tcope/edm/ocelot_dev.edl &"))

                #Save path for data, default will put the data in the current matlab data directory
                #See data logging module 'matlog'
                self.save_path = 'default'

                #init plots 
                self.addPlots()
                
                #object funciton selectinator (gdet)
                self.setObFunc()

		#load in the dark theme style sheet
                self.loadStyleSheet()

                #timer for plots, starts when scan starts
		self.multiPvTimer = QtCore.QTimer()
    		self.multiPvTimer.timeout.connect(self.getPlotData)
                
		#Index of optimizer selection dropdown
		self.indexOpt = 0
		
		#Index of device list dropdown
		self.index = 0

        def loadStyleSheet(self):
                """ Sets the dark GUI theme from a css file."""
		try:
			self.cssfile = "style.css"
			with open(self.cssfile,"r") as f:
				self.setStyleSheet(f.read())
		except IOError:
			print 'No style sheet found!'	

	def emptyTable(self):
		""" Calls resetpanelbox class method to empty devices from list."""
		self.ui.widget.clearTable()

	def addList(self):
		""" Calls resetpanelbox class method to add devices from list (e.g. LI26 Quads)."""
		self.ui.widget.addTable(self.index)

	def selectQuads(self):
		""" Selects devices to add to table from dropdown, sets index."""
		self.index= self.ui.deviceList.currentIndex()

	def setRate(self,pvName = None, value = None, char_value = None, **kw):
		""" Method to update rate label and determine data_delay for scan. """
		self.rate = value
		try:	
			self.data_delay = self.numPulse/self.rate#default number of pulses
		except:
			print 'rate is 0, setting data_delay to 0s'
		self.ui.delay_label.setText("Cycle Period = "+str(round(self.trim_delay+self.data_delay,4)))
	
	def messageOut(self,pvName = None, value = None, char_value = None, **kw):
		""" Gets the current error message and displays in label on GUI in a callback. """
		self.message = char_value
		self.ui.messages.setText(self.message)

	def setObFunc(self):
                """ 
                Method to select new objective function PV (GDET).
                
                Typically the gas detector, but it could be some other calc PV.
                """
                text = str(self.ui.obj_func_edit.text())
                #check for blank string that will break it
                if text == '':
                        self.ui.obj_func_edit.setStyleSheet("color: red")
                        return 
		state = self.mi.get(str(text))
                print state

                if state != None:
                        self.objective_func_pv = text
                        self.ui.obj_func_edit.setStyleSheet("color: rgb(85, 255, 0);")
                        self.plot1.setLabel('left',text=text)
                else:
                        self.ui.obj_func_edit.setStyleSheet("color: red")	

	def create_devices(self, pvs):
		"""
		Method to create devices using only channels (PVs)
		:param pvs: str, device address/channel/PV
		:return: list of the devices [mint.opt_objects.Device(eid=pv[0]), mint.opt_objects.Device(eid=pv[1]), ... ]
		"""
		devices = []
		vals = []
		for pv in pvs:
			dev = obj.Device(eid=pv)
			dev.mi = self.mi
			val = dev.get_value()
			devices.append(dev)
			vals.append(val)
		return devices

        def setListener(self,state):
                """ 
                Method to set epics flag inducating that this GUI is running.

                Args:
                        state (bool): Bools to set the PV stats flag true or false 
                """
                #watcher cud flag
                try:
			self.mi.put("PHYS:ACR0:OCLT:OPTISRUNNING", state)
                except:
                        print "No watcher cud PV found!"
                #listener application flag
                try:     
			self.mi.put("SIOC:SYS0:ML03:AO702" ,state) 
                except:
                        print "No listener PV found!"

                #sets the hostname env to another watcher cud PV
                try:
                        opi = os.environ['HOSTNAME']
			self.mi.put("SIOC:SYS0:ML00:CA999",opi)
                except:
                        print "No OPI enviroment variable found"

	def simDisable(self):
		"""
                Method to disable development functionality durring production use.
                """
		#objective function edit
		self.ui.obj_func_edit.setEnabled(False)
		
		#Trim Delay
		self.ui.trim_delay_edit.setEnabled(False)

		#Add Remove/Devices UI Objects
		self.ui.addDevice.setEnabled(False)
		self.ui.remDevice.setEnabled(False)
		self.ui.deviceList.setEnabled(False)
		self.ui.deviceEnter.setEnabled(False)

	def devmodeCheck(self):
		#Check for sim mode
		parser = argparse.ArgumentParser(description = 'To launch sim mode')
		parser.add_argument('--s','--simulation', action = 'store_true', help = "run in simulation mode")
		self.args = parser.parse_args()	

                #setup development mode if devmode==True
		if self.args.s:
			self.simDisable()
			path = '/u1/lcls/matlab/data/2016/2016-10/2016-10-20/'
			scan = 'CorrelationPlot-QUAD_LI26_801_BCTRL-2016-10-20-055153.mat'
			#scan = 'CorrelationPlot-QUAD_IN20_511_BCTRL-2016-10-20-053315.mat'
			sint = SimulationInterface(path+scan)
			self.mi = sint
			print "Using Simulation Interface"
			
		else:
			self.mi = LCLSMachineInterface()
			print "Launching Ocelot in Normal Mode"

        def devmode(self):
                """
                Used to setup a development mode for quick testing.

                This method contains settings for a dev mode on GUI startup.

                Uses the following PVs as dev devices:
                        SIOC:SYS0:ML00:CALCOUT997
                        SIOC:SYS0:ML00:CALCOUT998
                        SIOC:SYS0:ML00:CALCOUT999
                        SIOC:SYS0:ML00:CALCOUT000

                Uses the following PV as an objective function:
                        SIOC:SYS0:ML00:CALCOUT993

                Best used with the epics dev control panel fromt he GUIs options panel.
                """
                #select GP alg for testing
                self.ui.select_optimizer.setCurrentIndex(0) 

                #set dev objective function
                self.objective_func_pv = "SIOC:SYS0:ML00:CALCOUT993"

                #faster timing
                self.trim_delay = 0.2 #fast trim time
                self.data_delay = 0.2 #fast delay time

                #GP settings
                self.GP_hyp_file = "parameters/hype3.npy"
                self.SeedScanBool = True
                #set the save path to tmp instead of the lcls matlab data directory
                self.save_path = '/tmp/'
	       	self.ui.widget.devices = []
       		self.pvs =[]
	       	for dev in self.mi.pvs[0:2]:
	       		self.pvs.append(str(dev))
	       	self.ui.widget.addPv(str(self.pvs[0]))
	       	self.ui.widget.addPv(self.pvs[1])
		self.devices = []
	       	self.devices = self.ui.widget.get_devices(self.pvs[0:2])
	       	self.objective_func_pv = self.mi.pvs[2]
		self.scanMethodSelect()

#==============================================================#
# -------------- Start code for scan options UI -------------- #
#==============================================================#



        def setScanParameters(self):
                """
                Initialize default parameters for a scan when the GUI starts up.

                Creates connection for parameter changes on options panel.
                """
                #normalization amp coeff for scipy scanner
                #multiplicative factor
                self.norm_amp_coeff = 1.0
                self.ui.norm_scale_edit.setText(str(self.norm_amp_coeff))
                self.ui.norm_scale_edit.returnPressed.connect(self.setNormAmpCoeff)

		#To scale hyperparameters
		self.hyp_amp_coeff = 1.0
		self.ui.hyp_scale_edit.setText(str(self.hyp_amp_coeff))
                self.ui.hyp_scale_edit.returnPressed.connect(self.setHypAmpCoeff)
		

                #set objection method (gdet or some other pv to optimize)
                #self.objective_func_pv = "GDET:FEE1:241:ENRCHSTBR"
		if self.args.s:
			self.objective_func_pv = str(self.mi.pvs[2])
		else:
			self.objective_func_pv = "SIOC:SYS0:ML00:CALCOUT000"
		self.ui.obj_func_edit.setText(str(self.objective_func_pv))
                self.ui.obj_func_edit.returnPressed.connect(self.setObFunc)

		#For manually adding device to scan by typing it in
		self.ui.deviceEnter.returnPressed.connect(self.setDevice)

                #set trim delay
                self.trim_delay = 1.0
                self.ui.trim_delay_edit.setText(str(self.trim_delay))
                self.ui.trim_delay_edit.returnPressed.connect(self.setTrimDelay)

                #set data delay
		self.numPulse = 120
		#self.rate = self.mi.get('EVNT:SYS0:1:LCLSBEAMRATE')
		#if self.rate != 0:
		#	self.data_delay = self.numPulse/self.rate#default number of pulses	
		self.data_delay = 1
                self.ui.data_points_edit.setText(str(self.numPulse))
                self.ui.data_points_edit.returnPressed.connect(self.setDataDelay)
		self.ui.delay_label.setText("Cycle Period = "+str(round(self.trim_delay+self.data_delay,4)))

                #set GP Seed data file
                self.GP_seed_file = "parameters/simSeed.mat"
                self.ui.seed_file_edit.setText(str(self.GP_seed_file))
                self.ui.seed_file_edit.returnPressed.connect(self.setGpSeed)

                #set GP Hyperparameters from a file
                self.GP_hyp_file = "parameters/hype3.npy"
                self.ui.hyps_edit.setText(str(self.GP_hyp_file))
                self.ui.hyps_edit.returnPressed.connect(self.setGpHyps)

                #set the "use GP Simplex Seed" bool for the GP optimizer class
                self.use_normscale = True
                self.ui.normscale_check.stateChanged.connect(self.setNormScale)
                self.ui.normscale_check.setCheckState(2)

		#set the "use GP Simplex Seed" bool for the GP optimizer class
		self.SeedScanBool = True
                self.ui.live_seed_check.stateChanged.connect(self.setGpSimplexSeed)
                self.ui.live_seed_check.setCheckState(2)

                #initialize algorithm names for UI, add items to combobox
                self.name1 = "Nelder-Mead Simplex"
                self.name2 = "Gaussian Process"
                self.name3 = "Conjugate Gradient"
                self.name4 = "Powell's Method"
                self.ui.select_optimizer.addItem(self.name1)
                self.ui.select_optimizer.addItem(self.name2)
                #self.ui.select_optimizer.addItem(self.name3)
                #self.ui.select_optimizer.addItem(self.name4)

                #initialize GUI with simplex method
                self.name_opt = "Nelder-Mead Simplex"        

	def loadSimData(self):
		return 0

	def setSimMode(self):
		return 0

	def setDevice(self):
                """ 
                Method to select new Device to Scan, must be valid PV.
                
                """
                text = str(self.ui.deviceEnter.text())
                #check for blank string that will break it
                if text == '':
                        self.ui.deviceEnter.setStyleSheet("color: red")
                        return #exit

		state = self.mi.get(str(text))
                print "state"

                if state != None:
                        self.ui.widget.addPv(text)
			self.ui.deviceEnter.clear()
                        
        def setNormAmpCoeff(self):
                """Changes the scaling parameter for the simplex/scipy normalization."""
                try:
                        self.norm_amp_coeff = float(self.ui.norm_scale_edit.text())
                        print "Norm scaling coeff = ", self.norm_amp_coeff
                except:
                        self.ui.norm_scale_edit.setText(str(self.norm_amp_coeff))
                        print "Bad float for norm amp coeff"

	def setHypAmpCoeff(self):
                """Changes the scaling parameter for the simplex/scipy normalization."""
                try:
                        self.hyp_amp_coeff = float(self.ui.hyp_scale_edit.text())
                        print "Hyperparameter scaling coeff = ", self.hyp_amp_coeff
                except:
                        self.ui.hyp_scale_edit.setText(str(self.hyp_amp_coeff))
                        print "Bad float for norm amp coeff"

        def setTrimDelay(self):
                """
                Select a new trim time for a device from GUI line edit.

                Scanner will wait this long before starting data acquisition.
                """
                try:
                        self.trim_delay = float(self.ui.trim_delay_edit.text())
                        self.ui.delay_label.setText("Cycle Period = "+str(round(self.trim_delay+self.data_delay,4)))
                        print "Trim delay =",self.trim_delay
                except:
                        self.ui.trim_delay.setText(str(self.trim_delay))
                        print "bad float for trim delay"

        def setDataDelay(self):
                """
                Select time for objective method data collection time.

                Scanner will wait this long to collect new data.
                """
                try:
                        self.numPulse = float(self.ui.data_points_edit.text())
			self.rate = self.mi.get('EVNT:SYS0:1:LCLSBEAMRATE')
			self.data_delay = self.numPulse/self.rate
                        self.ui.delay_label.setText("Cycle Period = "+str(round(self.trim_delay+self.data_delay,4)))
                        print "Data delay =",self.data_delay
                except:
                        self.ui.data_points_edit.setText(str(self.data_delay))
                        print "bad float for data delay"

        def setGpSeed(self):
                """
                Set directory string to use for the GP scanner seed file.
                """
                self.GP_seed_file = str(self.ui.seed_file_edit.text())

        def setGpHyps(self):
                """
                Set directory string to use for the GP hyper parameters file.
                """
                self.GP_hyp_file = str(self.ui.hyps_edit.text())
                print self.GP_hyp_file

        def setGpSimplexSeed(self):
                """
                Sets the bool to run GP in a simplex seed mode.
                """
                if self.ui.live_seed_check.isChecked():
                        self.seedScanBool = True
                else:
                        self.seedScanBool = False
                print "GP seed bool == ",self.seedScanBool
 
	def setNormScale(self):
                """
                Sets the bool to use normalization scale factor for Simplex
                """
                if self.ui.normscale_check.isChecked():
                        self.useNormScale = True
                else:
                        self.useNormScale = False
                print "Use Normalization Scaling == ",self.useNormScale
#========================================================================#
# -------------- Start code for running optimization scan -------------- #
#========================================================================# 


	def scanMethodSelect(self):
                """
                Sets scanner method from options panel combo box selection.  Creates Objective Function object
		
                
                This method executes from the startScan() method, when the UI "Start Scan" button is pressed.

                Returns:
                         Selected scanner object 
                         These objects are contrained in the scannerThreads.py file
                """
                self.indexOpt = self.ui.select_optimizer.currentIndex()
		self.name_opt = self.ui.select_optimizer.currentText()
		self.objective_func = obj.SLACTarget(eid=self.objective_func_pv)	
		self.objective_func.mi = self.mi

                #simplex Method
                if self.indexOpt == 0: 
                        self.minimizer = Simplex()
			self.ui.groupBox_2.setEnabled(False)
			self.ui.groupBox_4.setEnabled(True)

                #GP Method
                if self.indexOpt == 1: 
			self.minimizer = GaussProcess()
			self.ui.groupBox_2.setEnabled(True)
			self.ui.groupBox_4.setEnabled(False)
			self.use_normscale = False

                # Conjugate Gradient
                if self.indexOpt == 2: 
                        self.name_current = self.name3

                # Powells Method
                if self.indexOpt == 3: 
                        self.name_current = self.name4

                print "Selected Algorithm =", self.name_opt
		return self.minimizer

	def closeEvent(self, event):
		""" Happens upon user exit."""
		if self.ui.startButton.text() == "Stop Scan":
			self.opt.opt_ctrl.stop()
			del(self.opt)
			self.ui.startButton.setStyleSheet("color: rgb(85, 255, 127);")
			self.ui.startButton.setText("Start Scan")
			return 0
		QFrame.closeEvent(self, event)

	def set_inputs(self):
		""" Sets all the user inputs from UI """
		

	def startScan(self):
		"""
                This starts the optimizer thread and sets the algorithm as the "minimizer"
		
                
                This method executes when the UI "Start Scan" button is pressed.

                """
		self.setListener((self.indexOpt + 1))
		self.scanStartTime = time.time()
		self.pvs = self.ui.widget.getPvsFromCbState()
		self.devices = self.ui.widget.get_devices(self.pvs)
		if self.ui.startButton.text() == "Stop Scan":
			self.opt.opt_ctrl.stop()
			self.finishScript()
			return 0
		self.setUpMultiPlot(self.pvs)
    		self.multiPvTimer.start(100)
		self.scanMethodSelect()
		self.objective_func.points = self.numPulse
		self.opt = Optimizer()
		self.opt.norm_coef_multiplier = self.norm_amp_coeff 
		self.opt.normalization = self.use_normscale
		self.opt.minimizer = self.minimizer
		self.opt.timeout    = self.data_delay+self.trim_delay
		self.minimizer.seed_timeout = self.data_delay+self.trim_delay
		self.minimizer.max_iter = 50
		self.minimizer.hyper_file = "parameters/hype3.npy"
		self.minimizer.multiplier = self.hyp_amp_coeff
		self.opt.seq = [Action(func=self.opt.max_target_func, args=[self.objective_func, self.devices])]
		self.opt.start()
		self.ui.startButton.setText("Stop Scan")
		self.ui.startButton.setStyleSheet("color:red")
	
	def scanFinished(self, guimode = True):
                """
                Reset the GUI after a scan is complete.  Runs on QTimer set in Main()
                """
		try:
			if not self.opt.isAlive() and self.ui.startButton.text() == "Stop Scan":
				self.finishScript()
		except:
			pass
	
	def finishScript(self):
		print "Scan Finished"
		if self.args.s:
			pass
		else:
			self.saveData()
                #set flag PV to zero
		self.setListener(0)
		del(self.opt)
		#reset UI controls
		self.multiPvTimer.stop()
		self.ui.startButton.setStyleSheet("color: rgb(85, 255, 127);")
		self.ui.startButton.setText("Start scan")

	##############from GP scanner Threads, not sure if we use this.

        def loadModelParams(self, model, filename):
                """ 
                Method to build the GP model using loaded model parameters

                Can give this method an ocelot save file to load in that files model
               
                Args:
                        filename (str): String for the file directory
                        model (object): Takes in a GP model object

                Returns:
                        GP model object with parameters from loaded data
                """
                model_file = scipy.io.loadmat(filename)['data']

                model.alpha        = model_file['alpha'].flatten(0)[0]
                model.C            = model_file['C'].flatten(0)[0]
                model.BV           = model_file['BV'].flatten(0)[0]
                model.covar_params = model_file['covar_params'].flatten(0)[0]
                model.covar_params = (model.covar_params[0][0],model.covar_params[1][0])
                model.KB           = model_file['KB'].flatten(0)[0]
                model.KBinv        = model_file['KBinv'].flatten(0)[0]
                model.weighted     = model_file['weighted'].flatten(0)[0]

                print
                print 'Loading in new model from:'
                print filename
                print 

                return model

	def saveModel(self):
                """ 
                Add GP model parameters to the save file.
                """
                #add in extra GP model data to save
                self.mi.data["alpha"]        = self.model.alpha
                self.mi.data["C"]            = self.model.C
                self.mi.data["BV"]           = self.model.BV
                self.mi.data["covar_params"] = self.model.covar_params
                self.mi.data["KB"]           = self.model.KB
                self.mi.data["KBinv"]        = self.model.KBinv
                self.mi.data["weighted"]     = self.model.weighted
                self.mi.data["noise_var"]    = self.model.noise_var
                self.mi.data["pv_list"]      = self.pvs	          

#======================================================================#
# -------------- Start code for setting/updating plots --------------- #
#======================================================================#

        def getPlotData(self):
                """
                Collects data and updates plot on every GUI clock cycle.
                """
                #get x,y obj func data from the machine interface
                try:
			y = self.objective_func.values
                except:
                        self.scanFinished
		x = np.array(self.objective_func.times) - self.objective_func.times[0]
                
                #set data to like pg line object
                self.obj_func_line.setData(x=x,y=y)

		for dev in self.devices:
			y = np.array(dev.values)-self.multiPlotStarts[dev.eid]
			x = np.array(dev.times) - np.array(dev.times)[0]
			line = self.multilines[dev.eid]
			line.setData(x=x, y=y)

        
        def addPlots(self):
                """
                Initializes the GUIs plots and labels on startup.
                """
                #setup plot 1 for obj func monitor
                self.plot1 = pg.PlotWidget(title = "Objective Function Monitor",labels={'left':str(self.objective_func_pv),'bottom':"Time (seconds)"})
                self.plot1.showGrid(1,1,1)
		self.plot1.getAxis('left').enableAutoSIPrefix(enable=False) # stop the auto unit scaling on y axes
		layout = QtGui.QGridLayout()
		self.ui.widget_2.setLayout(layout)
		layout.addWidget(self.plot1,0,0)	

                #setup plot 2 for device monitor
                self.plot2 = pg.PlotWidget(title = "Device Monitor",labels={'left':"Device (Current - Start)",'bottom':"Time (seconds)"})
                self.plot2.showGrid(1,1,1)
		self.plot2.getAxis('left').enableAutoSIPrefix(enable=False) # stop the auto unit scaling on y axes
		layout = QtGui.QGridLayout()
		self.ui.widget_3.setLayout(layout)
		layout.addWidget(self.plot2,0,0)	

                #legend for plot 2
                self.leg2 = customLegend(offset=(75,20))
                self.leg2.setParentItem(self.plot2.graphicsItem())

                #create the obj func line object
                color = QtGui.QColor(0,255,255)
                pen=pg.mkPen(color,width=3)
                self.obj_func_line = pg.PlotCurveItem(x=[],y=[],pen=pen,antialias=True)
                self.plot1.addItem(self.obj_func_line)

        def randColor(self):
                """
                Generate random line color for each device plotted.

                Returns: 
                        QColor object of a random color
                """
		hi = 255
		lo = 128 
		c1 = np.random.randint(lo,hi)
		c2 = np.random.randint(lo,hi)
		c3 = np.random.randint(lo,hi)
		return QtGui.QColor(c1,c2,c3)

        def setUpMultiPlot(self,pvs):
                """
                Reset plots when a new scan is started.
                """
                self.plot2.clear()
                self.multilines      = {}
                self.multiPvData     = {}
                self.multiPlotStarts = {}
                x = []
                y = []
                self.leg2.scene().removeItem(self.leg2)
                self.leg2 = customLegend(offset=(50,10))
                self.leg2.setParentItem(self.plot2.graphicsItem())

                default_colors = [QtGui.QColor(255,51,51),QtGui.QColor(51,255,51),QtGui.QColor(255,255,51),QtGui.QColor(178,102,255)]
                for i in range(len(pvs)):
       
                        #set the first 4 devices to have the same default colors
                        if i < 4:
                                color = default_colors[i]
                        else:
                                color = self.randColor()

                        pen=pg.mkPen(color,width=2)
                        self.multilines[pvs[i]]  = pg.PlotCurveItem(x,y,pen=pen,antialias=True,name=str(pvs[i]))
                        self.multiPvData[pvs[i]] = []
                        self.multiPlotStarts[pvs[i]] = self.mi.get(pvs[i])
                        self.plot2.addItem(self.multilines[pvs[i]])
                        self.leg2.addItem(self.multilines[pvs[i]],pvs[i],color=str(color.name()))
        

        def launchHeatMap(self):
                """
                Launches script to display a GP heatmap of two PVs selected from table.

                Can only show data from the GUIs last scan.
                """
                pvnames = self.ui.widget.getPvsFromCbState()
                if len(pvnames) != 2:
                        print "Pick only 2 PVs for a slice!"
                        return
                com = "python ./GP/analyze_script.py "+str(self.last_filename)+" "+pvnames[0]+" "+pvnames[1]+" &"
                print 'Heatmap command:',com
                os.system(com)

#======================================================================#
# -------------- Start code for saving/logbooking data --------------- #
#======================================================================#


        def record_data(self):
                """
                Get data for devices everytime the SASE is measured to save syncronous data.
                
                Args:
                        gdet (str): String of the detector PV, usually gas detector
                        simga (float): Float of the measurement standard deviation
                
                """
		self.data = {} #dict of all devices deing scanned
                self.data[self.objective_func_pv] = [] #detector data array
                self.data['DetectorStd'] = [] #detector std array
                self.data['timestamps']  = [] #timestamp array
                for dev in self.devices:
                        self.data[dev.eid] = []
                self.data[self.objective_func_pv].append(self.objective_func.values) 
                self.data['DetectorStd'].append(self.objective_func.std_dev)
                self.data['timestamps'].append(self.objective_func.times)
                for dev in self.devices:
                        self.data[dev.eid].append(dev.values)
		return self.data

        def saveData(self):
                """
                Save scan data to the physics matlab data directory.
                
                Uses module matlog to save data dict in machine interface file.
                """
		data_new = self.record_data()
                #get the first and last points for GDET gain
                self.detValStart = data_new[self.objective_func_pv][0]
                self.detValStop  = data_new[self.objective_func_pv][-1]
        
                #replace with matlab friendly strings
                for key in data_new:
                        key2 = key.replace(":","_")
                        data_new[key2] = data_new.pop(key)
        
                #extra into to add into the save file
                data_new["BEND_DMP1_400_BDES"]   = self.mi.get("BEND:DMP1:400:BDES")
                data_new["ScanAlgorithm"]        = str(self.name_opt)      #string of the algorithm name
                data_new["ObjFuncPv"]            = str(self.objective_func_pv) #string identifing obj func pv
                data_new["NormAmpCoeff"]         = self.norm_amp_coeff

                #save data
                import matlog
                self.last_filename=matlog.save("OcelotScan",data_new,path=self.save_path) 

   	def logbook(self,extra_log_text='default'):
                """ 
                Send a screenshot to the physics logbook.

                Args:
                        extra_log_text (str): string to set if verbose text should be printed to logbook. 'default' prints only gain and algorithm
                """
                #Put an extra string into the logbook function

		log_text = "Gain ("+str(self.objective_func_pv)+"): "+str(round(self.objective_func.values[0],4))+" > "+str(round(self.objective_func.values[-1],4))
                if extra_log_text != 'default':
                        log_text = log_text+'\n'+str(extra_log_text)
                curr_time = datetime.now()
                timeString = curr_time.strftime("%Y-%m-%dT%H:%M:%S")
                log_entry = ElementTree.Element(None)
                severity  = ElementTree.SubElement(log_entry, 'severity')
                location  = ElementTree.SubElement(log_entry, 'location')
                keywords  = ElementTree.SubElement(log_entry, 'keywords')
                time      = ElementTree.SubElement(log_entry, 'time')
                isodate   = ElementTree.SubElement(log_entry, 'isodate')
                log_user  = ElementTree.SubElement(log_entry, 'author')
                category  = ElementTree.SubElement(log_entry, 'category')
                title     = ElementTree.SubElement(log_entry, 'title')
                metainfo  = ElementTree.SubElement(log_entry, 'metainfo')
                imageFile = ElementTree.SubElement(log_entry, 'link')
                imageFile.text = timeString + '-00.ps'
                thumbnail = ElementTree.SubElement(log_entry, 'file')
                thumbnail.text = timeString + "-00.png"
                text      = ElementTree.SubElement(log_entry, 'text')
                log_entry.attrib['type'] = "LOGENTRY"
                category.text = "USERLOG"
                location.text = "not set"
                severity.text = "NONE"
                keywords.text = "none"
                time.text = curr_time.strftime("%H:%M:%S")
                isodate.text =  curr_time.strftime("%Y-%m-%d")
                metainfo.text = timeString + "-00.xml"
                fileName = "/tmp/" + metainfo.text
                fileName=fileName.rstrip(".xml")
                log_user.text = " "
                title.text = unicode("Ocelot Interface")
                text.text = log_text
                if text.text == "": text.text = " " # If field is truly empty, ElementTree leaves off tag entirely which causes logbook parser to fail
                xmlFile = open(fileName+'.xml',"w")
                rawString = ElementTree.tostring(log_entry, 'utf-8')
                parsedString = sub(r'(?=<[^/].*>)','\n',rawString)
                xmlString=parsedString[1:]
                xmlFile.write(xmlString)
                xmlFile.write("\n")  # Close with newline so cron job parses correctly
                xmlFile.close()
                self.screenShot(fileName,'png')
                path = "/u1/lcls/physics/logbook/data/"
                copy(fileName+'.ps', path)
                copy(fileName+'.png', path)
                copy(fileName+'.xml', path)

        def screenShot(self,filename,filetype):
	        """ 
                Takes a screenshot of the whole gui window, saves png and ps images to file

                Args:
                        fileName (str): Directory string of where to save the file
                        filetype (str): String of the filetype to save
                """
                s = str(filename)+"."+str(filetype)
                p = QPixmap.grabWindow(self.winId())
                p.save(s, 'png')
                im = Image.open(s)
                im.save(s[:-4]+".ps")
                p = p.scaled(465,400)
                p.save(str(s), 'png')


        def logTextVerbose(self):
                """
                Logbook method with extra info in text string>
                """  
		e1 = "Iterations: "+str(self.objective_func.niter)+"\n"  
                e2 = "Trim delay: "+str(self.trim_delay)+"\n"
                e3 = "Data delay: "+str(self.data_delay)+"\n"
                e5 = "Normalization Amp Coeff: "+str(self.norm_amp_coeff)+"\n"
                e6 = "Using Live Simplex Seed: "+str(self.SeedScanBool)+"\n"
                e7 = "Type of optimization: "+(self.name_opt)+"\n"

                extra_log_text = e1+e2+e3+e5+e6+e7
                self.logbook(extra_log_text)


#==========================================================================#
# -------------- Start code for reformating the plot legend -------------- #
#==========================================================================#


# Ignore most of thus stuff, only cosmetic for device plot

class customLegend(pg.LegendItem):
        """ 
        STUFF FOR PG CUSTOM LEGEND (subclassed from pyqtgraph).
        Class responsible for drawing a single item in a LegendItem (sans label).
        This may be subclassed to draw custom graphics in a Legend.
        """
        def __init__(self,size=None,offset=None):
                pg.LegendItem.__init__(self,size,offset)
                 
        def addItem(self, item, name, color="CCFF00"):

                label = pg.LabelItem(name,color=color,size="6pt",bold=True)
                sample = None
                row = self.layout.rowCount()
                self.items.append((sample, label))
                self.layout.addItem(sample, row, 0)
                self.layout.addItem(label, row, 1)
                self.layout.setSpacing(0)
    
class ItemSample(pg.GraphicsWidget):
    """ MORE STUFF FOR CUSTOM LEGEND """

     ## Todo: make this more generic; let each item decide how it should be represented.
    def __init__(self, item):
        pg.GraphicsWidget.__init__(self)
        self.item = item
    
    def boundingRect(self):
        return QtCore.QRectF(0, 0, 20, 20)
        
    def paint(self, p, *args):
        #p.setRenderHint(p.Antialiasing)  # only if the data is antialiased.
        opts = self.item.opts
        
        if opts.get('fillLevel',None) is not None and opts.get('fillBrush',None) is not None:
            p.setBrush(fn.mkBrush(opts['fillBrush']))
            p.setPen(fn.mkPen(None))
            p.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(2,18), QtCore.QPointF(18,2), QtCore.QPointF(18,18)]))
        
        if not isinstance(self.item, ScatterPlotItem):
            p.setPen(fn.mkPen(opts['pen']))
            p.drawLine(2, 18, 18, 2)
        
        symbol = opts.get('symbol', None)
        if symbol is not None:
            if isinstance(self.item, PlotDataItem):
                opts = self.item.scatter.opts
                
            pen = fn.mkPen(opts['pen'])
            brush = fn.mkBrush(opts['brush'])
            size = opts['size']
            
            p.translate(10,10)
            path = drawSymbol(p, symbol, size, pen, brush)

#==============================================================#
# --------------- main method for starting GUI --------------- #
#==============================================================#

def main():

        """
        Function to start up the main program.

        Slecting a PV parameter set:
        If launched from the command line will take an argument with the filename of a parameter file.
        If no argv[1] is provided, the default list in ./parameters/lclsparams is used.

        Development mode:
        If devmode == False - GUI defaults to normal parameter list, defaults to nelder mead simplex
        if devmode == True  - GUI uses 4 development matlab PVs and loaded settings in the method "devmode()"
        """

	pvs = 'parameters/lclsparams'#default filename

        #make pyqt threadsafe
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_X11InitThreads)
        
        #create the application
        app    = QApplication(sys.argv)
        window = OcelotInterfaceWindow()

	#timer for end of scan, need to look at new threading methods using QT for Optimizer thread.
	timerFin = pg.QtCore.QTimer()
	timerFin.timeout.connect(window.scanFinished)
	timerFin.start(300)

        #setup development mode if devmode==True
	if window.args.s:
		devmode = True
	else:
		devmode = False
        if devmode:
		pvs =[]
	       	for dev in window.mi.pvs[0:2]:
	       		pvs.append(str(dev))
                window.devmode()
        else:
                pass
                #window.simDisable()
        
        #Build the PV list from dev PVs or selected source
        window.ui.widget.getPvList(pvs)

        #set checkbot status
        if not devmode: 
                window.ui.widget.uncheckBoxes()

        #show app
        window.setWindowIcon(QtGui.QIcon('ocelot.png'))
        window.show()

        #Build documentaiton if source files have changed
        os.system("cd ./docs && xterm -T 'Ocelot Doc Builder' -e 'bash checkDocBuild.sh' &")
        sys.exit(app.exec_())

if __name__ == "__main__":
        main()
