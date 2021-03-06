# datasetmodel.py --- 
# 
# Filename: datasetmodel.py
# Description: 
# Author: Subhasis Ray
# Maintainer: 
# Created: Wed May 16 10:57:05 2012 (+0530)
# Version: 
# Last-Updated: Fri May 18 15:12:54 2012 (+0530)
#           By: subha
#     Update #: 242
# URL: 
# Keywords: 
# Compatibility: 
# 
# 

# Commentary: 
# 
# 
# 
# 

# Change log:
# 
# 
# 

# Code:

import numpy
import h5py
from PyQt4 import QtGui, QtCore, Qt

class HDFDatasetModel(QtCore.QAbstractTableModel):
    """Custom data mode for interfacing to large datasets in HDF5. It
    keeps a local view of the dataset for quick access. Whenever some
    index outside the cache is requested, the cache is updated with
    eows around that index in the centre."""
    def __init__(self, *args, **kwargs):
        QtCore.QAbstractTableModel.__init__(self, *args, **kwargs)
        self._dset = [] # HDF5 dataset
        self._cache = [] # data cache
        self._cacheStartIndex = 0
        # cache these many rows before and after the current index.
        self._cacheSize = 4001

    def setDataset(self, node):
        self._dset = node
        self._cacheData(0)

    def _cacheData(self, start):
        # if cache is not smaller than dataset or current cache is
        # valid, then do nothing.
        if len(self._cache) >= len(self._dset) or \
               (self._cacheStartIndex == start and len(self._cache) > 0):
            return
        if start >= len(self._dset) or start < 0:
            start = 0
        end = start + self._cacheSize
        if end > self._dset.shape[0]:
            end = self._dset.shape[0]        
        self._cache = self._dset[start:end]
        if (self._dset.dtype.names is None) and \
               (len(self._dset.shape) > 1):
            fields = [('f%d' % (i), self._dset.dtype.name) for i in range(self._dset.shape[1])]
            self._cache = numpy.rec.fromarrays(self._cache.transpose(), fields)
        self._cacheStartIndex = start
        
    def data(self, index, role):
        if role != Qt.Qt.DisplayRole:
            return QtCore.QVariant()
        if not index.isValid():
            return QtCore.QVariant()
        row = index.row()
        if row < 0 or row >= self._dset.shape[0]:
            return QtCore.QVariant()
        if row < self._cacheStartIndex or row >= self._cacheStartIndex + self._cacheSize:
            self._cacheData(row - (self._cacheSize-1)/2)
        _row = row - self._cacheStartIndex
        colcnt = self.columnCount(QtCore.QModelIndex())
        if index.column() >= colcnt or colcnt < 1:
            return QtCore.QVariant()
        elif colcnt == 1:
            _data = self._cache[_row]
        elif colcnt > 1:            
            _data = self._cache[_row][index.column()]
        return QtCore.QVariant(str(_data))

    def headerData(self, section, orientation, role):
        if role != Qt.Qt.DisplayRole:
            return QtCore.QVariant()
        if orientation == Qt.Qt.Vertical:
            return section
        dtype = self._dset.dtype
        if (dtype.names is not None) and (section < len(dtype.names)):
            return QtCore.QVariant(dtype.names[section])
        print
        return section
        
    def rowCount(self, modelIndex):
        if not self._dset.shape:
            return 0
        return self._dset.shape[0]

    def columnCount(self, modelIndex):
        if not self._dset.shape:
            return 0
        if self._dset.dtype.names is not None:
            return len(self._dset.dtype.names)
        if len(self._dset.shape) == 1:
            return 1
        return self._dset.shape[1]

    def sort(self, ncol, order):
        print 'About to sort'
        self.emit(QtCore.SIGNAL('layoutAboutToBeChanged()'))
        self._cacheSize = self._dset.shape[0]
        self._cacheData(0)
        field=None
        if self._cache.dtype.names:
            field = self._cache.dtype.names[ncol]
        print 'Sorting by field', field
        self._cache.sort(order=field)
        if order == Qt.Qt.DescendingOrder:
            self._cache = self._cache[::-1]
        self.emit(QtCore.SIGNAL('layoutChanged()'))
    
def test_main():
    app = QtGui.QApplication([])
    main = QtGui.QMainWindow()
    tabview = QtGui.QTableView(main)
    fd = h5py.File('test_data/network_20111025_115951_4849.h5')
    dset = fd['/network/cellnetwork/gnmda']
    dset2 = fd['/network/celltype']
    model = HDFDatasetModel()
    model.setDataset(dset)
    tabview.setModel(model)
    model2 = HDFDatasetModel()
    model2.setDataset(dset2)
    tabview2 = QtGui.QTableView(main)
    tabview2.setModel(model2)
    widget = QtGui.QWidget(main)
    widget.setLayout(QtGui.QHBoxLayout())
    widget.layout().addWidget(tabview)
    widget.layout().addWidget(tabview2)
    main.setCentralWidget(widget)
    main.show()
    app.exec_()

if __name__ == '__main__':
    test_main()

# 
# datasetmodel.py ends here
