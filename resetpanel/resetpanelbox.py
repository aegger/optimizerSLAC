#!/usr/local/lcls/package/python/current/bin/python
"""
Subclass of ResetpanelWindow, used to make a version with check box selction

Tyler Cope, 2016
"""

from resetpanel import ResetpanelWindow
from PyQt4.QtGui import QApplication, QFrame, QPushButton, QClipboard, QTableWidget
from PyQt4 import QtGui, QtCore, Qt, uic
import sys
import time

class customTW(QTableWidget):
        """
        Subclass the tablewidget to add a custom PV on middle click.
        """
        def __init__(self, parent):
                """Init for the table widget, nothing special here"""
                QTableWidget.__init__(self, parent)
                self.parent = parent

	def mouseReleaseEvent(self, evt):
                """ 
                Grabs string from the clipboard if middle button click.

                Tries to then add the PV to the parent GUI pv lists.
                Calls parent.addPv() method.

                Args:
                        evt (QEvent): Event object passed in from QT
                """
		button = evt.button()
                if (button == 4) and (self.parent.enableMiddleClick):
                        pv = QtGui.QApplication.clipboard().text(mode=QClipboard.Selection)
                        self.parent.addPv(pv)
                else:
                        QTableWidget.mouseReleaseEvent(self,evt)

class ResetpanelBoxWindow(ResetpanelWindow):
        """
        The main GUI class to add in checkboxes, subclassed from the ResetPanelWindow class.
        """
	def __init__(self,parent=None):

                """
                Init method, adds in some new UI changes.

                Adds two buttons, to check and uncheck selected rows.
                Add in subclassed table to enable middle click PV add.
                """

		#initialize
	        ResetpanelWindow.__init__(self)

                self.check = QPushButton(self)
                self.check.setText('Check')
                self.uncheck = QPushButton(self)
                self.uncheck.setText('Uncheck')
                self.ui.horizontalLayout.addWidget(self.check)
                self.ui.horizontalLayout.addWidget(self.uncheck)
                self.check.clicked.connect(lambda: self.getRows(2))
                self.uncheck.clicked.connect(lambda: self.getRows(0))

                #make button text bigger
                #self.check.setStyleSheet('font-size: 18pt; font-family: Courier;')

                #enable middle click method
                self.enableMiddleClick = True

                #make the custom table for middle click
                self.ui.tableWidget.setParent(None) #remove old table
                self.ui.tableWidget = customTW(self) # make new widget
                self.ui.gridLayout.addWidget(self.ui.tableWidget,0,0)

		#get list of all devices in parameters/lclsparams to set with addTable
		self.pvsAll = []
		for line in open('parameters/lclsparams'):
			l = line.rstrip('\n')
			self.pvsAll.append(str(l[1:len(l)]))

	def set_parent(self, parent):
		self.parent = parent

	def mouseReleaseEvent(self, evt):
                """
	        Get PV coppied from the system clipboard on button release
                
                Button 4 is the middle click button.
                """
		button = evt.button()
                if (button == 4) and (self.enableMiddleClick):
                        pv = QtGui.QApplication.clipboard().text(mode=QClipboard.Selection)
                        self.addPv(pv)

	def clearTable(self):
		self.ui.tableWidget.clearContents()	
		self.ui.tableWidget.setRowCount(0)
		self.pvs=[]

	def addTable(self,index):
		"""
		Add a set of devices based on dropdown selection
		
		Args:
	                index (int): index of selection from deviceList QComboBox 
		"""
		if index == 0:
			self.pvs.extend(self.pvsAll[22:28])#IN20 Quads
		if index == 1:
			self.pvs.extend(self.pvsAll[18:22])#LI21 Quads
		if index == 2:
			self.pvs.extend(self.pvsAll[4:8])#LI26 201-501
		if index == 3:
			self.pvs.extend(self.pvsAll[8:12])#Li26 601-901
		if index == 4:
			self.pvs.extend(self.pvsAll[0:4])#LTU Quads
		if index == 5:
			self.pvs.extend(self.pvsAll[12:18])#Dispersion Quads
		if index == 6:
			self.pvs.extend(self.pvsAll[28:31])#CQ/SQ01/SOL
		if index == 7:
			self.pvs.extend(self.pvsAll[31:35])#DMD

		for pv in self.pvs:
			dev = self.parent.create_devices(pvs =[pv])[0]
			self.devices.append(dev)
		self.getStartValues()
                self.initTable()
                self.addCheckBoxes()	

        def addPv(self,pv):
                """ 
                Add another PV to the GUI on middle click.
                
                Args:
                        pv (str): String name of the PV to add
                """
                pv = str(pv)
                if pv in self.pvs:
                        print "PV already in list"
                        return
                try:
			dev = self.parent.create_devices(pvs=[pv])[0]
                except:
                        print "bad string"
                        return
		state = dev.state()
		if state:
			self.pvs.append(pv)
			self.devices.append(dev)
			val = dev.get_value()
			self.startValues[pv] = val
                self.initTable()
                self.addCheckBoxes()
		
	def get_devices(self, pvs):
		d_pvs = [dev.eid for dev in self.devices]
		inxs = [d_pvs.index(pv) for pv in pvs]
		return [self.devices[inx] for inx in inxs]

        def getPvList(self,pvs_in=None):
                """ 
                Redefine method to add in checkboxes when getting the PV list.
                
                Copied from resetpanel.py        
                """
                print "LOADING:"
                if not pvs_in:
                        print 'Exiting'
                        return
        
                if type(pvs_in) != list: 
                        self.pvs = []
                        for line in open(pvs_in):
                                l = line.rstrip('\n')
                                if l[0] == '#':
                                        continue
                                self.pvs.append(str(l))
                else:
                        self.pvs = pvs_in

                print "PVS LOADED",self.pvs
		self.devices = self.parent.create_devices(self.pvs)
                self.getStartValues()
                self.initTable()
                self.addCheckBoxes()

        def getRows(self,state):
                """ 
                Method to set the UI checkbox state from slected rows.
                
                Loops though the rows and gets the selected state from the 'Active" column.
                If highlighted, check box is set the the 'state' input arg.

                Args:
                        state (bool): Bool of whether the boxes should be checked or unchecked.
                """
                rows=[] 
                for idx in self.ui.tableWidget.selectedIndexes():
                        rows.append(idx.row()) 
                        item = self.ui.tableWidget.item(idx.row(),3)
                        item.setCheckState(state)

        def addCheckBoxes(self):
                """ 
                Creats additional column in UI table for check box.
                
                Must be called again if the user adds another PV with middle click function.
                """
                headers = ["PVs","Saved Value","Current Value","Active"]
		self.ui.tableWidget.setColumnCount(len(headers))
                self.ui.tableWidget.setHorizontalHeaderLabels(headers)
                
                for row in range(len(self.pvs)+1):

                        checkBoxItem = QtGui.QTableWidgetItem()
                        checkBoxItem.setCheckState(QtCore.Qt.Checked)
                        flags = checkBoxItem.flags()
                        flags != flags
                        checkBoxItem.setFlags(flags)
                        self.ui.tableWidget.setItem(row,3,checkBoxItem)

        def uncheckBoxes(self):
                """ Method to uncheck all active boxes """
                for row in range(len(self.pvs)):
                        item=self.ui.tableWidget.item(row,3)
                        item.setCheckState(False)

        def resetAll(self):
                """
                Resets all PVs with a box checked.

                Rewrote this function to only change selected rows, not all rows.
                """
		for row, dev in enumerate(self.devices):
			val = self.startValues[dev.eid]
			state = self.ui.tableWidget.item(row,3).checkState()
			if state ==2:
				dev.set_value(val)

        def updateReference(self):
                """
                Update reference values for selected rows.

                Rewrote this function to only update slected rows, not all.
                """
                self.ui.updateReference.setText("Getting vals...")
		for row in range(len(self.devices)):
			dev = self.devices[row]
			state = self.ui.tableWidget.item(row,3).checkState()
			print "STATE"
			if state == 2:
				self.startValues[dev.eid]= dev.get_value()
				self.ui.tableWidget.setItem(row,1,QtGui.QTableWidgetItem(str(self.startValues[dev.eid])))
		self.ui.updateReference.setText("Update Reference")

        def getPvsFromCbState(self):

                """
                Gets list of all pvs that have checked boxes.

                Returns:
                        List of PV strings
                """
                pvs = []  
                for row in range(len(self.pvs)):
                        state = self.ui.tableWidget.item(row,3).checkState()
                        if state == 2:
                                pvs.append(str(self.ui.tableWidget.item(row,0).text()))
                return pvs 

        #switch string from to SLECTED
        def launchPopupAll(self):
                """
                Launches the ARE YOU SURE popup for pv reset value function. 

                Rewrote to change the warning string to say "checkbox selected" instead of "all" to avoid confusion with number of devices being reset. 
                """
                self.ui_check = uic.loadUi("/home/physics/tcope/python/tools/resetpanel/UIareyousure.ui")
                self.ui_check.exit.clicked.connect(self.ui_check.close)
                self.ui_check.reset.clicked.connect(self.resetAll)
                self.ui_check.reset.clicked.connect(self.ui_check.close)
                self.ui_check.label.setText("Are you sure you want to implement \nchanges to checkbox selected PVs?")
                self.ui_check.show()

def main():
        """ 
        Start up the main program if launch from comamnd line.
        """
        try:
                pvs = sys.argv[1]
        except:
                pvs = "./lclsparams"       
        app = QApplication(sys.argv)
        window = ResetpanelBoxWindow()
        window.setWindowIcon(QtGui.QIcon('/usr/local/lcls/tools/python/toolbox/py_logo.png'))
        window.uncheckBoxes()
        window.show()
        sys.exit(app.exec_())

if __name__ == "__main__":
	main()
