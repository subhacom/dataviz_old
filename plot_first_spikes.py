# plot_first_spikes.py --- 
# 
# Filename: plot_first_spikes.py
# Description: 
# Author: 
# Maintainer: 
# Created: Sat Jul 28 10:53:40 2012 (+0530)
# Version: 
# Last-Updated: Mon Aug  6 16:24:58 2012 (+0530)
#           By: subha
#     Update #: 473
# URL: 
# Keywords: 
# Compatibility: 
# 
# 

# Commentary: 
# 
# This script is for plotting the first spikes after a stimulus. I
# want to see if the same cell fires early in response to a
# stimulus. So cell identitity needs to be maintained. I also want to
# see what fraction of cells are firing early. Are these connected to
# the stimulus?
# 
# Some summary info to put in:
#
#  How many cells do fire within 10 ms?
#
#  Do they do so consistently on each stimulus? 
#
#  Is there a difference between bg-only and bg+probe stimulus?
#
#  How do these cells relate to connectivity to stimulated cells? 
#
#  Are they consistently the directly connected cells?

# Change log:
# 
# 
# 
# 

# Code:

import os
from collections import defaultdict
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import numpy as np
import h5py as h5
import random
from scipy import weave
from datetime import datetime

# These are all the files with runconfig/cellcount info with > 10 MB
# data
filenames = [
'2012_01_03/data_20120103_100645_11976.h5',
'2012_01_03/data_20120103_101152_12049.h5',
'2012_01_09/data_20120109_112852_22086.h5',
'2012_01_10/data_20120110_115732_23924.h5',
'2012_01_11/data_20120111_135100_30693.h5',
'2012_01_11/data_20120111_135144_30762.h5',
'2012_01_13/data_20120113_170727_32728.h5',
'2012_01_14/data_20120114_120027_996.h5',
'2012_01_17/data_20120117_114805_6302.h5',
'2012_01_18/data_20120118_142820_7865.h5',
'2012_01_19/data_20120119_132336_9035.h5',
'2012_01_19/data_20120119_135900_9148.h5',
'2012_01_19/data_20120119_201036_10692.h5',
'2012_01_23/data_20120123_092150_14871.h5',
'2012_01_23/data_20120123_092550_14913.h5',
'2012_01_23/data_20120123_092558_14940.h5',
'2012_01_23/data_20120123_092600_14963.h5',
'2012_01_25/data_20120125_131449_16448.h5',
'2012_01_25/data_20120125_131453_16471.h5',
'2012_01_25/data_20120125_131455_16498.h5',
'2012_01_25/data_20120125_131456_16525.h5',
'2012_01_28/data_20120128_120809_21820.h5',
'2012_01_28/data_20120128_120931_21882.h5',
'2012_01_29/data_20120129_115942_22585.h5',
'2012_01_29/data_20120129_175534_22710.h5',
'2012_01_29/data_20120129_175536_22733.h5',
'2012_01_29/data_20120129_175538_22760.h5',
'2012_01_29/data_20120129_175540_22787.h5',
'2012_01_29/data_20120129_175541_22810.h5',
'2012_01_29/data_20120129_175542_22835.h5',
'2012_01_29/data_20120129_175543_22839.h5',
'2012_02_01/data_20120201_143411_29609.h5',
'2012_02_01/data_20120201_204744_29839.h5',
'2012_02_03/data_20120203_144709_31418.h5',
'2012_02_03/data_20120203_144711_31441.h5',
'2012_02_03/data_20120203_144712_31468.h5',
'2012_02_06/data_20120206_112440_1220.h5',
'2012_02_06/data_20120206_112441_1248.h5',
'2012_02_08/data_20120208_114141_4344.h5',
'2012_02_08/data_20120208_114143_4367.h5',
'2012_02_08/data_20120208_115556_4589.h5',
'2012_02_10/data_20120210_153047_7156.h5',
'2012_02_10/data_20120210_153833_7522.h5',
'2012_02_16/data_20120216_172956_12356.h5',
'2012_02_28/data_20120228_175456_20931.h5',
'2012_03_09/data_20120309_092324_5012.h5',
'2012_03_09/data_20120309_092344_5040.h5',
'2012_03_13/data_20120313_195421_10938.h5',
'2012_03_13/data_20120313_195423_10961.h5',
'2012_03_13/data_20120313_195424_10984.h5',
'2012_03_17/data_20120317_133359_13759.h5',
'2012_03_17/data_20120317_133412_13793.h5',
'2012_03_17/data_20120317_133413_13796.h5',
'2012_03_19/data_20120319_181924_19565.h5',
'2012_03_19/data_20120319_181926_19610.h5',
'2012_03_19/data_20120319_181927_19640.h5',
'2012_03_19/data_20120319_183805_31958.h5',
'2012_03_22/data_20120322_114922_24526.h5',
'2012_03_22/data_20120322_115005_24555.h5',
'2012_03_22/data_20120322_115006_24578.h5',
'2012_03_22/data_20120322_115007_24601.h5',
'2012_03_24/data_20120324_172342_4406.h5',
'2012_03_24/data_20120324_172345_4429.h5',
'2012_03_24/data_20120324_172347_4452.h5',
'2012_03_24/data_20120324_172349_4483.h5',
'2012_03_26/data_20120326_093746_5495.h5',
'2012_03_26/data_20120326_093747_5518.h5',
'2012_03_26/data_20120326_093748_5541.h5',
'2012_03_26/data_20120326_093749_5564.h5',
'2012_03_26/data_20120326_093750_5589.h5',
'2012_03_28/data_20120328_095225_25298.h5',
'2012_03_28/data_20120328_095226_25321.h5',
'2012_03_28/data_20120328_095228_25344.h5',
'2012_03_28/data_20120328_095229_25371.h5',
'2012_03_28/data_20120328_095234_25406.h5',
'2012_03_30/data_20120330_091516_27020.h5',
'2012_03_30/data_20120330_091517_27043.h5',
'2012_03_30/data_20120330_091518_27066.h5',
'2012_03_30/data_20120330_091519_27093.h5',
'2012_03_30/data_20120330_091520_27120.h5',
'2012_04_02/data_20120402_154315_2851.h5',
'2012_04_02/data_20120402_154315_2853.h5',
'2012_04_02/data_20120402_154316_2855.h5',
'2012_04_02/data_20120402_154317_2914.h5',
'2012_04_02/data_20120402_154318_2943.h5',
'2012_04_04/data_20120404_093406_14222.h5',
'2012_04_04/data_20120404_093408_14277.h5',
'2012_04_04/data_20120404_093409_14316.h5',
'2012_04_04/data_20120404_093410_14339.h5',
'2012_04_04/data_20120404_093411_14379.h5',
'2012_04_06/data_20120406_120014_29860.h5',
'2012_04_06/data_20120406_120018_29940.h5',
'2012_04_06/data_20120406_120019_29963.h5',
'2012_04_06/data_20120406_120020_30001.h5',
'2012_04_06/data_20120406_120022_30039.h5',
'2012_04_09/data_20120409_092925_10461.h5',
'2012_04_10/data_20120410_092059_29226.h5',
'2012_04_10/data_20120410_092102_29305.h5',
'2012_04_10/data_20120410_092104_29340.h5',
'2012_04_24/data_20120424_145719_7507.h5',
'2012_04_26/data_20120426_132826_7763.h5',
'2012_04_26/data_20120426_142250_7843.h5',
'2012_04_26/data_20120426_142251_7866.h5',
'2012_04_26/data_20120426_142300_7898.h5',
'2012_04_30/data_20120430_112233_16317.h5',
'2012_04_30/data_20120430_112234_16352.h5',
'2012_04_30/data_20120430_112235_16381.h5',
'2012_04_30/data_20120430_112240_16481.h5',
'2012_05_01/data_20120501_163950_25700.h5',
'2012_05_03/data_20120503_093603_26726.h5',
'2012_05_07/data_20120507_194518_31778.h5',
'2012_05_09/data_20120509_184603_2179.h5',
'2012_05_10/data_20120510_171659_3930.h5',
'2012_05_10/data_20120510_173715_4036.h5',
'2012_05_11/data_20120511_162701_5850.h5',
'2012_05_13/data_20120513_210447_9261.h5',
'2012_05_22/data_20120522_152734_10973.h5',
'2012_06_23/data_20120623_153426_27376.h5',
'2012_06_23/data_20120623_153426_27377.h5',
'2012_06_29/data_20120629_154728_24179.h5',
'2012_06_29/data_20120629_154728_24180.h5',
'2012_06_29/data_20120629_154728_24181.h5',
'2012_07_06/data_20120706_010425_2293.h5',
'2012_07_06/data_20120706_010425_2294.h5',
'2012_07_12/data_20120712_121129_32273.h5',
'2012_07_12/data_20120712_121129_32274.h5',
'2012_07_12/data_20120712_121129_32275.h5',
'2012_07_19/data_20120719_095615_32186.h5',
'2012_07_24/data_20120724_171405_17858.h5',
'2012_07_30/data_20120730_150206_20338.h5',
]

def calculate_stim_times(files):
    """Returns a dict of (file, background-simulus-times) for each
    file in `files` with such info."""
    times = {}
    for f in files:
        try:
            stim = f['/stimulus/stim_bg'][:]
            stime = float(dict(f['/runconfig/scheduling'])['simtime'])
            dt = stime / (len(stim))
            ix = np.nonzero(np.diff(stim) > 0)[0]
            times[f] = ix * dt
        except KeyError:
            print f.filename, 'does not have stimulus info or runconfig info'
            continue
    return times

def get_early_spikes(stim_times, celltype, t):
    """`stim_times` should be a dict containing (file,
    background-stimulus-times) and this function will return a list of
    spike times where there was a spike within t s after the stimulus"""
    early = defaultdict(list)
    for f, st in stim_times.items():
        for cell in f['/spikes']:
            if cell.startswith(celltype):
                data = f['/spikes'][cell][:]
                deltas = []
                for x in st:
                    dt = np.where(((data - x) < t) & (data > x), data-x, 0.0)
                    dt = np.array(dt[dt > 0])
                    deltas = np.r_[deltas, dt]
                if len(deltas) > 0:
                    early[f].append((cell, deltas))
    return early

def plot_early_spikes(files, celltype, t):
    stim_times = calculate_stim_times(files)
    early = get_early_spikes(stim_times, celltype, t)
    for f, data in early.items():
        fig = plt.figure()
        ax = fig.add_subplot(211)
        ax.set_title(f.filename)
        d = []
        for ii in range(len(data)):
            d.append(data[ii][1])
        plt.hist(np.concatenate(d), bins=np.arange(-0.5, 10.5, 1.0)*1e-3)
        # bg = f['/stimulus/stim_bg'][:]
        # stime = float(dict(f['/runconfig/scheduling'])['simtime'])
        # plt.plot(np.linspace(0, stime, len(bg)), bg * ii / np.max(bg))
        # plt.legend()
        d = dict(f['/runconfig/cellcount'])
        y = np.sum(ax.get_ylim()) / 2.0
        x = np.sum(ax.get_xlim()) / 2.0
        ax = fig.add_subplot(212)
        counts = [int(v) for v in d.values()]        
        cells = d.keys()
        bars = ax.bar(np.arange(len(counts))+0.5, counts)
        # plt.xticks(np.arange(0, len(counts), 1.0), d.keys(), rotation=45)
        for ii in range(len(bars)):
            ax.text(bars[ii].get_x() + bars[ii].get_width()/2.0, 1, cells[ii], va='bottom', rotation='vertical')
        img_filename = os.path.basename(f.filename).replace('.h5', '.png').replace('data_', 'ss_spiketime_hist_')
        plt.savefig(img_filename, bbox_inches=0)
        plt.show()

def plot_isi_hist(filenames, celltype, count):
    for fname in filenames:
        try:
            f = h5.File(fname, 'r')
            print 'Processing', f.filename
            cells = [cell for cell in f['spikes'] if cell.startswith(celltype)]
            onset = float(dict(f['/runconfig/stimulus'])['onset'])
            if len(cells) == 0:
                print 'Cell count 0 for', f.filename
                return
            indices = range(len(cells))
            if count < len(cells):
                random.shuffle(indices)
                indices = indices[:count]
            fig = plt.figure()        
            fig.set_size_inches(21, 12, forward=True)
            fig.suptitle(f.filename)
            stiminfo = dict(f['/runconfig/stimulus'])
            schedinfo = dict(f['/runconfig/scheduling'])
            cellcount = dict(f['/runconfig/cellcount'])
            inhibitory = sum([int(v) for k, v in cellcount.items() if k in ['DeepBasket', 'DeepAxoaxonic', 'DeepLTS', 'SupBasket', 'SupAxoaxonic', 'SupLTS']])
            bins = np.arange(0, float(dict(f['/runconfig/stimulus'])['bg_interval']), 5e-3)
            data = [f['spikes'][cells[ii]][:] for ii in indices]
            data = [d[d > onset] for d in data]
            print celltype
            print 'file simtime bginterval ppinterval spikecount cellcount inhibitory tcr stimulated burstlength spikesperburst'
            print os.path.basename(f.filename), schedinfo['simtime'], stiminfo['bg_interval'], stiminfo['isi'], np.mean([len(d) for d in data]), len(cells), inhibitory, cellcount['TCR'], stiminfo['bg_count'],
            totburstlength = 0.0
            totspikesperburst  = 0.0
            for ii in range(len(data)):
                # ax = fig.add_subplot(len(data), 2, 2*ii+1)
                # n, bins, patches = ax.hist(np.diff(data[ii]), bins=bins, normed=True)            
                # ax.set_title('%s, SS: %d, total spikes: %d' % (cells[indices[ii]], len(cells), len(data[ii])))
                # ax = fig.add_subplot(len(data), 2, 2*ii+2)
                bstarts, blength, scounts = c_get_burst_stat(data[ii], onset)
                if blength:
                    # ax.plot(bstarts, np.array(blength)*1e3, '^-.')
                    # ax.plot(bstarts, np.array(scounts), 'o-.')
                    totburstlength += np.mean(blength)
                    totspikesperburst += np.mean(scounts)
                else:
                    pass
                    # ax.plot(data[ii], np.ones(len(data[ii])), 'x')
            print totburstlength / len(data), totspikesperburst/len(data)
            # plt.show()
            # plt.savefig(os.path.basename(f.filename) + '.isi_burst.png')
            f.close()
        except IOError:
            print 'IOError opening:', fname

def c_get_burst_stat(data, onset, minspikes=4, maxinterval=10e-3):
    """Find if there are bursts of spikes in this data. Burst is
    defined as a sequence of at least `minspikes` spikes within
    `maxinterval` time of each other."""
    data = data[data > onset].copy()
    code = """
           int ii, inburst=0, sc = 0, length = Ndata[0];
           py::tuple results(3);
           py::list bstart, blen, scount;
           double bl = 0.0, bs = 0.0, dt = 0.0;
           for ( ii = 1; ii < length; ++ii){
               dt = data[ii] - data[ii-1];
               if (dt < maxinterval){
                   bl += dt;
                   sc += 1;
                   if (!inburst){
                       bs = data[ii];
                       inburst = 1;
                   } else if ((ii == length - 1) && (sc > minspikes - 1)){
                       blen.append(PyFloat_FromDouble(bl));
                       scount.append(PyInt_FromLong(sc+1));
                       bstart.append(bs);
                   }
               } else if (inburst){ // this isi signifies end of a burst
                   if (sc > minspikes - 1){
                       blen.append(PyFloat_FromDouble(bl));
                       scount.append(PyInt_FromLong(sc+1));
                       bstart.append(bs);
                   }
                   bl = 0.0;
                   sc = 0;
                   inburst = 0;
               }
           }
           results[0] = bstart;
           results[1] = blen;
           results[2] = scount;
           return_val = results;                       
           """
    res = weave.inline(code, ['data', 'minspikes', 'maxinterval'])
    return res
    
def get_burst_stat(data, onset, minspikes=4, maxinterval=10e-3):
    data = data[data>onset].copy()
    isi = np.diff(data)
    spikes = 0
    inburst = False
    burstlength = 0
    burstlengthlist = []
    spikecountlist = []
    burststarts = []
    start = -1
    for index in range(len(isi)):
        dt = isi[index]
        if dt < maxinterval:
            # print '^',data[index]
            burstlength += dt
            if not inburst:
                spikes = 2
                inburst = True
                start = data[index]
            else:
                spikes += 1
                if (index == len(isi) - 1) and (spikes > minspikes):
                    burstlengthlist.append(burstlength)
                    spikecountlist.append(spikes)                    
                    burststarts.append(start)

        else:
            if inburst:
                inburst = False
                # print 'v', data[index]
                if spikes > minspikes:
                    burstlengthlist.append(burstlength)
                    spikecountlist.append(spikes)
                    burststarts.append(start)
                burstlength = 0.0
                spikes = 0
    return (burststarts, burstlengthlist, spikecountlist)

import numpy.testing as tst

def test_burst_stat():
    data = np.array([0.001, 0.002, 0.003, 0.004, 0.005,
                     1.001, 1.003, 1.005, 1.007, 1.008, 
                     2.001, 
                     2.011, 2.012, 2.013, 2.014, 2.015, 2.016,
                     2.027, 2.028])
    onset = 1.0
    starts, lengths, counts = c_get_burst_stat(data, onset)
    print starts
    assert(len(starts) == 2)
    np.allclose(starts[0], 1.001) # bad
    np.allclose(starts[1], 2.011) # bad
    print lengths
    assert(len(lengths) == 2)
    np.allclose(lengths[0], 0.007)
    np.allclose(lengths[1], 0.005)
    print counts
    assert(len(counts) == 2)
    assert(counts[0] == 5)
    assert(counts[1] == 6)
    print 'Test 1: OK'
    data = np.r_[data, 2.027]
    starts, lengths, counts = get_burst_stat(data, onset)
    print starts
    assert(len(starts) == 2)
    np.allclose(starts[0], 1.001) # bad
    np.allclose(starts[1], 2.011) # bad
    print lengths
    assert(len(lengths) == 2)
    np.allclose(lengths[0], 0.007)
    np.allclose(lengths[1], 0.005)
    print counts
    assert(len(counts) == 2)
    assert(counts[0] == 5)
    assert(counts[1] == 6)
    print 'Test 2: OK'

testing = False
if __name__ == '__main__':
    if testing:
        test_burst_stat()
    else:
        datadir = '/data/subha/cortical/py/data'
        # files = [h5.File(os.path.join(datadir, name), 'r') for name in filenames]
        files = [os.path.join(datadir, name) for name in filenames]
        start = datetime.now()
        plot_isi_hist(files, 'SpinyStellate', 10)
        end = datetime.now()
        dt = end - start
        print 'Total time:', dt.seconds + dt.microseconds * 1e-6
        # plot_early_spikes(files, 'SpinyStellate', 10e-3)
        # for f in files: f.close()
        

# 
# plot_first_spikes.py ends here
