# YET TO DO:
# - Modify the data in order to read from Arduino and Keithleys (DONE for Arduino!)
# - Some graphical tweaks
# - Test efficiency (DELAY!!) with Arduino as a timer (refresh every 4 s)
# - Output data file writing

import sys
import serial
import time
import random
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
from datetime import datetime
from queue import Queue,Empty


from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QThread,pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout,QWidget,QTabWidget,QLabel,QHBoxLayout,QComboBox, QPushButton

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import pymeasure.instruments.keithley as kit


class GetData(QtCore.QObject):
    """
    Subclass of QtCore.QObject, used for defining the main thread of program.
    """
    # How we expect our signal (13 floats)
    dataChanged = pyqtSignal(float, float, float, float, float, float, float, float,float,float,float,float,float)

    def __init__(self, queue, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)
        self.queue = queue

        # Data file path
        directory = "/home/labb2/ardu_dew_point/data/" # directory name << CHANGE WHEN NEEDED
        actual_time = f"{datetime.now()}"
        wrd = actual_time.split()
        wrd2 = wrd[1].split(":")
        wrd1 = wrd[0].split("-")
        dat = "".join(wrd1)
        tim = "".join(wrd2[:-1])
        ff = "-".join([dat,tim])
        file = "time-and-dew-point-{0}.dat".format(ff)
        self.filename = directory+file # file name << CHANGE WHEN NEEDED

        # Initialization of the serial port for communication with Arduino
        self.Arduino = serial.Serial("/dev/ttyUSB0",115200, timeout=0.01) # open the serial port << CHANGE WHEN NEEDED

        # INSERT THE CORRECT LINKS FOR THE KEITHLEYS
        # Initialization of the Keithleys for current measuring
        self.keithley1 = kit.Keithley2450("169.254.091.1")
        self.keithley2 = kit.Keithley2450("169.254.091.2")
        self.keithley3 = kit.Keithley2450("169.254.091.3")

        # IF THE CURRENTS' PART DOESN'T WORK: TRY WITH THE COMMANDS OF THE RAMP UP

        time.sleep(2) # wait 2 seconds


    def __del__(self):  # part of the standard format of a QThread
        self.wait()

    def run(self):  # also a required QThread function, the working part
        starttime = time.time() # starting time
        self.active = True # flag for exit procedure management
        self.currents = True # flag for currents measuring management
        while self.active:
            try:

                if ard.inWaiting() > 0: # Do not do anything if there are no characters to read
                    while True:
                        data = ard.readline().decode() # read data and decode
                        # print(repr(data))
                        if not data:
                            break
                        words = data.split()

                        if words[0] == "inizio:" and len(words) == 8: # CHANGE accordingly to Arduino code!!!
                            # Extract the data
                            ddpp = float(words[1]) # dew point
                            ttchip = float(words[2]) # T_NTC
                            ttcold = float(words[3]) # T_cold side
                            tthot = float(words[4]) # T_hot side
                            delta_hc = abs(float(words[5])) # T_hot - T_cold
                            delta_cc = float(words[6]) # T_NTC - T_cold
                            delta_dc = float(words[7]) # T_cold - dew point
                            delta_ch = ttchip-tthot # T_NTC - T_hot
                            delta_dh = tthot-ddpp #T_hot - dew point

                            tt = time.time()-starttime # extract the time

                            # self.data structure: time,dew point,T_NTC,T_Cold,T_hot,Delta_ColdNTC,Delta_DpNTC,Delta_NTCHot,Delta_DpHot,I_HV,I_pwell,I_psub

                            self.data_set[0].append(tt)
                            self.data_set[1].append(ddpp)
                            self.data_set[2].append(ttchip)
                            self.data_set[3].append(ttcold)
                            self.data_set[4].append(tthot)
                            self.data_set[5].append(delta_hc)
                            self.data_set[6].append(delta_cc)
                            self.data_set[7].append(delta_dc)
                            self.data_set[8].append(delta_ch)
                            self.data_set[9].append(delta_dh)

                            # Currents' part managed by the currents flag
                            if self.currents:
                                i_hv = self.keithley3.current*1000 # I_HV converted in mA
                                i_pwell = self.keithley2.current*1000 # I_pwell converted in mA
                                i_psub = self.keithley1.current*1000 # I_psub converted in mA
                                self.data_set[10].append(i_hv)
                                self.data_set[11].append(i_pwell)
                                self.data_set[12].append(i_psub)
                            else:
                                i_hv = 0
                                i_pwell = 0
                                i_psub = 0
                            # Signal with the new data
                            self.dataChanged.emit(tt,ddpp,ttchip,ttcold,tthot,delta_hc,delta_cc,delta_dc,delta_ch,delta_dh,i_hv,i_pwell,i_psub)
            except Empty:
                print("Empty")
                continue


    def stop(self):
        """Method to safely stop the thread"""
        # Set the thread managing flag to False
        self.active = False
        # Close the output data file
        self.output_data_file.close()

class MplCanvas(FigureCanvas):
    """
    A subclass of FigureCanvas, required for creating widgets with plots.
    It has been optimized to work with more than 1 subplot but the class itself
    should work fine with just one of them.

    Parameters:
    - subs (int): default = 1, it is the number of subplots in the vertical diretion;
    - tit (str or list of str): default = None, it is the title or the list of
    the titles of the subplot(s);
    - xlab (str or list of str): default = None, it is the label or the list of
    the labels of the x axis of the subplot(s);
    - ylab (str or list of str): default = None, it is the label or the list of
    the labels of the y axis of the subplot(s);
    """

    def __init__(self, parent=None,subs = 1,tit=None,xlab=None,ylab=None):
        self.fig,self.axes = plt.subplots(subs,1,sharex=False)
        self.titles = tit
        self.xlabs = xlab
        self.ylabs = ylab
        # Styling of the subplot(s)
        if subs >1:
            for t,tt in enumerate(tit):
                self.axes[t].set_title(tt)
                self.axes[t].set_xlabel(xlab[t])
                self.axes[t].set_ylabel(ylab[t])
        elif subs == 1:
            self.axes.set_title(tit)
            self.axes.set_xlabel(xlab)
            self.axes.set_ylabel(ylab)
        # Preparing the lists with the infos about the plotted data and graphical charachteristics
        self.data_indx = [[] for i in range(subs)]
        self.line_colors = [[] for i in range(subs)]
        self.line_labels = [[] for i in range(subs)]
        super().__init__(self.fig)


class MainWindow(QtWidgets.QMainWindow):
    """
    A subclass of QtWidgets.QMainWindow, it is where the GUI is implemented.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Window and Tabs configuration
        self.setWindowTitle("C & T monitor")

        tabs = QTabWidget()

        temps = QWidget()
        currs = QWidget()

        tabs.addTab(temps, "Temperatures")
        tabs.addTab(currs, "Currents")

        # Layout of first tab (Temperatures)
        layout_temps = QVBoxLayout()

        # Last T_NTC widget
        self.last_T_NTC = QLabel(" T_NTC = --.-- *C ")
        font_NTC = self.last_T_NTC.font()
        font_NTC.setPointSize(20)
        self.last_T_NTC.setFont(font_NTC)

        # Operating mode widget(s)
        self.descr = QLabel("Select the monitoring mode: ")
        font_descr = self.descr.font()
        font_descr.setPointSize(20)
        self.descr.setFont(font_descr)

        self.heat_or_cool = QComboBox()
        self.heat_or_cool.addItems(["Cooling Mode","Heating Mode"])
        font_hc = self.heat_or_cool.font()
        font_hc.setPointSize(20)
        self.heat_or_cool.setFont(font_hc)
        self.heat_or_cool.currentIndexChanged.connect(self.index_changed)

        # Configuration of the plots
        labs_temp = [["Temperatures","Temperature Deltas","Temperature Deltas"],["T [*C]","Delta T [*C]","Delta T [*C]"],["Time [s]","Time [s]","Time [s]"]]
        self.temp_plot = MplCanvas(self,tit=labs_temp[0],ylab=labs_temp[1],xlab=labs_temp[2],subs=3)
        self.toolbar_temp = NavigationToolbar(self.temp_plot, self)
        self.temp_plot.data_indx[0].append(1)
        self.temp_plot.data_indx[0].append(2)
        self.temp_plot.data_indx[0].append(3)
        self.temp_plot.data_indx[0].append(4)
        self.temp_plot.line_colors[0].append("r")
        self.temp_plot.line_colors[0].append("b")
        self.temp_plot.line_colors[0].append("cyan")
        self.temp_plot.line_colors[0].append("green")
        self.temp_plot.line_labels[0] = ["Dew point","T_NTC chip","T_cold side Peltier","T_hot  side Peltier"]

        self.temp_plot.data_indx[1].append(7)
        self.temp_plot.line_colors[1].append("r")
        self.temp_plot.line_labels[1] = ["T_cold-Dew point"]

        self.temp_plot.data_indx[2].append(5)
        self.temp_plot.data_indx[2].append(6)
        self.temp_plot.line_colors[2].append("r")
        self.temp_plot.line_colors[2].append("b")
        self.temp_plot.line_labels[2] = ["|T_hot-T_cold|","T_NTC-T_cold"]
        self.temp_plot.fig.tight_layout()

        # Layout construction
        layout_mode = QHBoxLayout()
        layout_mode.addWidget(self.last_T_NTC)
        layout_mode.addWidget(self.descr)
        layout_mode.addWidget(self.heat_or_cool)
        layout_temps.addLayout(layout_mode)

        layout_temps.addWidget(self.toolbar_temp)
        self.temp_plot.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        layout_temps.addWidget(self.temp_plot)

        tabs.setTabText(0, "Temperatures")
        temps.setLayout(layout_temps)

        # Layout of second tab (Currents)
        layout_currs = QVBoxLayout()
        layout_meass = QHBoxLayout()

        # Configuration of the plots
        labs_currs = [["I_HV","I_DC"],["I [mA]","I [mA]"],["Time [s]","Time [s]"]]
        self.curr_plot = MplCanvas(self,tit=labs_currs[0],ylab=labs_currs[1],xlab=labs_currs[2],subs=2)
        self.curr_plot.data_indx[0].append(10)
        self.curr_plot.line_colors[0].append("r")
        self.curr_plot.line_labels[0] = ["I_HV"]

        self.curr_plot.data_indx[1].append(11)
        self.curr_plot.data_indx[1].append(12)
        self.curr_plot.line_colors[1].append("green")
        self.curr_plot.line_colors[1].append("b")
        self.curr_plot.line_labels[1] = ["I_pwell","I_psub"]
        self.curr_plot.fig.tight_layout()

        # Stop Acquisition Button configuration
        self.stop_cur = QPushButton("Stop Acquisition")
        self.stop_cur.setCheckable(False)
        self.stop_cur.clicked.connect(self.stop_acq)
        self.stop_cur.setMaximumSize(300,70)
        font_cur = self.stop_cur.font()
        font_cur.setPointSize(20)
        self.stop_cur.setFont(font_cur)

        # Last currents widgets configuration
        self.last_IHV = QLabel(" I_HV = 0.000 mA  ")
        font_HV = self.last_IHV.font()
        font_HV.setPointSize(30)
        self.last_IHV.setFont(font_HV)
        self.last_Ipwell = QLabel("I_pwell = 0.000 mA  ")
        font_pwell = self.last_Ipwell.font()
        font_pwell.setPointSize(30)
        self.last_Ipwell.setFont(font_pwell)
        self.last_Ipsub = QLabel("I_psub = 0.000 mA ")
        font_psub = self.last_Ipsub.font()
        font_psub.setPointSize(30)
        self.last_Ipsub.setFont(font_psub)

        # Layout(s) construction
        layout_meass.addWidget(self.last_IHV)
        layout_meass.addWidget(self.last_Ipwell)
        layout_meass.addWidget(self.last_Ipsub)

        layout_currs.addWidget(self.stop_cur)
        layout_currs.addLayout(layout_meass)

        self.toolbar_currs = NavigationToolbar(self.curr_plot, self)
        self.curr_plot.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        layout_currs.addWidget(self.toolbar_currs)
        layout_currs.addWidget(self.curr_plot)

        tabs.setTabText(1, "Currents")

        currs.setLayout(layout_currs)

        # Utility lists
        self.plots = [self.temp_plot,self.curr_plot]
        self.labels = [["Temperatures","Time [s]","T [*C]"],["Temperature Deltas","Time [s]","Delta T [*C]"],["Temperature Deltas","Time [s]","Delta T [*C]"],["I_HV","Time [s]","I [mA]"],["I_DC","Time [s]","I [mA]"]]

        # Data list initialization
        self.data = []
        for i in range(13):
            self.data.append([])

        # Thread initialization
        self.queue = Queue()
        self.thread = QtCore.QThread(self)
        self.receiver = GetData(self.queue)
        self.receiver.moveToThread(self.thread)
        self.thread.started.connect(self.receiver.run)
        self.receiver.dataChanged.connect(self.onDataChanged)

        self.thread.start()

        self.setCentralWidget(tabs)

        self.show()

    def closeEvent(self, event):
        """
        Method called at the closing of the window.
        We stop the thread by setting the flag to False, quitting the
        thread and waiting for it to actually finish.
        """
        print('Closing the application...')
        self.receiver.stop()  # Sets the active flag to False
        self.thread.quit()
        self.thread.wait()

    def index_changed(self,i):
        """
        Method called when the operating mode is changed.
        We change the temperature plots.
        """
        # Cooling
        if i == 0:
            self.temp_plot.line_labels[0] = ["Dew point","T_NTC chip","T_cold side Peltier","T_hot  side Peltier"]
            self.temp_plot.data_indx[1][0] = 7
            self.temp_plot.data_indx[2][1] = 6

        # Heating
        elif i == 1:
            self.temp_plot.line_labels[0] = ["Dew point","T_NTC chip","T_hot  side Peltier","T_cold side Peltier"]
            self.temp_plot.data_indx[1][0] = 9
            self.temp_plot.data_indx[2][1] = 8

    def stop_acq(self):
        """
        Method called when the Stop Acquisition Button is clicked.
        When the acquisition is stopped the button's label is changed to
        Restart Acquisition.
        """
        # Stopping
        if self.receiver.currents:
            self.receiver.currents = False
            self.stop_cur.setText("Restart Acquisition")
        # Restarting
        else:
            self.receiver.currents = True
            self.stop_cur.setText("Stop Acquisition")

    def onDataChanged(self,a,b,c,d,e,f,g,h,i,j,k,l,m):
        """
        Method called with the Data Changed signal of the Thread.
        It takes 13 floats as inputs and distributes them to the
        corresponding data sublist.
        It also writes on the output data file if the active flag
        is set to True.
        It then updates the plots and the labels widgets.
        """
        # Number of points shown
        N_show = 150
        N = min(N_show,len(self.data[0]))

        # Data distribution
        t = self.data[0][-N:]
        t.append(a)
        dp = self.data[1][-N:]
        dp.append(b)
        tchip= self.data[2][-N:]
        tchip.append(c)
        tcold = self.data[3][-N:]
        tcold.append(d)
        thot= self.data[4][-N:]
        thot.append(e)
        del_hc= self.data[5][-N:]
        del_hc.append(f)
        del_cc= self.data[6][-N:]
        del_cc.append(g)
        del_dc= self.data[7][-N:]
        del_dc.append(h)
        del_ch= self.data[8][-N:]
        del_ch.append(i)
        del_dh= self.data[9][-N:]
        del_dh.append(j)
        i_hv= self.data[10][-N:]
        i_hv.append(k)
        i_pwell= self.data[11][-N:]
        i_pwell.append(l)
        i_psub= self.data[12][-N:]
        i_psub.append(m)

        self.data[0] = t
        self.data[1] = dp
        self.data[2] = tchip
        self.data[3] = tcold
        self.data[4] = thot
        self.data[5] = del_hc
        self.data[6] = del_cc
        self.data[7] = del_dc
        self.data[8] = del_ch
        self.data[9] = del_dh
        self.data[10] = i_hv
        self.data[11] = i_pwell
        self.data[12] = i_psub

        # Writing on the output data file
        line = "{0} {1} {2} {3} {4} {5} {6} {7} {8} {9} {10} {11} {12}\n".format(a,b,c,d,e,f,g,h,i,j,k,l,m)
        if self.receiver.output_data_file.closed:
            print("Not saving data anymore: file closed")
        else:
            self.receiver.output_data_file.write(line)

        # Updating of the plots
        for i,pl in enumerate(self.plots):
            for j,ax in enumerate(pl.axes):
                ax.cla()  # Clear the canvas.
                ax.grid()
                for k, ind in enumerate(pl.data_indx[j]):
                    y_indx = ind
                    ax.plot(self.data[0], self.data[y_indx],color= pl.line_colors[j][k],label=pl.line_labels[j][k])
                ax.set_title(pl.titles[j])
                ax.set_xlabel(pl.xlabs[j])
                ax.set_ylabel(pl.ylabs[j])
                if i == 0:
                    if j == 1:
                        ax.hlines(5,min(t)-.5,max(t)+.5,colors="red",label="Min for Peltier (T_cold-dew point)",linestyles="dashed")
                ax.legend(loc = "upper left")
            pl.fig.tight_layout()
            pl.draw()

        # Updating of the temperature and currents labels
        t_ntc = " T_NTC = %.2f *C " % (self.data[2][-1])
        ihv = " I_HV = %.4f mA  " % (self.data[10][-1]*1000)
        ipwell = "I_pwell = %.4f mA  " % (self.data[11][-1]*1000)
        ipsub = "I_psub = %.4f mA " % (self.data[12][-1]*1000)
        self.last_T_NTC.setText(t_ntc)
        self.last_IHV.setText(ihv)
        self.last_Ipwell.setText(ipwell)
        self.last_Ipsub.setText(ipsub)

app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
app.exec_()