"""
Objective function and devices
S.Tomin, 2017
"""

import numpy as np
import time

class Device(object):
    def __init__(self, eid=None):
        self.eid = eid
        self.id = eid
        self.values = []
        self.times = []
        self.simplex_step = 0
        self.mi = None

    def set_value(self, val):
        """ Set Value for devices, record time and value """
        self.values.append(val)
        self.times.append(time.time())
        self.mi.set_value(self.eid, val)

    def get_value(self):
        """ Standard get_value method for devices """
        val = self.mi.get_value(self.eid)
        return val

    def state(self):
        """
        Check if device is readable
        :return: state, True if readable and False if not
        """
        state = True
        try:
            self.get_value()
        except:
            state = False
        return state

    def clean(self):
        """ Init time and value list for device """
        self.values = []
        self.times = []

    def check_limits(self, value):
        limits = self.get_limits()
        if value < limits[0] or value > limits[1]:
            print('limits exceeded', value, limits[0], value, limits[1])
            return True
        return False

    def get_limits(self):
        return self.mi.get_limits(self.eid)

class SLACTarget(object):
    def __init__(self, mi=None, eid=None):
        super(SLACTarget, self).__init__()
        """
        :param mi: Machine interface
        :param dp: Device property
        :param eid: ID
        """
        self.eid = eid
        self.secs_to_ave = 1
        self.debug = False
        self.kill = False
        self.pen_max = 100
        self.niter = 0
        self.y = []
        self.x = []
        self.eid = eid
        self.id = eid
        self.pen_max = 100
        self.penalties = []
        self.values = []
        self.alarms = []
        self.times = []
        self.std_dev = []
        self.points = None
        
    def get_penalty(self):
        sase, std = self.get_value()
        alarm = self.get_alarm()
        if self.debug: print('alarm:', alarm)
        if self.debug: print('sase:', sase)
        pen = 0.0
        if alarm > 1.0:
            return self.pen_max
        if alarm > 0.7:
            return alarm * 50.0
        pen += alarm
        pen -= sase
        if self.debug: print('penalty:', pen)
        self.penalties.append(pen)
        self.times.append(time.time())
        self.values.append(sase)
        self.std_dev.append(std)
        self.alarms.append(alarm)
        self.niter += 1
        return pen

    def check_machine(self):
        """ Check the machine for errors """
        self.mi.errorCheck()

    def get_value(self):
        """
        Returns data for the ojective function (detector) from the selected detector PV.
        At lcls the repetition is  120Hz and the readout buf size is 2800.
        The last 120 entries correspond to pulse energies over past 1 second.
        Args:
                seconds (float): Variable input on how many seconds to average data
        Returns:
                Float of SASE or other detecor measurment
                Float of Standard Deviation of array, or -1 for non-array.
        """
        datain = self.mi.get_value(self.eid)
        dataout, sigma = self.mi.get_sase(datain, self.points)
        return dataout, sigma

    def get_alarm(self):
        """ Used with alarms, not used for now """
        return 0

    def get_energy(self):
        """ Get Energy for hyperparams loading """
        return self.mi.get_energy()
