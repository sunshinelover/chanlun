''' Setting x-axis labels for time series
Window, pyqtgraph (09.10) numpy (1.11.1) PyQt4(4.11.4)
'''

import datetime as dt
from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg

def main():
    app = QtGui.QApplication([])
    #Plot some data for 2 days
    x=np.arange(0.0, 1.0, 0.02)
    day0=100*np.sin(2*np.pi*x)   # Just som data to plot
    day1=100*(np.cos(2*np.pi*x)-1)   # Just som data to plot
    xx=np.concatenate([x,x+1]) # two days
    yy=np.concatenate([day0,day1])

    win = pg.PlotWidget(title="Plotting time series")
    win.resize(1600,400)
    win.plot(xx,yy)

    # Tick labels
    tr=np.arange('2016-06-10 09:00', '2016-06-11 18:00', dtype='datetime64[2h]') # tick labels one day
    tday0=(tr-tr[0])/(tr[-1]-tr[0])  #Map time to 0.0-1.0 day 2 1.0-2.0 ...
    tday1=tday0+1
    tnorm=np.concatenate([tday0,tday1])
    tr[-1]=tr[0]  # End day=start next day
    # Create tick labels for axis.setTicks
    ttick=list()
    for i,t in enumerate(np.concatenate([tr,tr])):
        tstr=np.datetime64(t).astype(dt.datetime)
        ttick.append(  (tnorm[i],  tstr.strftime("%H:%M:%S")))

    ax=win.getAxis('bottom')    #This is the trick
    ax.setTicks([ttick])

    # Set grid x and y-axis
    ax.setGrid(255)
    ay=win.getAxis('left')
    ay.setGrid(255)

    win.show()
    app.exec_()

if __name__ == '__main__':
    main()