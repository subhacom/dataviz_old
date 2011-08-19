# animate3d.py --- 
# 
# Filename: animate3d.py
# Description: 
# Author: Subhasis Ray
# Maintainer: 
# Created: Thu Aug 11 09:49:49 2011 (+0530)
# Version: 
# Last-Updated: Fri Aug 19 23:55:39 2011 (+0530)
#           By: Subhasis Ray
#     Update #: 715
# URL: 
# Keywords: 
# Compatibility: 
# 
# 

# Commentary: 
# 
# Attempt to use vtk for 3D visualization of data from Traub model simulation 
# 
# 

# Change log:
# 
# 
# 

# Code:

import sys

from collections import defaultdict
import numpy

import csv
import h5py
import vtk
from vtk.util import numpy_support as vtknp

cmp_spring_matrix = numpy.loadtxt('spring.cmp')

cmp_autumn_matrix = numpy.loadtxt('autumn.cmp')

cmp_winter_matrix = numpy.loadtxt('winter.cmp')

cmp_summer_matrix = numpy.loadtxt('summer.cmp')

cmp_bone_matrix = numpy.loadtxt('bone.cmp')

cmp_hot_matrix = numpy.loadtxt('hot.cmp')

cmp_cool_matrix = numpy.loadtxt('cool.cmp')

class TraubDataHandler(object):
    """Reader for data generated by Traub model."""
    def __init__(self):
        self.class_cell = defaultdict(list)
        self.class_pos = {}
        self.cellname = [] # List of cells
        self.pos = None    # List of positions - must have same order as cellname
        self.vm = None # List of vms - must have the same order as cellname
        self.datafile = None
        self.cellclass = []
        self.simtime = None
        self.plotdt = None

    def read_posdata(self, filename):
        """Read position data from file"""
        with open(filename, 'r') as filehandle:
            reader = csv.DictReader(filehandle, fieldnames=['cellclass', 'depth', 'start', 'end', 'dia', 'layer', 'isInTraub'], delimiter=',', quotechar='"')
            reader.next() #Skip the header row
            for row in reader:
                self.class_pos[row['cellclass']] = row
                self.cellclass.append(row['cellclass'])

    def read_celldata(self,filename):
        """Read the Vm data from the hdf5 file"""
        print 'Start read_celldata'
        self.datafile = h5py.File(filename, 'r')            
        self.vm_node = self.datafile['/Vm']
        for cellname in self.vm_node.keys():
            tmp = cellname.partition('_')
            cellclass = tmp[0]
            self.class_cell[cellclass].append(cellname)
        for cellclass in self.cellclass:
            print cellclass, len(self.class_cell[cellclass])
            self.cellname.extend(self.class_cell[cellclass])
        for cellname in self.cellname:
            if self.vm is None:
                self.vm = numpy.array(self.vm_node[cellname], order='C')
            else:
                self.vm = numpy.vstack((self.vm, numpy.array(self.vm_node[cellname], order='C')))
        print 'Finished read_celldata'
        

    def generate_cellpos(self, diascale=1.0):
        """Create random positions based on depth and diameter data
        for the cells"""
        old_pos_len = 0
        
        for cellclass in self.cellclass:
            start = float(self.class_pos[cellclass]['start'])
            end = float(self.class_pos[cellclass]['end'])
            # print cellclass, 'Start:', start, 'End:', end
            rad = float(self.class_pos[cellclass]['dia'])/2.0
            size = len(self.class_cell[cellclass])
            zpos = -numpy.random.uniform(low=start, high=end, size=size)
            rpos = rad * numpy.sqrt(numpy.random.uniform(low=0, high=1.0, size=size))
            theta = numpy.random.uniform(low=0, high=2*numpy.pi, size=size)
            xpos = rpos * numpy.cos(theta)
            ypos = rpos * numpy.sin(theta)
            pos = numpy.column_stack((xpos, ypos, zpos))
            # print cellclass, 'Positions:'
            # print pos
            if pos.size == 0:
                print 'Zero length position for', cellclass
                continue
            if self.pos is None:
                self.pos = pos
            else:
                self.pos = numpy.concatenate((self.pos, pos))
            print cellclass, 'start: %d, end: %d' % (old_pos_len, len(self.pos))
            old_pos_len = len(self.pos)
        self.pos = numpy.array(self.pos, copy=True, order='C')
        print 'Position has shape:', self.pos.shape
        
        

    def update_times(self):
        try:
            self.simtime = self.datafile.attrs['simtime']
            self.plotdt = self.datafile.attrs['plotdt']
        except KeyError, e:
            print 'simtime or plotdt attribute absent'
            self.simtime = None
            self.plotdt = None
        try:
            firstcell = self.cellname[0]
            self.num_time = len(self.vm_node[firstcell])
        except IndexError, e:
            print 'There are no Vm arrays in the data file.'
            raise e
        if self.simtime is None or self.plotdt is None:
            self.simtime = float(self.num_time)
            self.plotdt = 1.0
        
    def get_vm(self, cellclass, step):
        """Get the Vm for all cells at step ordered in the same
        sequence as cellname."""
        cellrange = self.get_range(cellclass)
        if cellrange[0] != cellrange[1]:
            try:
                vm_range = self.vm[cellrange[0]:cellrange[1], step]
                return numpy.array(vm_range, copy=True, order='C')
            except IndexError:
                print 'Index out of bounds:', cellrange, step, min([len(self.vm[ii]) for ii in range(cellrange[0], cellrange[1])])
                return numpy.array([])

    def get_range(self, cellclass):
        start = 0
        end = 0
        ii = 0

        for classname in self.cellclass:
            celllist = self.class_cell[classname]
            if classname == cellclass:
                end = start + len(celllist)
                break
            else:
                start = start + len(celllist)
        return (start, end)
            
    def __del__(self):
	if self.datafile:
	    self.datafile.close()
    
class TraubDataVis(object):
    """Visualizer for Traub model data"""
    def __init__(self):
        self.datafile = None
        self.posfile = None
        self.datahandler = TraubDataHandler()
        self.vrange = (-120e-3, 40e-3)
        self.cmap = {'SupPyrRS': cmp_spring_matrix,
                     'SupPyrFRB': cmp_summer_matrix,
                     'SupLTS': cmp_autumn_matrix,
                     'SupAxoaxonic': cmp_winter_matrix,
                     'SupBasket': cmp_bone_matrix,
                     'SpinyStellate': cmp_spring_matrix,
                     'TuftedIB': cmp_winter_matrix,
                     'TuftedRS': cmp_summer_matrix,
                     'NontuftedRS': cmp_autumn_matrix,
                     'DeepBasket': cmp_winter_matrix,
                     'DeepAxoaxonic': cmp_summer_matrix,
                     'DeepLTS': cmp_spring_matrix,
                     'TCR': cmp_bone_matrix,
                     'nRT': cmp_hot_matrix
                     }
        self.static_colors = {'SupPyrRS': (0.0, 0.0, 1.0),
                     'SupPyrFRB': (0.0, 1.0, 0.0),
                     'SupLTS': (1.0, 0.0, 0.0),
                     'SupAxoaxonic': (1.0, 0.0, 1.0),
                     'SupBasket': (1.0, 1.0, 0.0),
                     'SpinyStellate': (0.0, 1.0, 1.0),
                     'TuftedIB': (1.0, 0.5, 0.5),
                     'TuftedRS': (0.5, 0.5, 1.0),
                     'NontuftedRS': (0.5, 1.0, 0.5),
                     'DeepBasket': (0.2, 0.5, 1.0),
                     'DeepAxoaxonic': (1.0, 0.5, 0.2),
                     'DeepLTS': (0.5, 1.0, 0.2),
                     'TCR': (0.5, 0.2, 1.0),
                     'nRT': (1.0, 0.2, 0.5)
                     }

        # scalarbar_pos: (x_top_left, y_top_left)

    def load_data(self, posfilename, datafilename):
        self.datahandler.read_posdata(posfilename)
        self.datahandler.read_celldata(datafilename)
        self.datahandler.generate_cellpos()
        self.datahandler.update_times()

    def setup_visualization(self, animate=True):
        self.positionSource = {}
        self.glyphSource = {}
        self.mapper = {}
        self.glyph = {}
        self.actor = {}
        self.colorXfun = {}
        self.scalarBar = {}
        self.renderer = vtk.vtkRenderer()
        self.renwin = vtk.vtkRenderWindow()
        self.renwin.SetSize(1280, 900)
        # self.renwin.SetFullScreen(1)
        self.renwin.AddRenderer(self.renderer)
        scalarbarX = 0.01
        scalarbarY = 0.95
        for classname in self.datahandler.cellclass:
            cellrange = self.datahandler.get_range(classname)
            if cellrange[0] == cellrange[1]:
                continue
            # print cellrange, 
            pos = self.datahandler.pos[cellrange[0]: cellrange[1]]
            print classname, 'strat-->end', cellrange
            print classname, 'Z-range', min(pos[:,2]),max(pos[:,2])
            # print pos, pos.size
            pos_array = vtknp.numpy_to_vtk(pos, deep=True)
            points = vtk.vtkPoints()
            points.SetData(pos_array)
            polydata = vtk.vtkPolyData()
            polydata.SetPoints(points)
            # polydata.GlobalReleaseDataFlagOn()            # data = self.datahandler.get_vm(0)
            
            self.positionSource[classname] = polydata
            print 'Position size:', polydata.GetPointData().GetNumberOfTuples()
            source = None
            if classname.find('Pyr') >= 0:
                print 'Cone for', classname
                source = vtk.vtkConeSource()
                source.SetRadius(1)
                source.SetResolution(20)
                source.SetHeight(2)
                source.SetDirection(0, 0, 1)
            else:                
                source = vtk.vtkSphereSource()
                source.SetRadius(1)
                source.SetThetaResolution(20)
                source.SetPhiResolution(20)
            self.glyphSource[classname] = source
            glyph = vtk.vtkGlyph3D()
            glyph.SetSource(source.GetOutput())
            glyph.SetInput(polydata)
            glyph.SetScaleModeToDataScalingOff()
            glyph.SetScaleFactor(10)
            self.glyph[classname] = glyph
            colorXfun = vtk.vtkColorTransferFunction()
            cmap_matrix = self.cmap[classname]
            values = numpy.linspace(self.vrange[0], self.vrange[1], len(cmap_matrix))
            for ii in range(len(cmap_matrix)):                
                colorXfun.AddRGBPoint(values[ii], cmap_matrix[ii][0], cmap_matrix[ii][1], cmap_matrix[ii][2])
            self.colorXfun[classname] = colorXfun
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInput(glyph.GetOutput())
            mapper.SetLookupTable(colorXfun)
            mapper.ImmediateModeRenderingOn()
            self.mapper[classname] = mapper
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetOpacity(0.5)
            self.actor[classname] = actor
            self.renderer.AddActor(actor)
            scalarBar = vtk.vtkScalarBarActor()
            scalarBar.SetLookupTable(colorXfun)
            scalarBar.SetTitle(classname)
            # scalarBar.SetNumberOfLabels(4)
            scalarBar.SetPosition(scalarbarX, scalarbarY)
            scalarbarY -= 0.07
            scalarBar.SetHeight(0.05)
            scalarBar.SetWidth(0.30)
            scalarBar.SetOrientationToHorizontal()
            scalarBar.GetTitleTextProperty().SetOrientation(90.0)
            self.scalarBar[classname] = scalarBar
            self.renderer.AddActor2D(scalarBar)
            
        # for key, value in self.mapper.items():
        #     value.GlobalImmediateModeRenderingOn()
        #     break            
        print 'End setup_visualization'

    def display(self, animate=True, movie=False, filename=None):
        print 'TraubDataVis.display::Start: animate: %d, movie: %d, filename: %s' % (animate, movie, filename)
        self.camera = vtk.vtkCamera() #self.renderer.GetActiveCamera()
        self.camera.SetPosition(0.0, 500.0, -1200.0)
        self.camera.SetFocalPoint(0, 0, -1200)
        self.camera.ComputeViewPlaneNormal()
        self.renderer.SetActiveCamera(self.camera)
        self.renderer.ResetCamera()
        if not animate:
            self.interactor = vtk.vtkRenderWindowInteractor()
            self.interactor.SetRenderWindow(self.renwin)
            self.interactor.Initialize()
            self.interactor.Start()
        else:
            self.renwin.SetOffScreenRendering(True)
            self.win2image = vtk.vtkWindowToImageFilter()
            self.win2image.SetInput(self.renwin)
	    if movie:
                self.moviewriter = vtk.vtkFFMPEGWriter()
                self.moviewriter.SetQuality(2)
                self.moviewriter.SetRate(10)
                self.moviewriter.SetInputConnection(self.win2image.GetOutputPort())
                self.moviewriter.SetFileName(filename)
                self.moviewriter.Start()
            else:
                self.imwriter = vtk.vtkPNGWriter()
                self.imwriter.SetInputConnection(self.win2image.GetOutputPort())
            time = 0.0
            for ii in range(self.datahandler.num_time):
                time += self.datahandler.plotdt
                print 'Time:', time
                for cellclass in self.datahandler.cellclass:
                    vm = self.datahandler.get_vm(cellclass, ii)
                    print cellclass, ': Length of vm: ', vm.size
                    if (vm is None) or len(vm) == 0:
                        print 'Error:', cellclass, vm
                        continue
                    print 'Size of positions:', self.positionSource[cellclass].GetPointData().GetNumberOfTuples()
                    print vm
                    self.positionSource[cellclass].GetPointData().SetScalars(vtknp.numpy_to_vtk(vm))
                    print 'Here'
                self.renwin.Render()
                print '--1'
                self.win2image.Modified()
                if movie:
                    self.moviewriter.Write()
                else:
                    self.imwriter.SetFileName('frame_%05d.png' % (ii))
                    self.imwriter.Write()
                    print 'Here'
            if movie:
                self.moviewriter.End()
        print 'TraubDataVis.display::End'

if __name__ == '__main__':
    args = sys.argv
    posfile = None
    datafile = None
    animate = False
    movie = False
    filename = 'traub_animated.avi'
    print 'Args', args, len(args)
    if len(args) >= 3:
        posfile = args[1]
        datafile = args[2]
        if len(args) > 3:
            animate = True
        if len(args) > 4:
            movie = True
            filename = args[4]
    else:
        posfile = '/home/subha/src/sim/cortical/dataviz/cellpos.csv'
        datafile = '/home/subha/src/sim/cortical/py/data/data_20101201_102647_8854.h5'
    print 'Visualizing: positions from %s and data from %s' % (posfile, datafile)
    vis = TraubDataVis()
    vis.load_data(posfile, datafile)
    vis.setup_visualization(animate=animate)
    vis.display(animate=animate, movie=movie, filename=filename)
        

# 
# animate3d.py ends here
