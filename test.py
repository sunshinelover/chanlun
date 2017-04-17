# from PyQt4 import QtCore
# import pyqtgraph as pg
# import numpy as np
#
#
# class MyStringAxis(pg.AxisItem):
#     def __init__(self, xdict, *args, **kwargs):
#         pg.AxisItem.__init__(self, *args, **kwargs)
#         self.x_values = np.asarray(xdict.keys())
#         self.x_strings = xdict.values()
#
#     def tickStrings(self, values, scale, spacing):
#         strings = []
#         for v in values:
#             # vs is the original tick value
#             vs = v * scale
#             # if we have vs in our values, show the string
#             # otherwise show nothing
#             if vs in self.x_values:
#                 # Find the string with x_values closest to vs
#                 vstr = self.x_strings[np.abs(self.x_values - vs).argmin()]
#             else:
#                 vstr = ""
#             strings.append(vstr)
#         return strings
#
#
# x = [u'21:00', u'21:05', u'21:10', u'21:15', u'21:20', u'21:25']
# # y = [1, 2, 3, 4, 5, 6]
# xdict = dict(enumerate(x))
#
# win = pg.GraphicsWindow()
# stringaxis = MyStringAxis(xdict, orientation='bottom')
# plot = win.addPlot(axisItems={'bottom': stringaxis})
# # curve = plot.plot(xdict.keys(), y)

if __name__ == '__main__':
    unit = 1
    print unit
    unit = 'daily'
    print unit