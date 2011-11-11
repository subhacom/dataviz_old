#!/usr/bin/env python

# Filename: dataviz.py
# Description: 
# Author: Subhasis Ray
# Maintainer: 
# Copyright (C) 2010 Subhasis Ray, all rights reserved.
# Created: Wed Dec 15 10:16:41 2010 (+0530)
# Version: 
# Last-Updated: Fri Nov 11 11:20:58 2011 (+0530)
#           By: subha
#     Update #: 2701
# URL: 
# Keywords: 
# Compatibility: 
# 
# 

# Commentary: 
# 
# This is for visualizing neuronal activity in animation from a hdf5
# data file.
# 
# Decided to use matplotlib/mlab instead of mayavi for the sake of ease of coding.

# Change log:
# 
# 2010-12-15 10:17:49 (+0530) -- initial version
#
# 2010-12-17 11:30:12 (+0530) -- working matplotlib 2D animation with
# randomly generated numbers.
#
# 2010-12-21 11:53:32 (+0530) -- realized that a better way to
# organize data would be to create /data/spike /data/Vm and /data/Ca
# in the MOOSE model and the corresponding tables under those with
# same name as the cell it is recording from. Depending on table name
# suffix is as bad as filename extensions in Windows - one has to be
# consistent with the assumptions about table names between the
# simulation code and the data analysis code.  Hence forking this away
# into code for analyzing newer data.
#
# 2011-02-11 15:26:02 (+0530) -- scrapped matplotlib/mayavi approach
# and going for simple 2D rasters with option for selecting tables and
# scrolling (using Qt).
#
# 2011-03-03 23:46:42 (+0530) -- h5py browsing tree is functional.
#
# 2011-03-06 14:12:59 (+0530) -- This has now been split into
# multiple files in the dataviz directory. Also, all data
# visualization code is being shifted to cortical/dataviz directory as
# they are independent of the simulation.

# 2011-04-06 11:43:25 (+0530) scrapped the old code in this file and
# starting over with the component widgets - h5f tree and spikeplot.

# Code:

import os
import sys
import numpy
from collections import defaultdict
from PyQt4 import QtCore, QtGui, Qt
from PyQt4 import Qwt5 as Qwt
from plotwidget import PlotWidget
from hdftree import H5TreeWidget
from datalist import UniqueListModel, UniqueListView
from plotconfig import PlotConfig
import analyzer
default_settings = {
    'lfpfilter/cutoff': '450.0',
    'lfpfilter/rolloff': '45.0'
}
class DataVizWidget(QtGui.QMainWindow):
    def __init__(self, *args):
        QtGui.QMainWindow.__init__(self, *args)
        QtCore.QCoreApplication.setOrganizationName('NCBS')
        QtCore.QCoreApplication.setOrganizationDomain('ncbs.res.in')
        QtCore.QCoreApplication.setApplicationName('dataviz')        
        self.settings = QtCore.QSettings()         
        for key, value in default_settings.items():
            s = self.settings.value(key)
            if not s.isValid():
                self.settings.setValue(key, value)
        self.mdi_data_map = {}
        self.data_dict = {}
        self.data_model_dict = {} # dict containing association between data file and corresponding model file.
        self.mdiArea = QtGui.QMdiArea(self)
        self.mdiArea.setViewMode(self.mdiArea.TabbedView)
        self.connect(self.mdiArea, QtCore.SIGNAL('subWindowActivated(QMdiSubWindow*)'), self.__subwindowActivatedSlot)
        self.leftDock = QtGui.QDockWidget(self)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.leftDock)
        self.rightDock = QtGui.QDockWidget(self)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.rightDock)
        self.h5tree = H5TreeWidget(self.leftDock)
        self.h5tree.setSelectionMode(self.h5tree.ExtendedSelection)
        self.h5tree.setContextMenuPolicy(Qt.Qt.CustomContextMenu)
        self.leftDock.setWidget(self.h5tree)
        self.dataList = UniqueListView()        
        self.dataList.setModel(UniqueListModel(QtCore.QStringList([])))
        self.dataList.setSelectionMode(self.dataList.ExtendedSelection)
        self.dataList.setContextMenuPolicy(Qt.Qt.CustomContextMenu)        
        self.rightDock.setWidget(self.dataList)
        self.setCentralWidget(self.mdiArea)
        self.setStatusBar(QtGui.QStatusBar())
        self.windowMapper = QtCore.QSignalMapper(self)
        # self.connect(self.windowMapper, QtCore.SIGNAL('mapped(QWidget*)'),
        #              self.__setActiveSubWindow)
        self.connect(self.h5tree, QtCore.SIGNAL('itemDoubleClicked(QTreeWidgetItem *, int )'), self.__displayData)

        self.plotConfig = PlotConfig(self)
        self.plotConfig.setVisible(False)        
        self.__setupActions()
        self.__setupMenuBar()

    def __setupActions(self):
        # Actions for File menu
        self.quitAction = QtGui.QAction('&Quit', self)        
        self.quitAction.setShortcut(QtGui.QKeySequence(self.tr('Ctrl+Q')))
        self.connect(self.quitAction, QtCore.SIGNAL('triggered()'), QtGui.qApp.quit)

        self.openAction = QtGui.QAction('&Open', self)
        self.openAction.setShortcut(QtGui.QKeySequence(self.tr('Ctrl+O')))
        self.connect(self.openAction, QtCore.SIGNAL('triggered()'), self.__openFileDialog)
        self.closeFileAction = QtGui.QAction('Close', self)
        self.connect(self.closeFileAction, QtCore.SIGNAL('triggered()'), self.__closeFile)

        self.saveDataAction = QtGui.QAction('&Save selected data', self)
        self.connect(self.saveDataAction, QtCore.SIGNAL('triggered()'), self.__saveSelectedDataToCsvFile)

        self.savePlotAction = QtGui.QAction('&Save plot', self)
        self.connect(self.savePlotAction, QtCore.SIGNAL('triggered()'), self.__savePlot)

        self.saveScreenshotAction = QtGui.QAction('Save screenshot', self)
        self.connect(self.saveScreenshotAction, QtCore.SIGNAL('triggered()'), self.__saveScreenshot)

        self.editSettingsAction = QtGui.QAction('Preferences', self)
        self.connect(self.editSettingsAction, QtCore.SIGNAL('triggered()'), self.__showPreferencesDialog)

        # Actions for Tools menu

        self.newFIRFilteredPlotAction = QtGui.QAction('Plot FIR filtered LFP in new window', self)
        self.connect(self.newFIRFilteredPlotAction, QtCore.SIGNAL('triggered()'), self.__plotFIRFilteredLFPNewWin)
        self.firFilteredPlotAction = QtGui.QAction('Plot FIR filtered LFP in current window', self)    
        self.connect(self.firFilteredPlotAction, QtCore.SIGNAL('triggered()'), self.__plotFIRFilteredLFPCurrentWin)
        self.newBlackmannFilteredPlotAction = QtGui.QAction('Plot Blackmann filtered LFP in new window', self)
        self.connect(self.newBlackmannFilteredPlotAction, QtCore.SIGNAL('triggered()'), self.__plotBlackmannFilteredLFPNewWin)
        self.blackmannFilteredPlotAction = QtGui.QAction('Plot Blackmann filtered LFP in current window', self)    
        self.connect(self.blackmannFilteredPlotAction, QtCore.SIGNAL('triggered()'), self.__plotBlackmannFilteredLFPCurrentWin)
        self.plotPowerSpectrumAction = QtGui.QAction('Plot power spectrum', self)
        self.connect(self.plotPowerSpectrumAction, QtCore.SIGNAL('triggered()'), self.__plotPowerSpectrum)

        self.plotPresynapticVmAction = QtGui.QAction('Plot presynaptic Vm', self)
        self.connect(self.plotPresynapticVmAction, QtCore.SIGNAL('triggered()'), self.__plotPresynapticVm)

        self.plotPresynapticSpikesAction = QtGui.QAction('Plot presynaptic spikes', self)
        self.connect(self.plotPresynapticSpikesAction, QtCore.SIGNAL('triggered()'), self.__plotPresynapticSpikes)
        
        # Actions for Plot menu
        self.newLinePlotAction = QtGui.QAction('&New line plot', self)
        self.connect(self.newLinePlotAction, QtCore.SIGNAL('triggered()'), self.__makeNewLinePlot)

        self.newLinePlotByRegexAction = QtGui.QAction('&New line plot by regex', self)
        self.connect(self.newLinePlotByRegexAction, QtCore.SIGNAL('triggered()'), self.__makeNewLinePlotByRegex)

        self.plotAction = QtGui.QAction('&Line plot in current subwindow', self)
        self.connect(self.plotAction, QtCore.SIGNAL('triggered()'), self.__makeLinePlot)

        self.newRasterPlotAction = QtGui.QAction('&New raster plot', self)
        self.connect(self.newRasterPlotAction, QtCore.SIGNAL('triggered()'), self.__makeNewRasterPlot)

        self.newRasterPlotByRegexAction = QtGui.QAction('&New raster plot by regex', self)
        self.connect(self.newRasterPlotByRegexAction, QtCore.SIGNAL('triggered()'), self.__makeNewRasterPlotByRegex)

        self.rasterPlotAction = QtGui.QAction('&Raster plot in current subwindow', self)
        self.connect(self.rasterPlotAction, QtCore.SIGNAL('triggered()'), self.__makeRasterPlot)
        self.editPlotTitleAction = QtGui.QAction(self.tr('Edit plot title '), self)
        self.connect(self.editPlotTitleAction, QtCore.SIGNAL('triggered()'), self.__editPlotTitle)

        self.editLegendTextAction = QtGui.QAction(self.tr('Edit legend text'), self)
        self.connect(self.editLegendTextAction, QtCore.SIGNAL('triggered(bool)'), self.__editLegendText)

        self.editXLabelAction = QtGui.QAction(self.tr('Edit X axis label'), self)
        self.connect(self.editXLabelAction, QtCore.SIGNAL('triggered()'), self.__editXAxisLabel)

        self.editYLabelAction = QtGui.QAction(self.tr('Edit Y axis label'), self)
        self.connect(self.editYLabelAction, QtCore.SIGNAL('triggered()'), self.__editYAxisLabel)

        self.fitSelectedCurvesAction = QtGui.QAction(self.tr('Fit selected curves'), self)
        self.connect(self.fitSelectedCurvesAction, QtCore.SIGNAL('triggered()'), self.__fitSelectedPlots)
        
        self.shiftSelectedCurvesAction = QtGui.QAction('Shift selected curves vertically', self)
        self.connect(self.shiftSelectedCurvesAction, QtCore.SIGNAL('triggered()'), self.__vShiftSelectedPlots)

        self.scaleSelectedCurvesAction = QtGui.QAction('Scale selected curves vertically', self)
        self.connect(self.scaleSelectedCurvesAction, QtCore.SIGNAL('triggered()'), self.__vScaleSelectedPlots)

        self.deselectAllCurvesAction = QtGui.QAction('Deselect all curves', self)
        self.connect(self.deselectAllCurvesAction, QtCore.SIGNAL('triggered()'), self.__deselectAllCurves)

        self.configurePlotAction = QtGui.QAction(self.tr('Configure selected plots'), self)
        self.connect(self.configurePlotAction, QtCore.SIGNAL('triggered(bool)'), self.__configurePlots)

        self.togglePlotVisibilityAction = QtGui.QAction(self.tr('Toggle selected plots'), self)
        self.connect(self.togglePlotVisibilityAction, QtCore.SIGNAL('triggered(bool)'), self.__togglePlotVisibility)
        
        self.displayLegendAction = QtGui.QAction('Display legend', self)
        self.displayLegendAction.setCheckable(True)
        self.displayLegendAction.setChecked(True)
        self.displayLegendAction.setEnabled(False)
        self.connect(self.displayLegendAction, QtCore.SIGNAL('triggered(bool)'), self.__displayLegend)

        self.overlayAction = QtGui.QAction('Overlay plots', self)
        self.overlayAction.setCheckable(True)
        self.overlayAction.setChecked(True)
        self.connect(self.overlayAction, QtCore.SIGNAL('triggered(bool)'), self.__overlayPlots)

        # Actions for Edit menu - works on HDFTree and DataList.
        self.removeSelectedAction = QtGui.QAction('Remove selected items', self)
        self.connect(self.removeSelectedAction, QtCore.SIGNAL('triggered()'), self.dataList.removeSelected)

        self.clearPlotListAction = QtGui.QAction('&Clear data list', self)
        self.connect(self.clearPlotListAction, QtCore.SIGNAL('triggered()'), self.dataList.model().clear)

        self.selectForPlotAction = QtGui.QAction(self.tr('Select for plotting'), self.h5tree)
        self.connect(self.selectForPlotAction, QtCore.SIGNAL('triggered()'), self.__selectForPlot)

        self.selectByRegexAction = QtGui.QAction('Select by regular expression', self)
        self.connect(self.selectByRegexAction, QtCore.SIGNAL('triggered()'), self.__popupRegexTool)

        self.displayPropertiesAction = QtGui.QAction('Properties', self)
        self.connect(self.displayPropertiesAction, QtCore.SIGNAL('triggered()'), self.__displayH5NodeProperties)

        self.displayDataAction = QtGui.QAction('Display data', self)
        self.connect(self.displayDataAction, QtCore.SIGNAL('triggered()'), self.__displayCurrentlySelectedItemData)

        # Actions for Window menu
        self.closeActiveSubwindowAction = QtGui.QAction('Close current Window', self)
        self.connect(self.closeActiveSubwindowAction, QtCore.SIGNAL('triggered()'), self.mdiArea.closeActiveSubWindow)
        self.closeAllAction = QtGui.QAction('Close All Windows', self)
        self.connect(self.closeAllAction, QtCore.SIGNAL('triggered()'), self.mdiArea.closeAllSubWindows)
        self.switchMdiViewAction = QtGui.QAction('Subwindow view', self)
        self.connect(self.switchMdiViewAction, QtCore.SIGNAL('triggered()'), self.__switchMdiView)
        self.cascadeAction = QtGui.QAction('&Cascade', self)
        self.connect(self.cascadeAction, QtCore.SIGNAL('triggered()'), self.mdiArea.cascadeSubWindows)
        self.cascadeAction.setVisible(False)
        self.tileAction = QtGui.QAction('&Tile', self)
        self.connect(self.tileAction, QtCore.SIGNAL('triggered()'), self.mdiArea.tileSubWindows)
        self.tileAction.setVisible(False)
        
    def __setupMenuBar(self):
        self.fileMenu = self.menuBar().addMenu('&File')
        self.fileMenu.addAction(self.openAction)
        self.fileMenu.addAction(self.closeFileAction)
        self.fileMenu.addAction(self.saveDataAction)
        self.fileMenu.addAction(self.savePlotAction)
        self.fileMenu.addAction(self.saveScreenshotAction)
        self.fileMenu.addAction(self.quitAction)
        self.windowMenu = self.menuBar().addMenu('&Window')
        self.windowMenu.addAction(self.closeActiveSubwindowAction)
        self.windowMenu.addAction(self.closeAllAction)
        self.windowMenu.addAction(self.switchMdiViewAction)
        self.windowMenu.addAction(self.cascadeAction)
        self.windowMenu.addAction(self.tileAction)
        
        self.connect(self.windowMenu, QtCore.SIGNAL('aboutToShow()'), self.__updateWindowMenu)
        self.editMenu = self.menuBar().addMenu('&Edit')
        self.editMenu.addAction(self.selectForPlotAction)
        self.editMenu.addAction(self.selectByRegexAction)
        self.editMenu.addAction(self.removeSelectedAction)
        self.editMenu.addAction(self.clearPlotListAction)
        self.editMenu.addAction(self.editSettingsAction)

        self.plotMenu = self.menuBar().addMenu('&Plot')
        self.plotMenu.addAction(self.newLinePlotAction)
        self.plotMenu.addAction(self.newLinePlotByRegexAction)
        self.plotMenu.addAction(self.plotAction)

        self.plotMenu.addAction(self.newRasterPlotAction)
        self.plotMenu.addAction(self.newRasterPlotByRegexAction)
        self.plotMenu.addAction(self.rasterPlotAction)

        self.plotMenu.addAction(self.editPlotTitleAction)
        self.plotMenu.addAction(self.editLegendTextAction)
        self.plotMenu.addAction(self.configurePlotAction)
        self.plotMenu.addAction(self.deselectAllCurvesAction)
        self.plotMenu.addAction(self.togglePlotVisibilityAction)
        self.plotMenu.addAction(self.editXLabelAction)
        self.plotMenu.addAction(self.editYLabelAction)
        self.plotMenu.addAction(self.displayLegendAction)
        self.plotMenu.addAction(self.fitSelectedCurvesAction)
        self.plotMenu.addAction(self.shiftSelectedCurvesAction)
        self.plotMenu.addAction(self.scaleSelectedCurvesAction)
        self.plotMenu.addAction(self.overlayAction)
        self.toolsMenu = self.menuBar().addMenu('&Tools')

        self.toolsMenu.addAction(self.newFIRFilteredPlotAction)
        self.toolsMenu.addAction(self.firFilteredPlotAction)
        self.toolsMenu.addAction(self.newBlackmannFilteredPlotAction)
        self.toolsMenu.addAction(self.blackmannFilteredPlotAction)
        self.toolsMenu.addAction(self.plotPowerSpectrumAction)
        self.toolsMenu.addAction(self.plotPresynapticVmAction)
        self.toolsMenu.addAction(self.plotPresynapticSpikesAction)

        # These are custom context menus
        self.h5treeMenu = QtGui.QMenu(self.tr('Data Selection'), self.h5tree)
        self.h5treeMenu.addAction(self.selectForPlotAction)
        self.h5treeMenu.addAction(self.selectByRegexAction)
        self.h5treeMenu.addAction(self.displayPropertiesAction)
        self.h5treeMenu.addAction(self.displayDataAction)
        self.connect(self.h5tree, QtCore.SIGNAL('customContextMenuRequested(const QPoint&)'), self.__popupH5TreeMenu)
        
        self.dataListMenu = QtGui.QMenu(self.tr('Selected Data'), self.dataList)
        self.dataListMenu.addAction(self.removeSelectedAction)
        self.dataListMenu.addAction(self.clearPlotListAction)
        self.connect(self.dataList, QtCore.SIGNAL('customContextMenuRequested(const QPoint&)'), self.__popupDataListMenu)
        
    def __openFileDialog(self):
        last_dir = self.settings.value('lastVisitedDir').toString()
        file_names = QtGui.QFileDialog.getOpenFileNames(self, self.tr('Open hdf5 file'), last_dir)
        name = last_dir
        for name in file_names:
            self.h5tree.addH5Handle(str(name))
            model_file = os.path.basename(str(name)).replace('data', 'network') + '.new'
            model_file = os.path.join(os.path.dirname(str(name)), model_file)
            self.data_model_dict[str(name)] = model_file            
        self.settings.setValue('lastVisitedDir', QtCore.QString(os.path.dirname(str(name))))

    def __closeFile(self):
        self.h5tree.closeCurrentFile()


    def __selectForPlot(self):
        items = self.h5tree.selectedItems()
        self.data_dict = {}
        for item in items:
            if item.childCount() > 0: # not a leaf node                
                continue
            path = item.path()
            self.dataList.model().insertItem(path)
        
    def __makeRasterPlot(self):
        if self.mdiArea.activeSubWindow() is None or self.mdiArea.activeSubWindow().widget() is None:
            plotWidget = PlotWidget()
            mdiChild = self.mdiArea.addSubWindow(plotWidget)
            mdiChild.setWindowTitle('Raster %d' % len(self.mdiArea.subWindowList()))
        else:
            mdiChild = self.mdiArea.activeSubWindow()
            plotWidget = mdiChild.widget()
        self.displayLegendAction.setEnabled(True)
        self.connect(plotWidget, QtCore.SIGNAL('curveSelected'), self.__showStatusMessage)
        namelist = []
        datalist = []
        for item in self.h5tree.selectedItems():
            if item.childCount() == 0: # not a leaf node                
                path = item.path()
                tseries = self.h5tree.getTimeSeries(path)
                datalist.append((tseries, numpy.array(self.h5tree.getData(path))))
                namelist.append(path)
                self.dataList.model().insertItem(path)
        plotWidget.addPlotCurveList(namelist, datalist, curvenames=namelist, mode='raster')
        mdiChild.showMaximized()
                                    
    def __makeLinePlot(self):
        if self.mdiArea.activeSubWindow() is None or self.mdiArea.activeSubWindow().widget() is None:
            plotWidget = PlotWidget()
            mdiChild = self.mdiArea.addSubWindow(plotWidget)
            mdiChild.setWindowTitle('Plot %d' % len(self.mdiArea.subWindowList())) 
        else:
            mdiChild = self.mdiArea.activeSubWindow()
            plotWidget = mdiChild.widget()
        self.displayLegendAction.setEnabled(True)
        self.connect(plotWidget, QtCore.SIGNAL('curveSelected'), self.__showStatusMessage)
        datalist = []
        pathlist = []
        for item in self.h5tree.selectedItems():
            path = item.path()
            pathlist.append(path)
            tseries = self.h5tree.getTimeSeries(path)
            data = numpy.array(self.h5tree.getData(path))
            datalist.append((tseries, data))
        plotWidget.addPlotCurveList(pathlist, datalist, curvenames=pathlist, mode='curve')
        mdiChild.showMaximized()

    def __makeNewLinePlot(self):
        self.dataList.model().clear()
        self.__selectForPlot()
        mdiChild = self.mdiArea.activeSubWindow()
        if (mdiChild is None) or (mdiChild.widget() is not None):
            mdiChild = self.mdiArea.addSubWindow(PlotWidget())
            mdiChild.setWindowTitle('Plot %d' % len(self.mdiArea.subWindowList()))
        else:
            mdiChild.setWidget(PlotWidget())
        mdiChild.showMaximized()
        self.__makeLinePlot()

    def __makeNewRasterPlot(self):
        self.dataList.model().clear()
        self.__selectForPlot()
        mdiChild = self.mdiArea.activeSubWindow()
        if (mdiChild is None) or (mdiChild.widget() is not None):
            mdiChild = self.mdiArea.addSubWindow(PlotWidget())
            mdiChild.setWindowTitle('Raster %d' % len(self.mdiArea.subWindowList()))
        else:
            mdiChild.setWidget(PlotWidget())
        mdiChild.showMaximized()
        self.__makeRasterPlot()

    def __makeNewLinePlotByRegex(self):
        self.dataList.model().clear()
        self.__popupRegexTool()
        plotWidget = PlotWidget()
        mdiChild = self.mdiArea.activeSubWindow()
        if (mdiChild is None) or (mdiChild.widget() is not None):
            mdiChild = self.mdiArea.addSubWindow(plotWidget)
            mdiChild.setWindowTitle('Plot %d' % len(self.mdiArea.subWindowList()))
        else:
            mdiChild.setWidget(plotWidget)
        pathlist = []
        datalist = []
        for item in self.dataList.model().stringList():
            path = str(item)
            pathlist.append(path)
            tseries = self.h5tree.getTimeSeries(path)
            data = numpy.array(self.h5tree.getData(path))
            datalist.append((tseries, data))
        plotWidget.addPlotCurveList(pathlist, datalist, mode='curve')
        mdiChild.showMaximized()

    def __makeNewRasterPlotByRegex(self):
        self.dataList.model().clear()
        self.__popupRegexTool()
        plotWidget = PlotWidget()
        mdiChild = self.mdiArea.activeSubWindow()
        if (mdiChild is None) or mdiChild.widget():
            mdiChild = self.mdiArea.addSubWindow(plotWidget)
            mdiChild.setWindowTitle('Raster %d' % len(self.mdiArea.subWindowList()))
        else:
            mdiChild.setWidget(plotWidget)
        pathlist = []
        datalist = []
        for item in self.dataList.model().stringList():
            path = str(item)
            pathlist.append(path)
            tseries = self.h5tree.getTimeSeries(path)
            data = numpy.array(self.h5tree.getData(path))
            datalist.append((tseries, data))
        plotWidget.addPlotCurveList(pathlist, datalist, mode='raster')
        mdiChild.showMaximized()

    def __editXAxisLabel(self):
        activePlot = self.mdiArea.activeSubWindow().widget()
        xlabel, ok, = QtGui.QInputDialog.getText(self, self.tr('Change X Axis Label'), self.tr('X axis label:'), QtGui.QLineEdit.Normal, activePlot.axisTitle(activePlot.xBottom).text())
        if ok:
            activePlot.setAxisTitle(2, xlabel)
        
    def __editYAxisLabel(self):
        activePlot = self.mdiArea.activeSubWindow().widget()
        ylabel, ok, = QtGui.QInputDialog.getText(self, self.tr('Change Y Axis Label'), self.tr('Y axis label:'), QtGui.QLineEdit.Normal, activePlot.axisTitle(0).text())
        if ok:
            activePlot.setAxisTitle(0, ylabel)

    def __popupRegexTool(self):
        self.regexDialog = QtGui.QDialog(self)
        self.regexDialog.setWindowTitle('Select data by regex')
        regexlabel = QtGui.QLabel(self.regexDialog)
        regexlabel.setText('Regular expression:')
        self.regexLineEdit = QtGui.QLineEdit(self.regexDialog)        
        okButton = QtGui.QPushButton('OK', self.regexDialog)
        self.connect(okButton, QtCore.SIGNAL('clicked()'), self.regexDialog.accept)
        cancelButton = QtGui.QPushButton('Cancel', self.regexDialog)
        self.connect(cancelButton, QtCore.SIGNAL('clicked()'), self.regexDialog.reject)
        layout = QtGui.QGridLayout()
        layout.addWidget(regexlabel, 0, 0, 1, 2)
        layout.addWidget(self.regexLineEdit, 0, 2, 1, 2)
        layout.addWidget(okButton, 1, 0, 1, 1)
        layout.addWidget(cancelButton, 1, 2, 1, 1)
        self.regexDialog.setLayout(layout)
        if self.regexDialog.exec_() == QtGui.QDialog.Accepted:
            self.__selectDataByRegex(str(self.regexLineEdit.text()))
        
    def __selectDataByRegex(self, pattern):
        self.data_dict = self.h5tree.getDataByRe(pattern)
        self.dataList.model().clear()
        for key in self.data_dict.keys():
            self.dataList.model().insertItem(key)

    def __displayH5NodeProperties(self):
        attributes = self.h5tree.currentItem().getAttributes()
        displayWidget = QtGui.QTableWidget(self)
        displayWidget.setRowCount(len(attributes))
        displayWidget.setColumnCount(2)
        displayWidget.setHorizontalHeaderLabels(QtCore.QStringList(['Attribute', 'Value']))
        row = 0
        for key, value in attributes.items():
            newItem = QtGui.QTableWidgetItem(self.tr(str(key)))
            displayWidget.setItem(row, 0, newItem)
            newItem = QtGui.QTableWidgetItem(self.tr(str(value)))
            displayWidget.setItem(row, 1, newItem)
            row += 1
        displayWidget.setSortingEnabled(True)
        mdiChild = self.mdiArea.addSubWindow(displayWidget)
        mdiChild.setWindowTitle(str(self.h5tree.currentItem().h5node.name))
        mdiChild.showMaximized()

    def __displayData(self, node, column):
        data = node.getHDF5Data()
        if data is None:
            return
        tableWidget = QtGui.QTableWidget()
        tableWidget.setRowCount(len(data))
        if data.dtype.type == numpy.void:            
            tableWidget.setColumnCount(len(data.dtype.names))
            tableWidget.setHorizontalHeaderLabels(QtCore.QStringList(data.dtype.names))
            for row in range(len(data)):
                for column in range(len(data.dtype.names)):
                    item = QtGui.QTableWidgetItem(self.tr(str(data[row][column])))
                    tableWidget.setItem(row, column, item)
        else:
            tableWidget.setColumnCount(1)
            tableWidget.setHorizontalHeaderLabels(QtCore.QStringList(['value',]))
            for row in range(len(data)):
                item = QtGui.QTableWidgetItem(self.tr(str(data[row])))
                tableWidget.setItem(row, 0, item)
        tableWidget.setSortingEnabled(True)
        mdiChild = self.mdiArea.addSubWindow(tableWidget)
        mdiChild.showMaximized()
        mdiChild.setWindowTitle(str(node.h5node.name))
            
    def __displayCurrentlySelectedItemData(self):
        node = self.h5tree.currentItem().h5node
        self.__displayData(node, 0)

    def __switchMdiView(self):
        if self.mdiArea.viewMode() == self.mdiArea.TabbedView:
            self.mdiArea.setViewMode(self.mdiArea.SubWindowView)
        else:
            self.mdiArea.setViewMode(self.mdiArea.TabbedView)

    def __displayLegend(self, checked):
        activePlot = self.mdiArea.activeSubWindow().widget()
        activePlot.showLegend(checked)
        
    def __popupH5TreeMenu(self, point):
        if self.h5tree.model().rowCount() == 0:
            return
        globalPos = self.h5tree.mapToGlobal(point)
        self.h5treeMenu.exec_(globalPos)

    def __popupDataListMenu(self, point):
        if self.dataList.model().rowCount() == 0:
            return
        globalPos = self.dataList.mapToGlobal(point)
        self.dataListMenu.exec_(globalPos)

    def __updateWindowMenu(self):
        self.windowMenu.clear()
        if  len(self.mdiArea.subWindowList()) == 0:
            return
        self.windowMenu.addAction(self.closeActiveSubwindowAction)
        self.windowMenu.addAction(self.closeAllAction)
        self.windowMenu.addSeparator()
        self.windowMenu.addAction(self.switchMdiViewAction)
        if self.mdiArea.viewMode() == self.mdiArea.TabbedView:
            self.switchMdiViewAction.setText('Subwindow view')
        else:
            self.switchMdiViewAction.setText('Tabbed view')            
            self.windowMenu.addAction(self.cascadeAction)
            self.windowMenu.addAction(self.tileAction)
        self.windowMenu.addSeparator()
        activeSubWindow = self.mdiArea.activeSubWindow()
        for window in self.mdiArea.subWindowList():
            action = self.windowMenu.addAction(window.windowTitle())
            action.setCheckable(True)
            action.setChecked(window == activeSubWindow)
            self.connect(action, QtCore.SIGNAL('triggered()'), self.windowMapper, QtCore.SLOT('map()'))
            self.windowMapper.setMapping(action, window)


    def __subwindowActivatedSlot(self, window):
        if window is None:
            return
        widget = window.widget()
        if isinstance(widget, PlotWidget):
            legend = widget.legend()
            self.displayLegendAction.setChecked(legend is not None)
            self.overlayAction.setChecked(widget.overlay())

    def __editLegendText(self):
        """Change the legend text."""
        activePlot = self.mdiArea.activeSubWindow().widget()
        activePlot.editLegendText()

    def __editPlotTitle(self):
        activePlot = self.mdiArea.activeSubWindow().widget()
        title, ok, = QtGui.QInputDialog.getText(self, self.tr('Change Plot Title'), self.tr('Plot title:'), QtGui.QLineEdit.Normal, activePlot.title().text())
        if ok:
            activePlot.setTitle(title)
        
    def __configurePlots(self):
        """Interactively allow the user to configure everything about
        the plots."""
        activePlot = self.mdiArea.activeSubWindow().widget()
        self.plotConfig.setVisible(True)
        ret = self.plotConfig.exec_()
        if ret == QtGui.QDialog.Accepted:
            pen = self.plotConfig.getPen()
            symbol = self.plotConfig.getSymbol()
            style = self.plotConfig.getStyle()
            attribute = self.plotConfig.getAttribute()
            activePlot.reconfigureSelectedCurves(pen, symbol, style, attribute)

    def __togglePlotVisibility(self, hide):
        activePlot = self.mdiArea.activeSubWindow().widget()
        activePlot.toggleSelectedCurves()

    def __deselectAllCurves(self):
        activePlot = self.mdiArea.activeSubWindow().widget()
        activePlot.deselectAllCurves()

    def __plotPresynapticVm(self):
        """This is for easily displaying the data for presynaptic
        cells of the current cell. Depends on my specific file
        structure."""
        activePlot = self.mdiArea.activeSubWindow().widget()
        paths = activePlot.getDataPathsForSelectedCurves()
        files = []
        for path in paths:
            filepath = self.h5tree.getOpenFileName(path)
            net_file_name = self.data_model_dict[filepath]
            self.h5tree.addH5Handle(net_file_name)
            data = self.h5tree.getData(net_file_name + '/network/synapse')
            cell_name = path.rpartition('/')[-1]
            presyn_vm_paths = []
            presyn_vm = []
            for row in data:
                if row[1].startswith(cell_name):
                    print 'Presynaptic cell for', cell_name, 'is', row[0]
                    tmp_path = '%s/Vm/%s' % (filepath, row[0].partition('/')[0])
                    try:
                        tmp = self.h5tree.getData(tmp_path)
                        ts = self.h5tree.getTimeSeries(tmp_path)
                        presyn_vm_paths.append(tmp_path)
                        vm = numpy.zeros(len(tmp))
                        vm[:] = tmp[:]
                        time = numpy.zeros(len(ts))
                        time[:] = ts[:]
                        presyn_vm.append((time, vm))
                    except KeyError:
                        print tmp_path, ': not available in Vm data'
            activePlot.addPlotCurveList(presyn_vm_paths, presyn_vm, mode='curve')

    def __plotPresynapticSpikes(self):
        """This is for easily displaying the data for presynaptic
        cells of the current cell. Depends on my specific file
        structure."""
        activePlot = self.mdiArea.activeSubWindow().widget()
        paths = activePlot.getDataPathsForSelectedCurves()
        files = []
        # self.dataList.clear()
        for path in paths:
            filepath = self.h5tree.getOpenFileName(path)
            net_file_name = self.data_model_dict[filepath]
            self.h5tree.addH5Handle(net_file_name)
            data = self.h5tree.getData(net_file_name + '/network/synapse')
            cell_name = path.rpartition('/')[-1]
            presyn_spike_paths = []
            presyn_spike = []
            for row in data:
                if row[1].startswith(cell_name):
                    print 'Presynaptic cell for', cell_name, 'is', row[0]
                    tmp_path = '%s/spikes/%s' % (filepath, row[0].partition('/')[0])
                    try:
                        tmp = self.h5tree.getData(tmp_path)
                        ts = self.h5tree.getTimeSeries(tmp_path)
                        presyn_spike_paths.append(tmp_path)
                        vm = numpy.zeros(len(tmp))
                        vm[:] = tmp[:]
                        time = numpy.zeros(len(ts))
                        time[:] = ts[:]
                        presyn_spike.append((time, vm))
                    except KeyError:
                        print tmp_path, ': not available in Vm data'
            activePlot.addPlotCurveList(presyn_spike_paths, presyn_spike, mode='raster')

    def __vShiftSelectedPlots(self):
        """Shift the selected plots vertically"""
        activePlot = self.mdiArea.activeSubWindow().widget()
        shift, ok, = QtGui.QInputDialog.getText(self, 'Shift plot vertically', 'Enter y-shift')
        if ok:
            activePlot.vShiftSelectedPlots(float(shift))
            
    def __vScaleSelectedPlots(self):
        activePlot = self.mdiArea.activeSubWindow().widget()
        scale, ok, = QtGui.QInputDialog.getText(self, 'Scale plots', 'Enter scale factor')
        if ok:
            activePlot.vScaleSelectedPlots(float(scale))

        
    def __savePlot(self):
        if self.mdiArea.activeSubWindow() is None:
            return
        activePlot = self.mdiArea.activeSubWindow().widget()
        if isinstance(activePlot, PlotWidget):
            filename = QtGui.QFileDialog.getSaveFileName(self,
                                                     'Save plot as',
                                                     '%s.png' % (str(self.mdiArea.activeSubWindow().windowTitle())),
                                                     'Images (*.png *.jpg *.gif);; All files (*.*)')
            activePlot.savePlotImage(filename)


    def __saveScreenshot(self):
        activeSubWindow = self.mdiArea.activeSubWindow()
        if activeSubWindow is None:
            print 'Active subwindow is empty!'
            return
        activePlot = activeSubWindow.widget()
        pixmap = QtGui.QPixmap.grabWidget(activePlot)
        filename = QtGui.QFileDialog.getSaveFileName(self,
                                                     'Save plot as',
                                                     '%s.png' % (str(self.mdiArea.activeSubWindow().windowTitle())),
                                                     'Images (*.png *.jpg *.gif);; All files (*.*)')
        pixmap.save(filename)


    def __fitSelectedPlots(self):
        """Do curve fitting on the selected plots."""
        activePlot = self.mdiArea.activeSubWindow().widget()
        activePlot.fitSelectedCurves()
        
    def __showStatusMessage(self, message):
        self.statusBar().showMessage(message)


    def __plotFilteredLFP(self, method=analyzer.blackmann_windowedsinc_filter, newplot=True):
        """Filter LFP at 450 Hz upper cutoff and plot"""
        cutoff, correct = self.settings.value('lfpfilter/cutoff').toFloat()
        if not correct:
            cutoff = 450.0
        rolloff, correct = self.settings.value('lfpfilter/rolloff').toFloat()
        if not correct:
            rolloff = cutoff/50.0
        file_path_dict = defaultdict(list)
        for item in self.h5tree.selectedItems():
            path = item.path()
            print 'Filtering:', path
            file_path_dict[self.h5tree.getOpenFileName(path)].append(path)
        if not file_path_dict:
            return        
        data_dict = defaultdict(list)
        mdiChild = self.mdiArea.activeSubWindow()
        if newplot or (mdiChild is None) or (mdiChild.widget() is None):
            print 'Creating new plot widget'
            mdiChild = self.mdiArea.addSubWindow(PlotWidget())
            mdiChild.setWindowTitle('Plot %d' % len(self.mdiArea.subWindowList()))
        
        for filename in file_path_dict.keys():
            path_list = file_path_dict[filename]
            data_list = []
            for path in path_list:
                tmp_data = self.h5tree.getData(path)
                data = numpy.zeros(len(tmp_data))
                data[:] = tmp_data[:]
                data_list.append(data)
            sampling_interval = self.h5tree.get_plotdt(filename)
            filtered_data_list = method(data_list, sampling_interval, cutoff, rolloff)
            ts = self.h5tree.getTimeSeries(path_list[0])
            plot_data_list = [(ts, data) for data in filtered_data_list]
            mdiChild.widget().addPlotCurveList(path_list, plot_data_list, curvenames=path_list)
            self.connect(mdiChild.widget(), QtCore.SIGNAL('curveSelected'), self.__showStatusMessage)
        mdiChild.showMaximized()
        
    # def __plotFilteredLFPNewWin(self):
    #     self.__plotFilteredLFP(newplot=True)

    # def __plotFilteredLFPCurrentWin(self):
    #     print 'Here'
    #     self.__plotFilteredLFP(newplot=False)

    def __plotBlackmannFilteredLFPNewWin(self):
        self.__plotFilteredLFP(method=analyzer.blackmann_windowedsinc_filter, newplot=True)

    def __plotBlackmannFilteredLFPCurrentWin(self):
        self.__plotFilteredLFP(method=analyzer.blackmann_windowedsinc_filter, newplot=False)
        
    def __plotFIRFilteredLFPNewWin(self):
        self.__plotFilteredLFP(method=analyzer.fir_filter, newplot=True)

    def __plotFIRFilteredLFPCurrentWin(self):
        self.__plotFilteredLFP(method=analyzer.fir_filter, newplot=False)
        
    def __showPreferencesDialog(self):
        dialog = QtGui.QDialog(self)
        layout = QtGui.QGridLayout()
        row = 0
        textboxes = {}
        for key in self.settings.allKeys():
            label = QtGui.QLabel(key)
            textbox = QtGui.QLineEdit()            
            textboxes[key] = textbox
            textbox.setText(self.settings.value(key).toString())
            layout.addWidget(label, row, 0)
            layout.addWidget(textbox, row, 1)
            row += 1
        button = QtGui.QPushButton()
        button.setText('Cancel')
        self.connect(button, QtCore.SIGNAL('clicked()'), dialog.reject)
        layout.addWidget(button, row, 0)
        button = QtGui.QPushButton()
        button.setText('OK')
        self.connect(button, QtCore.SIGNAL('clicked()'), dialog.accept)
        layout.addWidget(button, row, 1)
        dialog.setLayout(layout)
        dialog.exec_()
        if dialog.result() == dialog.Accepted:
            for key, textbox in textboxes.items():
                print 'set', key, 'to', textbox.text()
                self.settings.setValue(key, textbox.text())

    def __overlayPlots(self, value):
        mdiChild = self.mdiArea.activeSubWindow()
        if mdiChild is not None and  mdiChild.widget() is not None:
            mdiChild.widget().setOverlay(value)

    def __saveSelectedDataToCsvFile(self):
        filename = QtGui.QFileDialog.getSaveFileName(self, 'Save data to file', 'Untitled.csv', self.tr('Comma separated values  (*.csv)'))
        if filename:
            self.h5tree.saveSelectedDataToCsvFile(str(filename))

    def __plotPowerSpectrumSelectedCurves(self, subwindow=None, start=0, end=None, apply_filter=None, method='fft', newplot=True):
        """Plot the power spectrum of the selected data after applying a filter."""
        file_path_dict = defaultdict(list)
        for item in self.h5tree.selectedItems():
            path = item.path()
            file_path_dict[self.h5tree.getOpenFileName(path)].append(path)
        if not file_path_dict:
            return        
        data_dict = defaultdict(list)
        mdiChild = subwindow
        if newplot or (mdiChild is None) or (mdiChild.widget() is None):
            print 'Creating new plot widget'
            mdiChild = self.mdiArea.addSubWindow(PlotWidget())
            mdiChild.setWindowTitle('Plot %d' % len(self.mdiArea.subWindowList()))
        plotWidget = mdiChild.widget()
        for filename in file_path_dict.keys():
            plotdts = []
            path_list = file_path_dict[filename]
            data_list = []
            sampling_interval = self.h5tree.get_plotdt(filename)
            simtime = self.h5tree.get_simtime(filename)
            if end is None or end > simtime:
                end = simtime
            end = int(end / sampling_interval + 0.5)
            start = int(start/sampling_interval + 0.5)
            for path in path_list:
                tmp_data = self.h5tree.getData(path)
                data = numpy.zeros(end-start)
                data[:] = tmp_data[start:end]
                data_list.append(data)
                plotdts.append(sampling_interval)
            if apply_filter == 'blackman':
                filtered_data_list = analyzer.blackmann_windowedsinc_filter(data_list, sampling_interval)
            elif apply_filter == 'fir':
                filtered_data_list = analyzer.fir_filter(data_list, sampling_interval)
            else:
                filtered_data_list = data_list
            new_datalist = []
            for ii in range(len(filtered_data_list)):
                data = filtered_data_list[ii]
                if method == 'fft':                    
                    xform = numpy.fft.rfft(data)
                    freq = numpy.linspace(0, 0.5/plotdts[ii], len(xform))
                    new_datalist.append((freq, numpy.abs(xform)**2))
            plotWidget.addPlotCurveList(path_list, new_datalist, curvenames=path_list)
            self.connect(plotWidget, QtCore.SIGNAL('curveSelected'), self.__showStatusMessage)
        plotWidget.setAxisTitle(0, 'Power')
        plotWidget.setAxisTitle(2, 'Frequency (Hz)')
                
        plotWidget.setAxisScaleEngine(plotWidget.xBottom, Qwt.QwtLog10ScaleEngine())
        plotWidget.setAxisScale(plotWidget.xBottom, 1, 1000)
        plotWidget.setAxisScaleEngine(plotWidget.yLeft, Qwt.QwtLog10ScaleEngine())
        # plotWidget.setAxisScale(plotWidget.yLeft, 0, 1e10)
        mdiChild.showMaximized()
        
    def __plotPowerSpectrum(self):
        dialog = QtGui.QDialog(self)
        filterLabel = QtGui.QLabel(dialog)
        filterLabel.setText('Filter')
        filterCombo = QtGui.QComboBox()
        filterCombo.addItem('Blackmann-windowed sinc')
        filterCombo.addItem('FIR')
        filterCombo.addItem('None')
        methodLabel = QtGui.QLabel('Transformation method')
        methodCombo = QtGui.QComboBox()
        methodCombo.addItem('FFT')
        dataRangeLabel = QtGui.QLabel(dialog)
        dataRangeLabel.setText('Data range:')
        dataStartText = QtGui.QLineEdit(dialog)
        dataStartText.setText('0.0')
        dataEndText =  QtGui.QLineEdit(dialog)
        dataEndText.setText('5.0')
        newplotButton = QtGui.QRadioButton('New plot window', dialog)
        okButton = QtGui.QPushButton('OK')
        cancelButton = QtGui.QPushButton('Cancel')
        self.connect(okButton, QtCore.SIGNAL('clicked()'), dialog.accept)
        self.connect(cancelButton, QtCore.SIGNAL('clicked()'), dialog.reject)
        layout = QtGui.QGridLayout()
        layout.addWidget(filterLabel, 0, 0)
        layout.addWidget(filterCombo, 0, 1)
        layout.addWidget(methodLabel, 1, 0)
        layout.addWidget(methodCombo, 1, 1)
        layout.addWidget(dataRangeLabel, 2, 0)
        layout.addWidget(dataStartText, 2, 1)
        layout.addWidget(dataEndText, 2, 2)
        layout.addWidget(newplotButton, 3, 0, 1, 2)
        layout.addWidget(okButton, 4, 0)
        layout.addWidget(cancelButton, 4, 1)
        dialog.setLayout(layout)
        activeSubWindow = self.mdiArea.activeSubWindow()
        dialog.exec_()
        if dialog.result() == dialog.Accepted:
            filterName = None
            if filterCombo.currentIndex() == 0:
                filterName = 'blackman'
            elif filterCombo.currentIndex() == 1:
                filterCombo = 'fir'
            method = None
            if methodCombo.currentIndex() == 0:
                method = 'fft'
            else:
                method = None
            newplot = newplotButton.isChecked()
            start, ok = dataStartText.text().toFloat()
            
            if not ok:
                print 'Need a number for data start time'
                start = 0.0
            end, ok = dataEndText.text().toFloat()
            if not ok:
                print 'Need a number for data end time'            
                end = None
            self.__plotPowerSpectrumSelectedCurves(subwindow=activeSubWindow, start=start, end=end, apply_filter=filterName, method=method, newplot=newplot)

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    QtGui.qApp = app
    mainwin = DataVizWidget()
    mainwin.show()
    app.exec_()
# 
# dataviz.py ends here
