# encoding: UTF-8

'''
缠论模块相关的GUI控制组件
'''

from uiBasicWidget import QtGui, QtCore, BasicCell
from eventEngine import *


########################################################################
class ChanlunValueMonitor(QtGui.QTableWidget):
    """参数监控"""

    # ----------------------------------------------------------------------
    def __init__(self, parent=None):
        """Constructor"""
        super(ChanlunValueMonitor, self).__init__(parent)

        self.keyCellDict = {}
        self.data = None
        self.inited = False

        self.initUi()

    # ----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setRowCount(1)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.NoEditTriggers)

        self.setMaximumHeight(self.sizeHint().height())

    # ----------------------------------------------------------------------
    def updateData(self, data):
        """更新数据"""
        if not self.inited:
            self.setColumnCount(len(data))
            self.setHorizontalHeaderLabels(data.keys())

            col = 0
            for k, v in data.items():
                cell = QtGui.QTableWidgetItem(unicode(v))
                self.keyCellDict[k] = cell
                self.setItem(0, col, cell)
                col += 1

            self.inited = True
        else:
            for k, v in data.items():
                cell = self.keyCellDict[k]
                cell.setText(unicode(v))


########################################################################
class ChanlunStrategyManager(QtGui.QGroupBox):
    """策略管理组件"""
    signal = QtCore.pyqtSignal(type(Event()))

    # ----------------------------------------------------------------------
    def __init__(self, chanlunEngine, eventEngine, name, parent=None):
        """Constructor"""
        super(ChanlunStrategyManager, self).__init__(parent)

        self.chanlunEngine = chanlunEngine
        self.eventEngine = eventEngine
        self.name = name

        self.initUi()
        self.updateMonitor()
        self.registerEvent()

    # ----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        # self.setTitle(self.name)
        #
        # self.paramMonitor = ChanlunValueMonitor(self)
        # self.varMonitor = ChanlunValueMonitor(self)
        #
        # maxHeight = 60
        # self.paramMonitor.setMaximumHeight(maxHeight)
        # self.varMonitor.setMaximumHeight(maxHeight)
        #
        # buttonInit = QtGui.QPushButton(u'初始化')
        # buttonStart = QtGui.QPushButton(u'启动')
        # buttonStop = QtGui.QPushButton(u'停止')
        # buttonInit.clicked.connect(self.init)
        # buttonStart.clicked.connect(self.start)
        # buttonStop.clicked.connect(self.stop)
        #
        # hbox1 = QtGui.QHBoxLayout()
        # hbox1.addWidget(buttonInit)
        # hbox1.addWidget(buttonStart)
        # hbox1.addWidget(buttonStop)
        # hbox1.addStretch()
        #
        # hbox2 = QtGui.QHBoxLayout()
        # hbox2.addWidget(self.paramMonitor)
        #
        # hbox3 = QtGui.QHBoxLayout()
        # hbox3.addWidget(self.varMonitor)
        #
        # vbox = QtGui.QVBoxLayout()
        # vbox.addLayout(hbox1)
        # vbox.addLayout(hbox2)
        # vbox.addLayout(hbox3)
        #
        # self.setLayout(vbox)


        self.setLayout(hbox)
        self.show()
    # ----------------------------------------------------------------------
    def updateMonitor(self, event=None):
        """显示策略最新状态"""
        paramDict = self.chanlunEngine.getStrategyParam(self.name)
        if paramDict:
            self.paramMonitor.updateData(paramDict)

        varDict = self.chanlunEngine.getStrategyVar(self.name)
        if varDict:
            self.varMonitor.updateData(varDict)

            # ----------------------------------------------------------------------

    def registerEvent(self):
        """注册事件监听"""
        self.signal.connect(self.updateMonitor)
        self.eventEngine.register(EVENT_CHANLUN_STRATEGY + self.name, self.signal.emit)

    # ----------------------------------------------------------------------
    def init(self):
        """初始化策略"""
        self.chanlunEngine.initStrategy(self.name)

    # ----------------------------------------------------------------------
    def start(self):
        """启动策略"""
        self.chanlunEngine.startStrategy(self.name)

    # ----------------------------------------------------------------------
    def stop(self):
        """停止策略"""
        self.chanlunEngine.stopStrategy(self.name)


########################################################################
class ChanlunEngineManager(QtGui.QWidget):
    """chanlun引擎管理组件"""
    signal = QtCore.pyqtSignal(type(Event()))

    # ----------------------------------------------------------------------
    def __init__(self, chanlunEngine, eventEngine, parent=None):
        """Constructor"""
        super(ChanlunEngineManager, self).__init__(parent)

        self.chanlunEngine = chanlunEngine
        self.eventEngine = eventEngine

        self.strategyLoaded = False

        self.initUi()
        self.registerEvent()

        # 记录日志
        self.chanlunEngine.writeChanlunLog(u'缠论引擎启动成功')

        # ----------------------------------------------------------------------

    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'缠论策略')

        # 按钮
        # loadButton = QtGui.QPushButton(u'加载策略')
        # initAllButton = QtGui.QPushButton(u'全部初始化')
        # startAllButton = QtGui.QPushButton(u'全部启动')
        # stopAllButton = QtGui.QPushButton(u'全部停止')

        # 按钮
        loadButton = QtGui.QPushButton(u'分笔')
        initAllButton = QtGui.QPushButton(u'分段')
        startAllButton = QtGui.QPushButton(u'买卖点')
        stopAllButton = QtGui.QPushButton(u'还原')

        loadButton.clicked.connect(self.load)
        initAllButton.clicked.connect(self.initAll)
        startAllButton.clicked.connect(self.startAll)
        stopAllButton.clicked.connect(self.stopAll)

        # 滚动区域，放置所有的ChanlunStrategyManager
        # self.scrollArea = QtGui.QScrollArea()
        # self.scrollArea.setWidgetResizable(True)

        # Chanlun组件的日志监控
        self.chanlunLogMonitor = QtGui.QTextEdit()
        self.chanlunLogMonitor.setReadOnly(True)
        self.chanlunLogMonitor.setMaximumHeight(200)

        # 设置布局
        hbox2 = QtGui.QHBoxLayout()
        hbox2.addWidget(loadButton)
        hbox2.addWidget(initAllButton)
        hbox2.addWidget(startAllButton)
        hbox2.addWidget(stopAllButton)
        hbox2.addStretch()


        okButton = QtGui.QPushButton("OK")
        oneMButton = QtGui.QPushButton(u"1分")
        fiveMButton = QtGui.QPushButton(u'5分')
        fifteenMButton = QtGui.QPushButton(u'15分')
        thirtyMButton = QtGui.QPushButton(u'30分')
        dayButton = QtGui.QPushButton(u'日')
        weekButton = QtGui.QPushButton(u'周')
        monthButton = QtGui.QPushButton(u'月')

        vbox1 = QtGui.QVBoxLayout()

        vbox2 = QtGui.QVBoxLayout()
        # vbox1.addWidget(okButton)
        vbox2.addWidget(oneMButton)
        vbox2.addWidget(fiveMButton)
        vbox2.addWidget(fifteenMButton)
        vbox2.addWidget(thirtyMButton)
        vbox2.addWidget(dayButton)
        vbox2.addWidget(weekButton)
        vbox2.addWidget(monthButton)
        vbox2.addStretch()

        hbox3 = QtGui.QHBoxLayout()
        hbox3.addStretch()
        hbox3.addLayout(vbox1)
        hbox3.addLayout(vbox2)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(hbox2)
        vbox.addLayout(hbox3)
        #vbox.addWidget(self.scrollArea)
        vbox.addWidget(self.chanlunLogMonitor)
        self.setLayout(vbox)

    # ----------------------------------------------------------------------
    def initStrategyManager(self):
        """初始化策略管理组件界面"""
        w = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout()

        for name in self.chanlunEngine.strategyDict.keys():
            strategyManager = ChanlunStrategyManager(self.chanlunEngine, self.eventEngine, name)
            vbox.addWidget(strategyManager)

        vbox.addStretch()

        w.setLayout(vbox)
        self.scrollArea.setWidget(w)

        # ----------------------------------------------------------------------

    def initAll(self):
        """全部初始化"""
        for name in self.chanlunEngine.strategyDict.keys():
            self.chanlunEngine.initStrategy(name)

            # ----------------------------------------------------------------------

    def startAll(self):
        """全部启动"""
        for name in self.chanlunEngine.strategyDict.keys():
            self.chanlunEngine.startStrategy(name)

    # ----------------------------------------------------------------------
    def stopAll(self):
        """全部停止"""
        for name in self.chanEngine.strategyDict.keys():
            self.chanEngine.stopStrategy(name)

    # ----------------------------------------------------------------------
    def load(self):
        """加载策略"""
        if not self.strategyLoaded:
            self.chanlunEngine.loadSetting()
            self.initStrategyManager()
            self.strategyLoaded = True
            self.chanlunEngine.writeChanlunLog(u'缠论策略加载成功')

    # ----------------------------------------------------------------------
    def updateChanlunLog(self, event):
        """更新缠论相关日志"""
        log = event.dict_['data']
        content = '\t'.join([log.logTime, log.logContent])
        self.chanlunLogMonitor.append(content)

    # ----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.signal.connect(self.updateChanlunLog)
        self.eventEngine.register(EVENT_CHANLUN_LOG, self.signal.emit)










