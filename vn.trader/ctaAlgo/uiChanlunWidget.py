# encoding: UTF-8

"""
缠论模块相关的GUI控制组件
"""
from vtGateway import VtSubscribeReq
from uiBasicWidget import QtGui, QtCore, BasicCell,BasicMonitor,TradingWidget
from eventEngine import *
from ctaBase import *
import pyqtgraph as pg
import numpy as np
import pymongo
from pymongo.errors import *
from datetime import datetime, timedelta
from ctaHistoryData import HistoryDataEngine
import time
import types
import pandas as pd
########################################################################
class MyStringAxis(pg.AxisItem):
    def __init__(self, xdict, *args, **kwargs):
        pg.AxisItem.__init__(self, *args, **kwargs)
        self.x_values = np.asarray(xdict.keys())
        self.x_strings = xdict.values()

    def tickStrings(self, values, scale, spacing):
        strings = []
        for v in values:
            # vs is the original tick value
            vs = v * scale
            # if we have vs in our values, show the string
            # otherwise show nothing
            if vs in self.x_values:
                # Find the string with x_values closest to vs
                vstr = self.x_strings[np.abs(self.x_values - vs).argmin()]
            else:
                vstr = ""
            strings.append(vstr)
        return strings

########################################################################
class ChanlunEngineManager(QtGui.QWidget):
    """chanlun引擎管理组件"""
    signal = QtCore.pyqtSignal(type(Event()))

    # ----------------------------------------------------------------------
    def __init__(self, chanlunEngine, eventEngine, mainEngine, parent=None):
        """Constructor"""
        super(ChanlunEngineManager, self).__init__(parent)

        self.chanlunEngine = chanlunEngine
        self.eventEngine = eventEngine
        self.mainEngine = mainEngine

        self.penLoaded = False
        self.segmentLoaded = False
        self.tickLoaded = False
        self.zhongShuLoaded = False
        self.instrumentid = ''

        self.initUi()
        self.registerEvent()

        # 记录日志
        self.chanlunEngine.writeChanlunLog(u'缠论引擎启动成功')

        # ----------------------------------------------------------------------

    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'缠论策略')

        # 期货代码输入框
        self.codeEdit = QtGui.QLineEdit()
        self.codeEdit.setPlaceholderText(u'在此输入期货代码')
        self.codeEdit.setMaximumWidth(200)
        self.data = pd.DataFrame() #画图所需数据, 重要
        self.fenX = [] #分笔分段所需X轴坐标
        self.fenY = [] #分笔分段所需Y轴坐标
        self.zhongshuPos = [] #中枢的位置
        self.zhongShuType = [] #中枢的方向
        # 金融图
        self.PriceW = PriceWidget(self.eventEngine, self.chanlunEngine, self.data)
        self.TickW = None

        # MongoDB数据库相关
        self.__mongoConnected = False
        self.__mongoConnection = None

        # 调用函数
        self.__connectMongo()

        # 按钮
        penButton = QtGui.QPushButton(u'分笔')
        segmentButton = QtGui.QPushButton(u'分段')
        zhongshuButton = QtGui.QPushButton(u'走势中枢')
        shopButton = QtGui.QPushButton(u'买卖点')
        restoreButton = QtGui.QPushButton(u'还原')

        penButton.clicked.connect(self.pen)
        segmentButton.clicked.connect(self.segment)
        zhongshuButton.clicked.connect(self.zhongShu)
        shopButton.clicked.connect(self.shop)
        restoreButton.clicked.connect(self.restore)

        # Chanlun组件的日志监控
        self.chanlunLogMonitor = QtGui.QTextEdit()
        self.chanlunLogMonitor.setReadOnly(True)
        self.chanlunLogMonitor.setMaximumHeight(180)

        # 设置布局
        self.hbox2 = QtGui.QHBoxLayout()
        self.hbox2.addWidget(self.codeEdit)
        self.hbox2.addWidget(penButton)
        self.hbox2.addWidget(segmentButton)
        self.hbox2.addWidget(zhongshuButton)
        self.hbox2.addWidget(shopButton)
        self.hbox2.addWidget(restoreButton)
        self.hbox2.addStretch()


        tickButton = QtGui.QPushButton(u'Tick')
        oneMButton = QtGui.QPushButton(u"1分")
        fiveMButton = QtGui.QPushButton(u'5分')
        fifteenMButton = QtGui.QPushButton(u'15分')
        thirtyMButton = QtGui.QPushButton(u'30分')
        sixtyMButton = QtGui.QPushButton(u'60分')
        dayButton = QtGui.QPushButton(u'日')
        weekButton = QtGui.QPushButton(u'周')
        monthButton = QtGui.QPushButton(u'月')

        oneMButton.checked = True

        self.vbox1 = QtGui.QVBoxLayout()

        tickButton.clicked.connect(self.openTick)
        oneMButton.clicked.connect(self.oneM)
        fiveMButton.clicked.connect(self.fiveM)
        fifteenMButton.clicked.connect(self.fifteenM)
        thirtyMButton.clicked.connect(self.thirtyM)
        sixtyMButton.clicked.connect(self.sixtyM)
        dayButton.clicked.connect(self.daily)
        weekButton.clicked.connect(self.weekly)
        monthButton.clicked.connect(self.monthly)

        self.vbox2 = QtGui.QVBoxLayout()
        self.vbox1.addWidget(self.PriceW)
        self.vbox2.addWidget(tickButton)
        self.vbox2.addWidget(oneMButton)
        self.vbox2.addWidget(fiveMButton)
        self.vbox2.addWidget(fifteenMButton)
        self.vbox2.addWidget(thirtyMButton)
        self.vbox2.addWidget(sixtyMButton)
        self.vbox2.addWidget(dayButton)
        self.vbox2.addWidget(weekButton)
        self.vbox2.addWidget(monthButton)
        self.vbox2.addStretch()

        self.hbox3 = QtGui.QHBoxLayout()
        self.hbox3.addStretch()
        self.hbox3.addLayout(self.vbox1)
        self.hbox3.addLayout(self.vbox2)

        self.vbox = QtGui.QVBoxLayout()
        self.vbox.addLayout(self.hbox2)
        self.vbox.addLayout(self.hbox3)
        self.vbox.addWidget(self.chanlunLogMonitor)
        self.setLayout(self.vbox)


        self.codeEdit.returnPressed.connect(self.updateSymbol)

    #-----------------------------------------------------------------------
    #从通联数据端获取历史数据
    def downloadData(self, symbol, unit):
        listBar = [] #K线数据
        num = 0

        #从通联客户端获取K线数据
        historyDataEngine = HistoryDataEngine()

        # unit为int型获取分钟数据，为String类型获取日周月K线数据
        if type(unit) is types.IntType:
            #从通联数据端获取当日分钟数据并存入数据库
            historyDataEngine.downloadFuturesIntradayBar(symbol, unit)
            # 从数据库获取前几天的分钟数据
            cx = self.getDbData(symbol, unit)
            if cx:
                for data in cx:
                    barOpen = data['open']
                    barClose = data['close']
                    barLow = data['low']
                    barHigh = data['high']
                    barTime = data['datetime']
                    listBar.append((num, barTime, barOpen, barClose, barLow, barHigh))
                    num += 1

        elif type(unit) is types.StringType:
            data = historyDataEngine.downloadFuturesBar(symbol, unit)
            if data:
                for d in data:
                    barOpen = d.get('openPrice', 0)
                    barClose = d.get('closePrice', 0)
                    barLow = d.get('lowestPrice', 0)
                    barHigh = d.get('highestPrice', 0)
                    if unit == "daily":
                        barTime = d.get('tradeDate', '').replace('-', '')
                    else:
                        barTime = d.get('endDate', '').replace('-', '')
                    listBar.append((num, barTime, barOpen, barClose, barLow, barHigh))
                    num += 1
                if unit == "monthly" or unit == "weekly":
                    listBar.reverse()
        else:
            print "参数格式错误"
            return

        #将List数据转换成dataFormat类型，方便处理
        df = pd.DataFrame(listBar, columns=['num', 'time', 'open', 'close', 'low', 'high'])
        df.index = df['time'].tolist()
        df = df.drop('time', 1)
        return df
    #-----------------------------------------------------------------------
    #从数据库获取前两天的分钟数据
    def getDbData(self, symbol, unit):
        #周六周日不交易，无分钟数据
        # 给数据库命名
        dbname = ''
        days = 7
        if unit == 1:
            dbname = MINUTE_DB_NAME
        elif unit == 5:
            dbname = MINUTE5_DB_NAME
        elif unit == 15:
            dbname = MINUTE15_DB_NAME
        elif unit == 30:
            dbname = MINUTE30_DB_NAME
        elif unit == 60:
            dbname = MINUTE60_DB_NAME

        weekday = datetime.now().weekday()  # weekday() 返回的是0-6是星期一到星期日
        if days == 2:
            if weekday == 6:
                aDay = timedelta(days=3)
            elif weekday == 0 or weekday == 1:
                aDay = timedelta(days=4)
            else:
                aDay = timedelta(days=2)
        else:
            aDay = timedelta(days=7)

        startDate = (datetime.now() - aDay).strftime('%Y%m%d')
        print startDate
        if self.__mongoConnected:
            collection = self.__mongoConnection[dbname][symbol]
            cx = collection.find({'date': {'$gte': startDate}})
            return cx
        else:
            return None
    #----------------------------------------------------------------------------------
    #"""合约变化"""
    def updateSymbol(self):
        # 读取组件数据
        instrumentid = str(self.codeEdit.text())

        self.chanlunEngine.writeChanlunLog(u'查询合约%s' % (instrumentid))

        # 从通联数据客户端获取当日分钟数据
        self.data = self.downloadData(instrumentid, 1)

        if self.data.empty:
            self.chanlunEngine.writeChanlunLog(u'合约%s 不存在' % (instrumentid))
        else:
            if self.tickLoaded:
                self.vbox1.removeWidget(self.TickW)
                self.TickW.deleteLater()
            else:
                self.vbox1.removeWidget(self.PriceW)
                self.PriceW.deleteLater()

            self.PriceW = PriceWidget(self.eventEngine, self.chanlunEngine, self.data)
            self.vbox1.addWidget(self.PriceW)
            # 画K线图
            self.PriceW.plotHistorticData()

            self.chanlunEngine.writeChanlunLog(u'打开合约%s 1分钟K线图' % (instrumentid))

            self.penLoaded = False
            self.segmentLoaded = False
            self.tickLoaded = False
            self.zhongShuLoaded = False

            # # 订阅合约[仿照ctaEngine.py写的]
            # # 先取消订阅之前的合约，再订阅最新输入的合约
            # contract = self.mainEngine.getContract(self.instrumentid)
            # if contract:
            #     req = VtSubscribeReq()
            #     req.symbol = contract.symbol
            #     self.mainEngine.unsubscribe(req, contract.gatewayName)
            #
            #     contract = self.mainEngine.getContract(instrumentid)
            #     if contract:
            #         req = VtSubscribeReq()
            #         req.symbol = contract.symbol
            #         self.mainEngine.subscribe(req, contract.gatewayName)
            #     else:
            #         self.chanlunEngine.writeChanlunLog(u'交易合约%s无法找到' % (instrumentid))
            #
            # # 重新注册事件监听
            # self.eventEngine.unregister(EVENT_TICK + self.instrumentid, self.signal.emit)
            # self.eventEngine.register(EVENT_TICK + instrumentid, self.signal.emit)

            # 更新目前的合约
            self.instrumentid = instrumentid

    def oneM(self):
        "打开1分钟K线图"
        self.chanlunEngine.writeChanlunLog(u'打开合约%s 1分钟K线图' % (self.instrumentid))
        # 从通联数据客户端获取数据
        self.data = self.downloadData(self.instrumentid, 1)

        if self.tickLoaded:
            self.vbox1.removeWidget(self.TickW)
            self.TickW.deleteLater()
        else:
            self.vbox1.removeWidget(self.PriceW)
            self.PriceW.deleteLater()

        self.PriceW = PriceWidget(self.eventEngine, self.chanlunEngine, self.data)
        self.vbox1.addWidget(self.PriceW)

        # 画K线图
        self.PriceW.plotHistorticData()

        self.tickLoaded = False
        self.penLoaded = False
        self.segmentLoaded = False
        self.zhongShuLoaded = False

    # ----------------------------------------------------------------------
    def fiveM(self):
        "打开5分钟K线图"
        self.chanlunEngine.writeChanlunLog(u'打开合约%s 5分钟K线图' % (self.instrumentid))

        # 从通联数据客户端获取数据
        self.data = self.downloadData(self.instrumentid, 5)

        if self.tickLoaded:
            self.vbox1.removeWidget(self.TickW)
            self.TickW.deleteLater()
        else:
            self.vbox1.removeWidget(self.PriceW)
            self.PriceW.deleteLater()

        self.PriceW = PriceWidget(self.eventEngine, self.chanlunEngine, self.data)
        self.vbox1.addWidget(self.PriceW)

        # 画K线图
        self.PriceW.plotHistorticData()

        self.tickLoaded = False
        self.penLoaded = False
        self.segmentLoaded = False
        self.zhongShuLoaded = False


    # ----------------------------------------------------------------------
    def fifteenM(self):
        "打开15分钟K线图"
        self.chanlunEngine.writeChanlunLog(u'打开合约%s 15分钟K线图' % (self.instrumentid))

        # 从通联数据客户端获取数据
        self.data = self.downloadData(self.instrumentid, 15)

        if self.tickLoaded:
            self.vbox1.removeWidget(self.TickW)
            self.TickW.deleteLater()
        else:
            self.vbox1.removeWidget(self.PriceW)
            self.PriceW.deleteLater()

        self.PriceW = PriceWidget(self.eventEngine, self.chanlunEngine, self.data)
        self.vbox1.addWidget(self.PriceW)

        # 画K线图
        self.PriceW.plotHistorticData()

        self.tickLoaded = False
        self.penLoaded = False
        self.segmentLoaded = False
        self.zhongShuLoaded = False

    # ----------------------------------------------------------------------
    def thirtyM(self):
        "打开30分钟K线图"
        self.chanlunEngine.writeChanlunLog(u'打开合约%s 30分钟K线图' % (self.instrumentid))
        # 从通联数据客户端获取数据
        self.data = self.downloadData(self.instrumentid, 30)

        if self.tickLoaded:
            self.vbox1.removeWidget(self.TickW)
            self.TickW.deleteLater()
        else:
            self.vbox1.removeWidget(self.PriceW)
            self.PriceW.deleteLater()

        self.PriceW = PriceWidget(self.eventEngine, self.chanlunEngine, self.data)
        self.vbox1.addWidget(self.PriceW)

        # 画K线图
        self.PriceW.plotHistorticData()

        self.tickLoaded = False
        self.penLoaded = False
        self.segmentLoaded = False
        self.zhongShuLoaded = False


    # ----------------------------------------------------------------------
    def sixtyM(self):
        "打开60分钟K线图"
        self.chanlunEngine.writeChanlunLog(u'打开合约%s 60分钟K线图' % (self.instrumentid))
        # 从通联数据客户端获取数据
        self.data = self.downloadData(self.instrumentid, 60)

        if self.tickLoaded:
            self.vbox1.removeWidget(self.TickW)
            self.TickW.deleteLater()
        else:
            self.vbox1.removeWidget(self.PriceW)
            self.PriceW.deleteLater()

        self.PriceW = PriceWidget(self.eventEngine, self.chanlunEngine, self.data)
        self.vbox1.addWidget(self.PriceW)

        # 画K线图
        self.PriceW.plotHistorticData()

        self.tickLoaded = False
        self.penLoaded = False
        self.segmentLoaded = False
        self.zhongShuLoaded = False


    # ----------------------------------------------------------------------
    def daily(self):
        """打开日K线图"""
        self.chanlunEngine.writeChanlunLog(u'打开合约%s 日K线图' % (self.instrumentid))
        # 从通联数据客户端获取数据
        self.data = self.downloadData(self.instrumentid, "daily")

        if self.tickLoaded:
            self.vbox1.removeWidget(self.TickW)
            self.TickW.deleteLater()
        else:
            self.vbox1.removeWidget(self.PriceW)
            self.PriceW.deleteLater()

        self.PriceW = PriceWidget(self.eventEngine, self.chanlunEngine, self.data)
        self.vbox1.addWidget(self.PriceW)

        # 画K线图
        self.PriceW.plotHistorticData()

        self.tickLoaded = False
        self.penLoaded = False
        self.segmentLoaded = False
        self.zhongShuLoaded = False
        
    # ----------------------------------------------------------------------
    def weekly(self):
        """打开周K线图"""
        self.chanlunEngine.writeChanlunLog(u'打开合约%s 周K线图' % (self.instrumentid))
        # 从通联数据客户端获取数据
        self.data = self.downloadData(self.instrumentid, "weekly")
        
        if self.tickLoaded:
            self.vbox1.removeWidget(self.TickW)
            self.TickW.deleteLater()
        else:
            self.vbox1.removeWidget(self.PriceW)
            self.PriceW.deleteLater()

        self.PriceW = PriceWidget(self.eventEngine, self.chanlunEngine, self.data)
        self.vbox1.addWidget(self.PriceW)

        # 画K线图
        self.PriceW.plotHistorticData()

        self.tickLoaded = False
        self.penLoaded = False
        self.segmentLoaded = False
        self.zhongShuLoaded = False
    
    def monthly(self):
        """打开月K线图"""
        self.chanlunEngine.writeChanlunLog(u'打开合约%s 月K线图' % (self.instrumentid))
        # 从通联数据客户端获取数据并画图
        self.data = self.downloadData(self.instrumentid, "monthly")
        
        if self.tickLoaded:
            self.vbox1.removeWidget(self.TickW)
            self.TickW.deleteLater()
        else:
            self.vbox1.removeWidget(self.PriceW)
            self.PriceW.deleteLater()

        self.PriceW = PriceWidget(self.eventEngine, self.chanlunEngine, self.data)
        self.vbox1.addWidget(self.PriceW)

        # 画K线图
        self.PriceW.plotHistorticData()

        self.tickLoaded = False
        self.penLoaded = False
        self.segmentLoaded = False
        self.zhongShuLoaded = False
    # ----------------------------------------------------------------------
    def openTick(self):
        """切换成tick图"""
        self.chanlunEngine.writeChanlunLog(u'打开tick图')

        self.vbox1.removeWidget(self.PriceW)
        self.PriceW.deleteLater()
        self.TickW = TickWidget(self.eventEngine, self.chanlunEngine)
        self.vbox1.addWidget(self.TickW)

        self.tickLoaded = True
        self.penLoaded = False
        self.segmentLoaded = False
        self.zhongShuLoaded = False

    # ----------------------------------------------------------------------
    def restore(self):
        """还原初始k线状态"""
        self.chanlunEngine.writeChanlunLog(u'还原加载成功')
        if self.tickLoaded:
            self.vbox1.removeWidget(self.TickW)
            self.TickW.deleteLater()
        else:
            self.vbox1.removeWidget(self.PriceW)
            self.PriceW.deleteLater()

        self.data = self.downloadData(self.instrumentid, 1)
        self.PriceW = PriceWidget(self.eventEngine, self.chanlunEngine, self.data, self)
        self.vbox1.addWidget(self.PriceW)

        # 画K线图
        self.PriceW.plotHistorticData()

        self.chanlunEngine.writeChanlunLog(u'还原为1分钟k线图')
        self.penLoaded = False
        self.segmentLoaded = False
        self.tickLoaded = False

    # ----------------------------------------------------------------------
    def pen(self):
        """加载分笔"""
        # 先合并K线数据,记录新建PriceW之前合并K线的数据
        if not self.penLoaded:
            after_fenxing = self.judgeInclude() #判断self.data中K线数据的包含关系

            # 清空画布时先remove已有的Widget再新建
            self.vbox1.removeWidget(self.PriceW)
            self.PriceW.deleteLater()
            self.PriceW = PriceWidget(self.eventEngine, self.chanlunEngine, after_fenxing)
            self.vbox1.addWidget(self.PriceW)

            #使用合并K线的数据重新画K线图
            self.plotAfterFenXing(after_fenxing)
            # 找出顶和底
            fenxing_data, fenxing_type = self.findTopAndLow(after_fenxing)

            arrayFenxingdata = np.array(fenxing_data)
            arrayTypedata = np.array(fenxing_type)
            self.fenY = []
            self.fenX = [m[0] for m in arrayFenxingdata]
            fenbiY1 = [m[4] for m in arrayFenxingdata]  # 顶分型标志最高价
            fenbiY2 = [m[3] for m in arrayFenxingdata]  # 底分型标志最低价
            for i in xrange(len(self.fenX)):
                if arrayTypedata[i] == 1:
                    self.fenY.append(fenbiY1[i])
                else:
                    self.fenY.append(fenbiY2[i])
            if not self.penLoaded:
                if self.fenX:
                    self.fenX.append(self.fenX[-1])
                    self.fenY.append(self.fenY[-1])
                    print "self.fenX: ", self.fenX
                    print "self.fenY: ", self.fenY
                    self.fenbi(self.fenX, self.fenY)
                    self.fenX.pop()
                    self.fenY.pop()

            self.chanlunEngine.writeChanlunLog(u'分笔加载成功')
            self.penLoaded = True
    # ----------------------------------------------------------------------
    def segment(self):
        if not self.penLoaded:
            self.pen()                #先分笔才能分段
        segmentX = []    #分段点X轴值
        segmentY = []    #分段点Y轴值
        temp_type = 0    #标志线段方向，向上为1，向下为-1, 未判断前三笔是否重合为0
        i = 0
        while i < len(self.fenX) - 4:
            if temp_type == 0:
                if self.fenY[i] > self.fenY[i+1] and self.fenY[i] > self.fenY[i+3]:
                    temp_type = -1           #向下线段，三笔重合
                    segmentX.append(self.fenX[i])
                    segmentY.append(self.fenY[i])
                elif self.fenY[i] < self.fenY[i+1] and self.fenY[i] < self.fenY[i+3]:
                    temp_type = 1            #向上线段，三笔重合
                    segmentX.append(self.fenX[i])
                    segmentY.append(self.fenY[i])
                else:
                    temp_type = 0
                    i += 1
                    continue
            if temp_type == 1:  #向上线段
                j = i+1
                high = []  # 记录顶
                low = []  # 记录低
                while j < len(self.fenX) - 1:     #记录顶底
                    high.append(self.fenY[j])
                    low.append(self.fenY[j+1])
                    j += 2
                if self.fenY[i+4] < self.fenY[i+1]:    #向上线段被向下笔破坏
                    j = 0
                    while j < len(high)-2:
                        # 顶底出现顶分型，向上线段结束
                        if high[j+1] > high[j] and high[j+1] > high[j+2]:
                            num = i + 2 * j + 3   #线段结束点位置
                            segmentX.append(self.fenX[num])
                            segmentY.append(self.fenY[num])
                            i = num
                            temp_type = -1   #向上线段一定由向下线段结束
                            break
                        j += 1
                    if j == len(high)-2:
                        break
                else:   #向上线段未被向下笔破坏
                    j = 1
                    while j < len(high)-2:
                        # 顶底出现底分型，向上线段结束
                        if low[j + 1] < low[j] and low[j + 1] < low[j + 2]:
                            num = i + 2 * j + 1  # 线段结束点位置
                            segmentX.append(self.fenX[num])
                            segmentY.append(self.fenY[num])
                            i = num
                            temp_type = -1  # 向上线段一定由向下线段结束
                            break
                        j += 1
                    if j == len(high)-2:
                        break
            elif temp_type == -1:  # 向下线段
                j = i + 1
                high = []  # 记录顶
                low = []  # 记录低
                while j < len(self.fenX) - 1:  # 记录顶底
                    high.append(self.fenY[j + 1])
                    low.append(self.fenY[j])
                    j += 2
                if self.fenY[i + 4] > self.fenY[i + 1]:  # 向下线段被向上笔破坏
                    j = 0
                    while j < len(high) - 2:
                        # 顶底出现底分型，向下线段结束
                        if low[j + 1] < low[j] and low[j + 1] < low[j + 2]:
                            num = i + 2 * j + 3  # 线段结束点位置
                            segmentX.append(self.fenX[num])
                            segmentY.append(self.fenY[num])
                            i = num
                            temp_type = 1  # 向下线段一定由向上线段结束
                            break
                        j += 1
                    if j == len(high) - 2:
                        break
                else:  # 向下线段未被向上笔破坏
                    j = 1
                    while j < len(high) - 2:
                    # 顶底出现顶分型，向下线段结束
                        if high[j + 1] > high[j] and high[j + 1] > high[j + 2]:
                            num = i + 2 * j + 1  # 线段结束点位置
                            segmentX.append(self.fenX[num])
                            segmentY.append(self.fenY[num])
                            i = num
                            temp_type = 1  # 向下线段一定由向上线段结束
                            break
                        j += 1
                    if j == len(high) - 2:
                        break
        print "segmentX: ", segmentX
        print "segmentY: ", segmentY
        if not self.segmentLoaded:
            if len(segmentX) > 1:
                segmentX.append(segmentX[-1])
                segmentY.append(segmentY[-1])
                segmentX = [int(x) for x in segmentX]
                segmentY = [int(y) for y in segmentY]
                self.fenduan(segmentX, segmentY)
        self.chanlunEngine.writeChanlunLog(u'分段加载成功')
        self.segmentLoaded = True
    # ----------------------------------------------------------------------
    def updateChanlunLog(self, event):
        """更新缠论相关日志"""
        log = event.dict_['data']
        # print type(log)
        if(log.logTime):
            content = '\t'.join([log.logTime, log.logContent])
            self.chanlunLogMonitor.append(content)
        else:
            print 0
    #-----------------------------------------------------------------------
    def zhongShu(self):
        if not self.penLoaded:
            self.pen()  # 先分笔才能画走势中枢
        # temp_type = 0  # 标志中枢方向，向上为1，向下为-1
        i = 0
        temp_high, temp_low = 0, 0
        minX, maxY = 0, 0
        self.zhongshuPos = []  # 记录所有的中枢开始段和结束段的位置
        self.zhongShuType = [] #记录所有中枢的方向
        while i < len(self.fenX) - 4:
            if (self.fenY[i] > self.fenY[i + 1] and self.fenY[i + 1] < self.fenY[i + 4]): #判断进入段方向
                temp_low = max(self.fenY[i + 1], self.fenY[i + 3])
                temp_high = min(self.fenY[i + 2], self.fenY[i + 4])   #记录中枢内顶的最小值与底的最大值
                minX = self.fenX[i+1]
                self.zhongshuPos.append(i)
                self.zhongShuType.append(-1)
                j = i
                while i < len(self.fenX) - 4:
                    j = i
                    if self.fenY[i + 1] < self.fenY[i + 4] and self.fenY[i + 4] > temp_low and self.fenY[i + 3] < temp_high :
                        maxX = self.fenX[i+4]
                        if self.fenY[i + 3] > temp_low:
                            temp_low = self.fenY[i + 3]
                        if self.fenY[i + 4] < temp_high:
                            temp_high = self.fenY[i + 4]
                        i = i + 1
                    elif self.fenY[i + 1] > self.fenY[i + 4] and self.fenY[i + 4] < temp_high and self.fenY[i + 3] > temp_low :
                        maxX = self.fenX[i + 4]
                        if self.fenY[i + 3] < temp_high:
                            temp_high = self.fenY[i + 3]
                        if self.fenY[i + 4] > temp_low:
                            temp_low = self.fenY[i + 4]
                        i = i + 1
                    if j == i:
                        break
            elif (self.fenY[i] < self.fenY[i + 1] and self.fenY[i + 1] > self.fenY[i + 4]):
                temp_high = min(self.fenY[i + 1], self.fenY[i + 3])
                temp_low = max(self.fenY[i + 2], self.fenY[i + 4])
                minX = self.fenX[i + 1]
                self.zhongshuPos.append(i)
                self.zhongShuType.append(1)
                j = i
                while i < len(self.fenX) - 4:
                    j = i
                    if self.fenY[i + 1] > self.fenY[i + 4] and self.fenY[i + 4] < temp_high and self.fenY[i + 3] > temp_low:
                        maxX = self.fenX[i + 4]
                        if self.fenY[i + 3] < temp_high:
                            temp_high = self.fenY[i + 3]
                        if self.fenY[i + 4] > temp_low:
                            temp_low = self.fenY[i + 4]
                        i = i + 1
                    elif self.fenY[i + 1] < self.fenY[i + 4] and self.fenY[i + 4] > temp_low and self.fenY[i + 3] < temp_high:
                        maxX = self.fenX[i + 4]
                        if self.fenY[i + 3] > temp_low:
                            temp_low = self.fenY[i + 3]
                        if self.fenY[i + 4] < temp_high:
                            temp_high = self.fenY[i + 4]
                        i = i + 1
                    if i == j:
                        break
            else:
                i += 1
                continue

            # 画出当前判断出的中枢
            if minX != 0 and maxX == 0:
                maxX = self.fenX[i+4]
                i = i + 1
                self.zhongshuPos.append(i + 4)
            else:
                self.zhongshuPos.append(i + 3)

            minY, maxY = temp_low, temp_high

            print minX, minY, maxX, maxY
            if int(maxY) > int(minY):
                plotX = [minX, minX, maxX, maxX, minX]
                plotY = [minY, maxY, maxY, minY, minY]
                plotX = [int(x) for x in plotX]
                plotY = [int(y) for y in plotY]
                self.zhongshu(plotX, plotY)

            i = i + 4

        self.zhongShuLoaded = True
        self.chanlunEngine.writeChanlunLog(u'走势中枢加载成功')

     # ----------------------------------------------------------------------
    def shop(self):
        """加载买卖点"""
        if not self.zhongShuLoaded:
            self.zhongShu()
        i = 0
        while i < len(self.zhongShuType) - 1:
            startPos, endPos = self.zhongshuPos[2*i], self.zhongshuPos[2*i + 1]  # 中枢开始段的位置和结束段的位置

            startY = self.fenY[startPos + 1] - self.fenY[startPos]  # 开始段Y轴距离
            startX = self.fenX[startPos + 1] - self.fenX[startPos]  # 开始段X轴距离
            startK = abs(startY * startX)  # 开始段投影面积

            endY = self.fenY[endPos + 1] - self.fenY[endPos]  # 结束段Y轴距离
            endX = self.fenX[endPos + 1] - self.fenX[endPos]  # 结束段段X轴距离
            endK = abs(endY * endX)  # 开始段投影面积

            if endK < startK:
                print startPos, endPos
                if self.zhongShuType[i] == 1 and self.zhongShuType[i + 1] == -1:
                    # 一卖
                    self.sellpoint([self.fenX[endPos + 1]], [self.fenY[endPos + 1]], 1)
                    # 二卖，一卖后一个顶点
                    self.sellpoint([self.fenX[endPos + 3]], [self.fenY[endPos + 3]], 2)
                    # 三卖，一卖之后中枢结束段的第一个顶
                    i = i + 1
                    nextPos = self.zhongshuPos[2*i + 1]  # 下一个中枢结束位置
                    if nextPos + 1 < len(self.fenY):
                        if self.fenY[nextPos + 1] > self.fenY[nextPos]:
                            self.sellpoint([self.fenX[nextPos + 1]], [self.fenY[nextPos + 1]], 3)
                        else:
                            self.sellpoint([self.fenX[nextPos]], [self.fenY[nextPos]], 3)
                elif self.zhongShuType[i] == -1 and self.zhongShuType[i + 1] == 1:
                    # 一买
                    self.buypoint([self.fenX[endPos + 1]], [self.fenY[endPos + 1]], 1)
                    # 二买，一买后一个底点
                    self.buypoint([self.fenX[endPos + 3]], [self.fenY[endPos + 3]], 2)
                    # 三买，一买之后中枢结束段的第一个顶
                    i = i + 1
                    nextPos = self.zhongshuPos[2*i + 1]  # 下一个中枢结束位置
                    if nextPos + 1 < len(self.fenY):
                        if self.fenY[nextPos + 1] < self.fenY[nextPos]:
                            self.buypoint([self.fenX[nextPos + 1]], [self.fenY[nextPos + 1]], 3)
                        else:
                            self.buypoint([self.fenX[nextPos]], [self.fenY[nextPos]], 3)

            i = i + 1           # 接着判断之后的中枢是否出现背驰

        self.chanlunEngine.writeChanlunLog(u'买卖点加载成功')
    # ----------------------------------------------------------------------
    def fenbi(self, fenbix, fenbiy):
        self.PriceW.pw2.plotItem.plot(x=fenbix, y=fenbiy, pen=QtGui.QPen(QtGui.QColor(255, 236, 139)))

    def fenduan(self, fenduanx, fenduany):
        self.PriceW.pw2.plot(x=fenduanx, y=fenduany, symbol='o', pen=QtGui.QPen(QtGui.QColor(131, 111, 255)))

    def zhongshu(self, zhongshux, zhongshuy):
        self.PriceW.pw2.plot(x=zhongshux, y=zhongshuy, pen=QtGui.QPen(QtGui.QColor(255,165,0)))

    def buypoint(self, buyx, buyy, point):
        if point == 1:
            self.PriceW.pw2.plot(x=buyx, y=buyy, symbolSize=18, symbolBrush=(255,0,0), symbolPen=(255,0,0), symbol='star')
        elif point == 2:
            self.PriceW.pw2.plot(x=buyx, y=buyy, symbolSize=18, symbolBrush=(238,130,238), symbolPen=(238,130,238),symbol='star')
        elif point == 3:
            self.PriceW.pw2.plot(x=buyx, y=buyy, symbolSize=18, symbolBrush=(138,43,226), symbolPen=(138,43,226),symbol='star')

    def sellpoint(self, sellx, selly, point):
        if point == 1:
            self.PriceW.pw2.plot(x=sellx, y=selly,  symbolSize=18, symbolBrush=(119,172,48), symbolPen=(119,172,48), symbol='star')
        elif point == 2:
                self.PriceW.pw2.plot(x=sellx, y=selly, symbolSize=18, symbolBrush=(221,221,34), symbolPen=(221,221,34),symbol='star')
        elif point == 3:
            self.PriceW.pw2.plot(x=sellx, y=selly, symbolSize=18, symbolBrush=(179,158,77), symbolPen=(179,158,77),symbol='star')


    # ----------------------------------------------------------------------
    # 判断包含关系，仿照聚框，合并K线数据
    def judgeInclude(self):
        ## 判断包含关系
        k_data = self.data
        # 保存分型后dataFrame的值
        after_fenxing = pd.DataFrame()
        temp_data = k_data[:1]
        zoushi = [3]  # 3-持平 4-向下 5-向上
        for i in xrange(len(k_data)):
            case1 = temp_data.high[-1] >= k_data.high[i] and temp_data.low[-1] <= k_data.low[i]  # 第1根包含第2根
            case2 = temp_data.high[-1] <= k_data.high[i] and temp_data.low[-1] >= k_data.low[i]  # 第2根包含第1根
            case3 = temp_data.high[-1] == k_data.high[i] and temp_data.low[-1] == k_data.low[i]  # 第1根等于第2根
            case4 = temp_data.high[-1] > k_data.high[i] and temp_data.low[-1] > k_data.low[i]  # 向下趋势
            case5 = temp_data.high[-1] < k_data.high[i] and temp_data.low[-1] < k_data.low[i]  # 向上趋势
            if case3:
                zoushi.append(3)
                continue
            elif case1:
                print temp_data
                if zoushi[-1] == 4:
                    temp_data.ix[0, 4] = k_data.high[i]  #向下走取高点的低点
                else:
                    temp_data.ix[0, 3] = k_data.low[i]   #向上走取低点的高点

            elif case2:
                temp_temp = temp_data[-1:]
                temp_data = k_data[i:i + 1]
                if zoushi[-1] == 4:
                    temp_data.ix[0, 4] = temp_temp.high[0]
                else:
                    temp_data.ix[0, 3] = temp_temp.low[0]

            elif case4:
                zoushi.append(4)
                after_fenxing = pd.concat([after_fenxing, temp_data], axis=0)
                temp_data = k_data[i:i + 1]


            elif case5:
                zoushi.append(5)
                after_fenxing = pd.concat([after_fenxing, temp_data], axis=0)
                temp_data = k_data[i:i + 1]

        return after_fenxing

    # ----------------------------------------------------------------------
    #画出合并后的K线图，分笔
    def plotAfterFenXing(self, after_fenxing):
        #判断包含关系，合并K线
        for i in xrange(len(after_fenxing)):
            #处理k线的最大最小值、开盘收盘价，合并后k线不显示影线。
            after_fenxing.iloc[i, 0] = i
            if after_fenxing.open[i] > after_fenxing.close[i]:
                after_fenxing.iloc[i, 1] = after_fenxing.high[i]
                after_fenxing.iloc[i, 2] = after_fenxing.low[i]
            else:
                after_fenxing.iloc[i, 1] = after_fenxing.low[i]
                after_fenxing.iloc[i, 2] = after_fenxing.high[i]
            self.PriceW.onBarAfterFenXing(i, after_fenxing.index[i], after_fenxing.open[i], after_fenxing.close[i], after_fenxing.low[i], after_fenxing.high[i])
        self.PriceW.plotKlineAfterFenXing()
        print "plotKLine after fenxing"

    # ----------------------------------------------------------------------
    # 找出顶和底
    def findTopAndLow(self, after_fenxing):
        temp_num = 0  # 上一个顶或底的位置
        temp_high = 0  # 上一个顶的high值
        temp_low = 0  # 上一个底的low值
        temp_type = 0  # 上一个记录位置的类型
        i = 1
        fenxing_type = []  # 记录分型点的类型，1为顶分型，-1为底分型
        fenxing_data = pd.DataFrame() # 分型点的DataFrame值
        while (i < len(after_fenxing) - 1):
            case1 = after_fenxing.high[i - 1] < after_fenxing.high[i] and after_fenxing.high[i] > after_fenxing.high[i + 1]  # 顶分型
            case2 = after_fenxing.low[i - 1] > after_fenxing.low[i] and after_fenxing.low[i] < after_fenxing.low[i + 1]  # 底分型
            if case1:
                if temp_type == 1:  # 如果上一个分型为顶分型，则进行比较，选取高点更高的分型
                    if after_fenxing.high[i] <= temp_high:
                        i += 1
                    else:
                        temp_high = after_fenxing.high[i]
                        temp_num = i
                        temp_type = 1
                        i += 1
                elif temp_type == 2:  # 如果上一个分型为底分型，则记录上一个分型，用当前分型与后面的分型比较，选取同向更极端的分型
                    if temp_low >= after_fenxing.high[i]:  # 如果上一个底分型的底比当前顶分型的顶高，则跳过当前顶分型。
                        i += 1
                    elif i < temp_num + 4:  # 顶和底至少5k线
                        i += 1
                    else:
                        fenxing_type.append(-1)
                        fenxing_data = pd.concat([fenxing_data, after_fenxing[temp_num:temp_num + 1]], axis=0)
                        temp_high = after_fenxing.high[i]
                        temp_num = i
                        temp_type = 1
                        i += 1
                else:
                    temp_high = after_fenxing.high[i]
                    temp_num = i
                    temp_type = 1
                    i += 1

            elif case2:
                if temp_type == 2:  # 如果上一个分型为底分型，则进行比较，选取低点更低的分型
                    if after_fenxing.low[i] >= temp_low:
                        i += 1
                    else:
                        temp_low = after_fenxing.low[i]
                        temp_num = i
                        temp_type = 2
                        i += 1
                elif temp_type == 1:  # 如果上一个分型为顶分型，则记录上一个分型，用当前分型与后面的分型比较，选取同向更极端的分型
                    if temp_high <= after_fenxing.low[i]:  # 如果上一个顶分型的底比当前底分型的底低，则跳过当前底分型。
                        i += 1
                    elif i < temp_num + 4:  # 顶和底至少5k线
                        i += 1
                    else:
                        fenxing_type.append(1)
                        fenxing_data = pd.concat([fenxing_data, after_fenxing[temp_num:temp_num + 1]], axis=0)
                        temp_low = after_fenxing.low[i]
                        temp_num = i
                        temp_type = 2
                        i += 1
                else:
                    temp_low = after_fenxing.low[i]
                    temp_num = i
                    temp_type = 2
                    i += 1
            else:
                i += 1

        # if fenxing_type:
        #     if fenxing_type[-1] == 1 and temp_type == 2:
        #         fenxing_type.append(-1)
        #         fenxing_data = pd.concat([fenxing_data, after_fenxing[temp_num:temp_num + 1]], axis=0)
        #
        #     if fenxing_type[-1] == -1 and temp_type == 1:
        #         fenxing_type.append(1)
        #         fenxing_data = pd.concat([fenxing_data, after_fenxing[temp_num:temp_num + 1]], axis=0)

        return fenxing_data, fenxing_type

    # ----------------------------------------------------------------------
    # 连接MongoDB数据库
    def __connectMongo(self):
        try:
            self.__mongoConnection = pymongo.MongoClient("localhost", 27017)
            self.__mongoConnected = True
        except ConnectionFailure:
            pass
    # ----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.signal.connect(self.updateChanlunLog)
        self.eventEngine.register(EVENT_CHANLUN_LOG, self.signal.emit)

########################################################################
class PriceWidget(QtGui.QWidget):
    """用于显示价格走势图"""
    signal = QtCore.pyqtSignal(type(Event()))
    symbol = ''

    class CandlestickItem(pg.GraphicsObject):
        def __init__(self, data):
            pg.GraphicsObject.__init__(self)
            self.data = data  ## data must have fields: time, open, close, min, max
            self.generatePicture()

        def generatePicture(self):
            ## pre-computing a QPicture object allows paint() to run much more quickly,
            ## rather than re-drawing the shapes every time.
            self.picture = QtGui.QPicture()
            p = QtGui.QPainter(self.picture)
            p.setPen(pg.mkPen(color='w', width=0.4))  # 0.4 means w*2
            # w = (self.data[1][0] - self.data[0][0]) / 3.
            w = 0.2
            for (n, t, open, close, min, max) in self.data:
                p.drawLine(QtCore.QPointF(n, min), QtCore.QPointF(n, max))
                if open > close:
                    p.setBrush(pg.mkBrush('g'))
                else:
                    p.setBrush(pg.mkBrush('r'))
                p.drawRect(QtCore.QRectF(n-w, open, w*2, close-open))
                pg.setConfigOption('leftButtonPan', False)
            p.end()

        def paint(self, p, *args):
            p.drawPicture(0, 0, self.picture)

        def boundingRect(self):
            ## boundingRect _must_ indicate the entire area that will be drawn on
            ## or else we will get artifacts and possibly crashing.
            ## (in this case, QPicture does all the work of computing the bouning rect for us)
            return QtCore.QRectF(self.picture.boundingRect())

    #----------------------------------------------------------------------
    def __init__(self, eventEngine, chanlunEngine, data, parent=None):
        """Constructor"""
        super(PriceWidget, self).__init__(parent)

        # K线图EMA均线的参数、变量
        self.EMAFastAlpha = 0.0167  # 快速EMA的参数,60
        self.EMASlowAlpha = 0.0083  # 慢速EMA的参数,120
        self.fastEMA = 0  # 快速EMA的数值
        self.slowEMA = 0  # 慢速EMA的数值
        self.listfastEMA = []
        self.listslowEMA = []

        # 保存K线数据的列表对象
        self.listBar = []
        self.listClose = []
        self.listHigh = []
        self.listLow = []
        self.listOpen = []

        # 是否完成了历史数据的读取
        self.initCompleted = False

        self.__eventEngine = eventEngine
        self.__chanlunEngine = chanlunEngine
        self.data = data  #画图所需数据
        # MongoDB数据库相关
        self.__mongoConnected = False
        self.__mongoConnection = None

        # 调用函数
        self.__connectMongo()
        self.initUi()
        # self.registerEvent()

    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'Price')

        self.vbl_1 = QtGui.QHBoxLayout()

        self.initplotKline()  # plotKline初始化

        self.setLayout(self.vbl_1)

    #----------------------------------------------------------------------
    def initplotKline(self):
        """Kline"""
        s = self.data.index  #横坐标值
        print "numbers of KLine: ", len(s)
        xdict = dict(enumerate(s))
        self.__axisTime = MyStringAxis(xdict, orientation='bottom')
        self.pw2 = pg.PlotWidget(axisItems={'bottom': self.__axisTime})  # K线图
        pw2x = self.pw2.getAxis('bottom')
        pw2x.setGrid(150)  # 设置默认x轴网格
        pw2y = self.pw2.getAxis('left')
        pw2y.setGrid(150)  # 设置默认y轴网格
        self.vbl_1.addWidget(self.pw2)
        self.pw2.setMinimumWidth(1500)
        self.pw2.setMaximumWidth(1800)
        self.pw2.setDownsampling(mode='peak')
        self.pw2.setClipToView(True)

        self.curve5 = self.pw2.plot()
        self.curve6 = self.pw2.plot()

        self.candle = self.CandlestickItem(self.listBar)
        self.pw2.addItem(self.candle)
        ## Draw an arrowhead next to the text box
        # self.arrow = pg.ArrowItem()
        # self.pw2.addItem(self.arrow)


    # 从数据库读取一分钟数据画分钟线
    def plotMin(self, symbol):
        self.initCompleted = True
        cx = self.__mongoMinDB[symbol].find()
        print cx.count()
        if cx:
            for data in cx:
                self.barOpen = data['open']
                self.barClose = data['close']
                self.barLow = data['low']
                self.barHigh = data['high']
                self.barOpenInterest = data['openInterest']
                # print self.num, self.barOpen, self.barClose, self.barLow, self.barHigh, self.barOpenInterest
                self.onBar(self.num, self.barOpen, self.barClose, self.barLow, self.barHigh, self.barOpenInterest)
                self.num += 1


    # 画历史数据K线图
    def plotHistorticData(self):
        self.initCompleted = True
        for i in xrange(len(self.data)):
            self.onBar(i, self.data.index[i], self.data.open[i], self.data.close[i], self.data.low[i], self.data.high[i])
        self.plotKline()
        print "plotKLine success"

    #----------------------------------------------------------------------
    def initHistoricalData(self):
        """初始历史数据"""
        if self.symbol!='':
            print "download histrical data:",self.symbol
            self.initCompleted = True  # 读取历史数据完成
            td = timedelta(days=1)     # 读取3天的历史TICK数据

            # if startDate:
            #     cx = self.loadTick(self.symbol, startDate-td)
            # else:
            #     today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
            #     cx = self.loadTick(self.symbol, today-td)

            print cx.count()

            if cx:
                for data in cx:
                    tick = Tick(data['symbol'])

                    tick.openPrice = data['lastPrice']
                    tick.highPrice = data['upperLimit']
                    tick.lowPrice = data['lowerLimit']
                    tick.lastPrice = data['lastPrice']

                    tick.volume = data['volume']
                    tick.openInterest = data['openInterest']

                    tick.upperLimit = data['upperLimit']
                    tick.lowerLimit = data['lowerLimit']

                    tick.time = data['time']
                    # tick.ms = data['UpdateMillisec']

                    tick.bidPrice1 = data['bidPrice1']
                    tick.bidPrice2 = data['bidPrice2']
                    tick.bidPrice3 = data['bidPrice3']
                    tick.bidPrice4 = data['bidPrice4']
                    tick.bidPrice5 = data['bidPrice5']

                    tick.askPrice1 = data['askPrice1']
                    tick.askPrice2 = data['askPrice2']
                    tick.askPrice3 = data['askPrice3']
                    tick.askPrice4 = data['askPrice4']
                    tick.askPrice5 = data['askPrice5']

                    tick.bidVolume1 = data['bidVolume1']
                    tick.bidVolume2 = data['bidVolume2']
                    tick.bidVolume3 = data['bidVolume3']
                    tick.bidVolume4 = data['bidVolume4']
                    tick.bidVolume5 = data['bidVolume5']

                    tick.askVolume1 = data['askVolume1']
                    tick.askVolume2 = data['askVolume2']
                    tick.askVolume3 = data['askVolume3']
                    tick.askVolume4 = data['askVolume4']
                    tick.askVolume5 = data['askVolume5']

                    self.onTick(tick)

            print('load historic data completed')

    #----------------------------------------------------------------------
    def plotKline(self):
        """K线图"""
        if self.initCompleted:
            # 均线
            self.curve5.setData(self.listfastEMA, pen=(255, 0, 0), name="Red curve")
            self.curve6.setData(self.listslowEMA, pen=(0, 255, 0), name="Green curve")

            # 画K线
            self.pw2.removeItem(self.candle)
            self.candle = self.CandlestickItem(self.listBar)
            self.pw2.addItem(self.candle)

    #----------------------------------------------------------------------
    def plotText(self):
        lenClose = len(self.listClose)

        if lenClose >= 5:                                       # Fractal Signal
            if self.listClose[-1] > self.listClose[-2] and self.listClose[-3] > self.listClose[-2] and self.listClose[-4] > self.listClose[-2] and self.listClose[-5] > self.listClose[-2] and self.listfastEMA[-1] > self.listslowEMA[-1]:
                ## Draw an arrowhead next to the text box
                # self.pw2.removeItem(self.arrow)
                self.arrow = pg.ArrowItem(pos=(lenClose-1, self.listLow[-1]), angle=90, brush=(255, 0, 0))#红色
                self.pw2.addItem(self.arrow)
            elif self.listClose[-1] < self.listClose[-2] and self.listClose[-3] < self.listClose[-2] and self.listClose[-4] < self.listClose[-2] and self.listClose[-5] < self.listClose[-2] and self.listfastEMA[-1] < self.listslowEMA[-1]:
                ## Draw an arrowhead next to the text box
                # self.pw2.removeItem(self.arrow)
                self.arrow = pg.ArrowItem(pos=(lenClose-1, self.listHigh[-1]), angle=-90, brush=(0, 255, 0))#绿色
                self.pw2.addItem(self.arrow)

    #----------------------------------------------------------------------
    def onBar(self, n, t, o, c, l, h):
        self.listBar.append((n, t, o, c, l, h))
        self.listOpen.append(o)
        self.listClose.append(c)
        self.listHigh.append(h)
        self.listLow.append(l)

        #计算K线图EMA均线
        if self.fastEMA:
            self.fastEMA = c*self.EMAFastAlpha + self.fastEMA*(1-self.EMAFastAlpha)
            self.slowEMA = c*self.EMASlowAlpha + self.slowEMA*(1-self.EMASlowAlpha)
        else:
            self.fastEMA = c
            self.slowEMA = c
        self.listfastEMA.append(self.fastEMA)
        self.listslowEMA.append(self.slowEMA)

        self.plotText()    #显示开仓位置

    # ----------------------------------------------------------------------
    #画合并后的K线Bar
    def onBarAfterFenXing(self, n, t, o, c, l, h):
        self.listBar.append((n, t, o, c, l, h))

    def plotKlineAfterFenXing(self):
        # 画K线
        self.pw2.removeItem(self.candle)
        self.candle = self.CandlestickItem(self.listBar)
        self.pw2.addItem(self.candle)


    #----------------------------------------------------------------------
    def __connectMongo(self):
        """连接MongoDB数据库"""
        try:
            self.__mongoConnection = pymongo.MongoClient("localhost", 27017)
            self.__mongoConnected = True
            self.__mongoMinDB = self.__mongoConnection['VnTrader_1Min_Db']
        except ConnectionFailure:
            pass


########################################################################
class TickWidget(QtGui.QWidget):
    """用于显示价格走势图"""
    signal = QtCore.pyqtSignal(type(Event()))

    # tick图的相关参数、变量
    listlastPrice = np.empty(1000)

    fastMA = 0
    midMA = 0
    slowMA = 0
    listfastMA = np.empty(1000)
    listmidMA = np.empty(1000)
    listslowMA = np.empty(1000)
    tickFastAlpha = 0.0333    # 快速均线的参数,30
    tickMidAlpha = 0.0167     # 中速均线的参数,60
    tickSlowAlpha = 0.0083    # 慢速均线的参数,120

    ptr = 0
    ticktime = None  # tick数据时间


    class CandlestickItem(pg.GraphicsObject):
        def __init__(self, data):
            pg.GraphicsObject.__init__(self)
            self.data = data  ## data must have fields: time, open, close, min, max
            self.generatePicture()

        def generatePicture(self):
            ## pre-computing a QPicture object allows paint() to run much more quickly,
            ## rather than re-drawing the shapes every time.
            self.picture = QtGui.QPicture()
            p = QtGui.QPainter(self.picture)
            p.setPen(pg.mkPen(color='w', width=0.4))  # 0.4 means w*2
            a = pg.AxisItem('bottom', pen=None, linkView=None, parent=None, maxTickLength=-5, showValues=True)
            a.setFixedWidth(1)
            a.setWidth(1)
            a.setLabel(show=True)
            a.setGrid(grid=True)
            labelStyle = {'color': '#FFF', 'font-size': '14pt'}
            a.setLabel('label text', units='V', **labelStyle)
            # w = (self.data[1][0] - self.data[0][0]) / 3.
            w = 0.2
            for (t, open, close, min, max) in self.data:
                p.drawLine(QtCore.QPointF(t, min), QtCore.QPointF(t, max))
                if open > close:
                    p.setBrush(pg.mkBrush('g'))
                else:
                    p.setBrush(pg.mkBrush('r'))
                p.drawRect(QtCore.QRectF(t-w, open, w*2, close-open))
                pg.setConfigOption('leftButtonPan', False)
            p.end()

        def paint(self, p, *args):
            p.drawPicture(0, 0, self.picture)

        def boundingRect(self):
            ## boundingRect _must_ indicate the entire area that will be drawn on
            ## or else we will get artifacts and possibly crashing.
            ## (in this case, QPicture does all the work of computing the bouning rect for us)
            return QtCore.QRectF(self.picture.boundingRect())

    #----------------------------------------------------------------------
    def __init__(self, eventEngine, chanlunEngine, parent=None):
        """Constructor"""
        super(TickWidget, self).__init__(parent)

        self.__eventEngine = eventEngine
        self.__chanlunEngine = chanlunEngine
        # MongoDB数据库相关
        self.__mongoConnected = False
        self.__mongoConnection = None
        self.__mongoTickDB = None

        # 调用函数
        self.initUi()
        self.registerEvent()

    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'Tick')

        self.vbl_1 = QtGui.QHBoxLayout()
        self.initplotTick()  # plotTick初始化

        self.setLayout(self.vbl_1)

    #----------------------------------------------------------------------
    def initplotTick(self):
        """"""
        self.pw1 = pg.PlotWidget(name='Plot1')
        self.vbl_1.addWidget(self.pw1)
        self.pw1.setMinimumWidth(1500)
        self.pw1.setMaximumWidth(1800)
        self.pw1.setRange(xRange=[-360, 0])
        self.pw1.setLimits(xMax=5)
        self.pw1.setDownsampling(mode='peak')
        self.pw1.setClipToView(True)

        self.curve1 = self.pw1.plot()
        self.curve2 = self.pw1.plot()
        self.curve3 = self.pw1.plot()
        self.curve4 = self.pw1.plot()


    # #----------------------------------------------------------------------
    # def initHistoricalData(self,startDate=None):
    #     """初始历史数据"""
    #     print "download histrical data"
    #     self.initCompleted = True  # 读取历史数据完成
    #     td = timedelta(days=1)     # 读取3天的历史TICK数据
    #
    #     if startDate:
    #         cx = self.loadTick(self.symbol, startDate-td)
    #     else:
    #         today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    #         cx = self.loadTick(self.symbol, today-td)
    #
    #     print cx.count()
    #
    #     if cx:
    #         for data in cx:
    #             tick = Tick(data['symbol'])
    #
    #             tick.openPrice = data['lastPrice']
    #             tick.highPrice = data['upperLimit']
    #             tick.lowPrice = data['lowerLimit']
    #             tick.lastPrice = data['lastPrice']
    #
    #             tick.volume = data['volume']
    #             tick.openInterest = data['openInterest']
    #
    #             tick.upperLimit = data['upperLimit']
    #             tick.lowerLimit = data['lowerLimit']
    #
    #             tick.time = data['time']
    #             # tick.ms = data['UpdateMillisec']
    #
    #             tick.bidPrice1 = data['bidPrice1']
    #             tick.bidPrice2 = data['bidPrice2']
    #             tick.bidPrice3 = data['bidPrice3']
    #             tick.bidPrice4 = data['bidPrice4']
    #             tick.bidPrice5 = data['bidPrice5']
    #
    #             tick.askPrice1 = data['askPrice1']
    #             tick.askPrice2 = data['askPrice2']
    #             tick.askPrice3 = data['askPrice3']
    #             tick.askPrice4 = data['askPrice4']
    #             tick.askPrice5 = data['askPrice5']
    #
    #             tick.bidVolume1 = data['bidVolume1']
    #             tick.bidVolume2 = data['bidVolume2']
    #             tick.bidVolume3 = data['bidVolume3']
    #             tick.bidVolume4 = data['bidVolume4']
    #             tick.bidVolume5 = data['bidVolume5']
    #
    #             tick.askVolume1 = data['askVolume1']
    #             tick.askVolume2 = data['askVolume2']
    #             tick.askVolume3 = data['askVolume3']
    #             tick.askVolume4 = data['askVolume4']
    #             tick.askVolume5 = data['askVolume5']
    #
    #             self.onTick(tick)
    #
    #     print('load historic data completed')

    #----------------------------------------------------------------------
    def plotTick(self):
        """画tick图"""
        self.curve1.setData(self.listlastPrice[:self.ptr])
        self.curve2.setData(self.listfastMA[:self.ptr], pen=(255, 0, 0), name="Red curve")
        self.curve3.setData(self.listmidMA[:self.ptr], pen=(0, 255, 0), name="Green curve")
        self.curve4.setData(self.listslowMA[:self.ptr], pen=(0, 0, 255), name="Blue curve")
        self.curve1.setPos(-self.ptr, 0)
        self.curve2.setPos(-self.ptr, 0)
        self.curve3.setPos(-self.ptr, 0)
        self.curve4.setPos(-self.ptr, 0)


    #----------------------------------------------------------------------
    def updateMarketData(self, event):
        """更新行情"""
        data = event.dict_['data']
        print "update", data['InstrumentID']
        symbol = data['InstrumentID']
        tick = Tick(symbol)
        tick.openPrice = data['OpenPrice']
        tick.highPrice = data['HighestPrice']
        tick.lowPrice = data['LowestPrice']
        tick.lastPrice = data['LastPrice']

        tick.volume = data['Volume']
        tick.openInterest = data['OpenInterest']

        tick.upperLimit = data['UpperLimitPrice']
        tick.lowerLimit = data['LowerLimitPrice']

        tick.time = data['UpdateTime']
        tick.ms = data['UpdateMillisec']

        tick.bidPrice1 = data['BidPrice1']
        tick.bidPrice2 = data['BidPrice2']
        tick.bidPrice3 = data['BidPrice3']
        tick.bidPrice4 = data['BidPrice4']
        tick.bidPrice5 = data['BidPrice5']

        tick.askPrice1 = data['AskPrice1']
        tick.askPrice2 = data['AskPrice2']
        tick.askPrice3 = data['AskPrice3']
        tick.askPrice4 = data['AskPrice4']
        tick.askPrice5 = data['AskPrice5']

        tick.bidVolume1 = data['BidVolume1']
        tick.bidVolume2 = data['BidVolume2']
        tick.bidVolume3 = data['BidVolume3']
        tick.bidVolume4 = data['BidVolume4']
        tick.bidVolume5 = data['BidVolume5']

        tick.askVolume1 = data['AskVolume1']
        tick.askVolume2 = data['AskVolume2']
        tick.askVolume3 = data['AskVolume3']
        tick.askVolume4 = data['AskVolume4']
        tick.askVolume5 = data['AskVolume5']

        self.onTick(tick)  # tick数据更新
        self.__recordTick(tick)  #记录Tick数据

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """tick数据更新"""
        from datetime import time

        # 首先生成datetime.time格式的时间（便于比较）,从字符串时间转化为time格式的时间
        hh, mm, ss = tick.time.split(':')
        self.ticktime = time(int(hh), int(mm), int(ss), microsecond=tick.ms)

        # 计算tick图的相关参数
        if self.ptr == 0:
            self.fastMA = tick.lastPrice
            self.midMA = tick.lastPrice
            self.slowMA = tick.lastPrice
        else:
            self.fastMA = (1-self.tickFastAlpha) * self.fastMA + self.tickFastAlpha * tick.lastPrice
            self.midMA = (1-self.tickMidAlpha) * self.midMA + self.tickMidAlpha * tick.lastPrice
            self.slowMA = (1-self.tickSlowAlpha) * self.slowMA + self.tickSlowAlpha * tick.lastPrice
        self.listlastPrice[self.ptr] = int(tick.lastPrice)
        self.listfastMA[self.ptr] = int(self.fastMA)
        self.listmidMA[self.ptr] = int(self.midMA)
        self.listslowMA[self.ptr] = int(self.slowMA)

        self.ptr += 1
        print(self.ptr)
        if self.ptr >= self.listlastPrice.shape[0]:
            tmp = self.listlastPrice
            self.listlastPrice = np.empty(self.listlastPrice.shape[0] * 2)
            self.listlastPrice[:tmp.shape[0]] = tmp

            tmp = self.listfastMA
            self.listfastMA = np.empty(self.listfastMA.shape[0] * 2)
            self.listfastMA[:tmp.shape[0]] = tmp

            tmp = self.listmidMA
            self.listmidMA = np.empty(self.listmidMA.shape[0] * 2)
            self.listmidMA[:tmp.shape[0]] = tmp

            tmp = self.listslowMA
            self.listslowMA = np.empty(self.listslowMA.shape[0] * 2)
            self.listslowMA[:tmp.shape[0]] = tmp

         # 调用画图函数
        self.plotTick()  # tick图

    #----------------------------------------------------------------------
    def __connectMongo(self):
        """连接MongoDB数据库"""
        try:
            self.__mongoConnection = pymongo.MongoClient("localhost", 27017)
            self.__mongoConnected = True
            self.__mongoTickDB = self.__mongoConnection['VnTrader_Tick_Db']
        except ConnectionFailure:
            pass

    #----------------------------------------------------------------------
    def __recordTick(self, data):
        """将Tick数据插入到MongoDB中"""
        if self.__mongoConnected:
            symbol = data['InstrumentID']
            data['date'] = datetime.now().strftime('%Y%m%d')
            self.__mongoTickDB[symbol].insert(data)

    # #----------------------------------------------------------------------
    # def loadTick(self, symbol, startDate, endDate=None):
    #     """从MongoDB中读取Tick数据"""
    #     cx = self.__mongoTickDB[symbol].find()
    #     print cx.count()
    #     return cx
    #     # if self.__mongoConnected:
    #     #     collection = self.__mongoTickDB[symbol]
    #     #
    #     #     # 如果输入了读取TICK的最后日期
    #     #     if endDate:
    #     #         cx = collection.find({'date': {'$gte': startDate, '$lte': endDate}})
    #     #     else:
    #     #         cx = collection.find({'date': {'$gte': startDate}})
    #     #     return cx
    #     # else:
    #     #     return None

    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        print "connect"
        self.signal.connect(self.updateMarketData)
        self.__eventEngine.register(EVENT_MARKETDATA, self.signal.emit)

class Tick:
    """Tick数据对象"""

    #----------------------------------------------------------------------
    def __init__(self, symbol):
        """Constructor"""
        self.symbol = symbol        # 合约代码

        self.openPrice = 0          # OHLC
        self.highPrice = 0
        self.lowPrice = 0
        self.lastPrice = 0

        self.volume = 0             # 成交量
        self.openInterest = 0       # 持仓量

        self.upperLimit = 0         # 涨停价
        self.lowerLimit = 0         # 跌停价

        self.time = ''              # 更新时间和毫秒
        self.ms = 0

        self.bidPrice1 = 0          # 深度行情
        self.bidPrice2 = 0
        self.bidPrice3 = 0
        self.bidPrice4 = 0
        self.bidPrice5 = 0

        self.askPrice1 = 0
        self.askPrice2 = 0
        self.askPrice3 = 0
        self.askPrice4 = 0
        self.askPrice5 = 0

        self.bidVolume1 = 0
        self.bidVolume2 = 0
        self.bidVolume3 = 0
        self.bidVolume4 = 0
        self.bidVolume5 = 0

        self.askVolume1 = 0
        self.askVolume2 = 0
        self.askVolume3 = 0
        self.askVolume4 = 0
        self.askVolume5 = 0