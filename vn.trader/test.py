import  numpy as np
class FFT_Plot():
    def __init__(self, win, nSamples, aData, sRate, wFunction,
                 zStart=0):
        self.nSamples = nSamples  # Number of Sample must be a 2^n power
        self.aData = aData # Amplitude data array
        self.sRate = sRate # Sample Rate as Frequency
        self.wFunction = wFunction # Windowing Function
        self.zStart = zStart # Start of Zoom Window if Used
        self.zStop = nSamples/2 # End of Zoom Window if Used # Instantiate a plot window within an existing pyQtGraph window.
        self.plot = win.addPlot(title="FFT")
        self.update(aData)
        self.grid_state()
        self.plot.setLabel('left', 'Amplitude', 'Volts')
        self.plot.setLabel('bottom', 'Frequency', 'Hz')
    def update(self, aData):
        x = np.fft.fft(aData,)
        amplitude = np.absolute(x) # Create a linear scale based on the Sample Rate and Number of Samples.
        fScale = np.linspace(0 , self.sRate, self.nSamples)
        self.plot.plot(x = fScale, y = amplitude, pen={'color': (0, 0, 0), 'width': 2})  # to set any range limits you must use the sRate.
        self.plot.setXRange(self.sRate/2, 0)
    def grid_state(self, x = True, y = True):
        self.plot.showGrid(x, y)
def main():
    f = FFT_Plot( win, nSamples, aData, sRate, wFunction,
                 zStart=0)

if __name__ == '__main__':
    main()