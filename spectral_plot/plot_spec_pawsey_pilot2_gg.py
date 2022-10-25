#!/usr/bin/env python

#################################################
#    
#     Script to plot spectra output from casa
#    
#        Elizabeth Mahony, April 2021
#   updated April 2022 for pilot 2 data
#     (with credit to James Allison as the plotting code mostly came from miriad_pipe.py)
#
#   Modified by Gordon German (GWHG) Oct 2022:
#       Refactored component processing in main into processComponent()
#       Added path templates
#       Added multiprocessing
##################################################

import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pylab as plt
import numpy as np
import math 
from astropy.io import fits
from astropy.io import votable
from astropy.io import ascii
from astropy.table import Table
from matplotlib import rc
import glob
from astropy.coordinates import match_coordinates_sky
from astropy.coordinates import SkyCoord
from astropy import units as u
import argparse
#import numpy.ma as ma

# GWHG
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from time import time
import tarfile
import S3Object as S3
import json
from get_access_keys import *

#############################################################################################################
######################################### USER EDIT SECTION #################################################

##define constants:
hi_rest=1420.40575177
c=2.99792458e5

# Number of cores requested - GWHG
NUMCORES = 25 
# Name for tarball of results
TARPATH = '/mnt/shared/flash_test/outputs/%s' # 'root' directory for tarring operation - GWHG
TARNAME = 'SB%s_output_plots_and_ascii.tar.gz'   # Template for tarball name - GWHG

PLOT = True # Generate the plots - GWHG
ARCHIVE = True # tar and push results to Acacia - GWHG

# DATA PATHS relative to CWD - GWHG
GlobTemplate = 'data/sourceSpectra/*'
CatalogueTemplate = 'data/catalogues/selavy-image.i*.SB%s.cont.*taylor.0.restored*.components.xml'
SpecHduTemplate = 'data/sourceSpectra/%s/SourceSpectra/spec_*.fits'
ContCubeTemplate = 'data/contcubes/%s/spectra/spectrum_contcube_SB%s_component_%s.txt'
NoiseTemplate = 'data/noise/%s/NoiseSpectra/noise_SB%s_component_%s.fits'
OutputTemplate1 = 'outputs/%s/spectra_ascii/'
OutputTemplate2 = 'outputs/%s/spectra_plots/'
AsciiTemplate1 = OutputTemplate1 + 'SB%s_component_%s_opd.dat'
AsciiTemplate2 = OutputTemplate1 + 'SB%s_component_%s_flux.dat'
PlotTemplate = OutputTemplate2 + 'SB%s_component_%s_opd.png'
PlotTemplate2 = OutputTemplate2 + 'SB%s_component_%s_flux.png'

# Optional objectstore (Acacia) credentials - GWHG
#
# output data can optionally be tarred up and stored to the Acacia objectstore,
# one tarball per sbid:
certfile = "certs.json" # json file holding user/project keys for Acacia access
endpoint = "https://projects.pawsey.org.au" # URL address of Acacia
project = "ja3"  # project owning the storage quota space on Acacia
bucket = "flash" # bucket ("directory") to store to
storepath = 'pilot2_outputs' # where the tarball will be relative to the above 'bucket' on Acacia

#############################################################################################################
#############################################################################################################

# Set user options and defaults
parser = argparse.ArgumentParser()

# Deprecated - use '--sbids' instead - GWHG
parser.add_argument('--sbid', default='', type=str,
                    help='set input SBID')

# Allows for one or multiple sbids on command line - GWHG
parser.add_argument('--sbids', nargs='+', default='all', type=str,
                    help='set multiple input SBIDs')
options = parser.parse_args()


##func for making spectra plots
def make_plot(freq,chan,flux,opd,noiseflux,noiseopd,z,compno, compname, peak_flux):

    ##Reverse x-axis
    chan=chan[::-1]
    freq=freq[::-1]
    flux=flux[::-1]
    z=z[::-1]
    opd=opd[::-1]
    noiseflux=noiseflux[::-1]
    noiseopd=noiseopd[::-1]
    

    ##MAKE PLOT
    ##     A4 portrait plot
    fig = plt.figure(figsize=(8.3,11.7))
    fig_pad = 0.5
    nplots = 8
    
    #make nice fonts
    #rc('text', usetex=True)
    #rc('font',**{'family':'serif','serif':['serif'],'size':10})
    rc('font',**{'size':10}) # 'serif' not available on Nimbus- GWHG
            
    fig.subplots_adjust(wspace=0,hspace=fig_pad)
    plt.rc('xtick',labelsize='6')
    plt.rc('ytick',labelsize='6') 
        
    ##beam-forming ints:
    #use 5 MHz intervals
    ints=[i+0.5 for i in range(713,999,5)] ##calculate 5 MHz ints
    chunks=np.hstack([711.5,ints,999.5]) ##

    # Set dimension of figure
    for subplot in range(0,nplots):
    # Calculate range of data for subplot
        N = len(freq)/nplots
        ind_min = int(subplot*N)
        ind_max = int((subplot+1)*N-1)
        
        # Define data for plotting
        sub_x = freq[ind_min:ind_max]
        sub_x = [float(x) if np.isfinite(float(x)) else 0 for x in sub_x]
        sub_y = flux[ind_min:ind_max]
        sub_y = [x if np.isfinite(x) else 0 for x in sub_y]
        sub_y_opd = opd[ind_min:ind_max]
        sub_y_opd = [x if np.isfinite(x) else 0 for x in sub_y_opd]
        sub_n = noiseflux[ind_min:ind_max]
        sub_n = [x if np.isfinite(x) else 1. for x in sub_n]
        sub_n_opd = noiseopd[ind_min:ind_max]
        sub_n_opd = [x if np.isfinite(x) else 1. for x in sub_n_opd]
        sub_z = z[ind_min:ind_max]
        sub_z = [float(x) if np.isfinite(float(x)) else 0. for x in sub_z]
        
        # Initialize sub plot
        pos = subplot+1
        ax1 = fig.add_subplot(nplots,1,pos)
        # Set x and y labels for primary axis
        ax1.set_xlabel('')
        ax1.set_ylabel('')
        if float(subplot) == 0.5*nplots:
            ylabh = ax1.set_ylabel(r"Flux density (Jy/bm)", fontsize=10)
            yshift = 1.0+(0.5*fig_pad)
            ylabh.set_position((ylabh.get_position()[1],yshift))
        if float(subplot) == nplots-1.:
            xlabh = ax1.set_xlabel("Frequency (MHz)", fontsize=10)    
        if float(subplot) == 0:
            mktitle='Component %s - %s (%.3f Jy)'%(compno, compname, peak_flux)
            plt.suptitle(mktitle, x=0.5, y=0.95, horizontalalignment='center',fontsize=10)#,transform = ax1.transAxes)
            #plt.title('%s' %mktitle,fontsize=12)    

        # Set axis limits
        xmin = max(sub_x)
        xmax = min(sub_x)
        #print(xmin,xmax)
        #ymax= max(np.abs(flux))*1.2
        xxx = np.ma.masked_array(noiseflux, [not np.isfinite(x) for x in noiseflux])
        ymax = np.ma.median(xxx)*20.
        ymin = ymax*-1.
        yyy = np.ma.masked_array(noiseopd, [not np.isfinite(x) for x in noiseopd])
        ymaxopd = np.ma.median(yyy)*20.
        yminopd = ymaxopd*-1. 
        plt.xlim(xmin, xmax)
        if math.isnan(ymax):
            continue
        else:        
            plt.ylim(ymin, ymax)
    

        # Plot spectrum
        plt.plot(sub_x, sub_y, 'k-', linewidth=0.5, zorder=3)
        plt.axhline(color='r', linestyle='-', linewidth=0.5, zorder=2)
        plt.fill_between(sub_x, [-5.*x for x in sub_n], [5.*x for x in sub_n], facecolor=[0.8,0.8,0.8], edgecolor='none',zorder=1)
        ##mark bean forming intervals
        for i in chunks:    
            plt.plot([i,i],[ymin,ymax], color='b', linestyle='-', linewidth=0.3, zorder=2)    
        #add additional axes labels (redshift)
        label_inc = 0.01
        label_min = label_inc*np.floor(min(sub_z)/label_inc)
        label_max = label_inc*np.ceil(max(sub_z)/label_inc)
        labels = np.arange(label_min,label_max,label_inc)
        positions = [1420.405752/(1+label) for label in labels]
        x2label = r"$z_\mathrm{HI}$"
        labels = ['%.2f' % (label) for label in labels]
        ax1.get_xaxis().tick_bottom()
        ax2 = plt.gcf().add_axes(ax1.get_position(), sharey=ax1, frameon=False) 
        ax2.xaxis.tick_top()
        ax2.set_xticks(positions)
        ax2.set_xticklabels(labels)
        ax2.set_xlim(xmin, xmax)
        # Add x-axis labels
        if subplot == 0:
            ax1.text(0.5,1.3,x2label,horizontalalignment='center',fontsize=10,transform=ax1.transAxes)        
        # Set minor ticks
        ax1.minorticks_on()
        #ax3.minorticks_on()
        # Set tick lengths
        ax1.tick_params(bottom=True,left=True,top=False,right=False,length=6,width=1,which='major',direction='in')
        ax1.tick_params(bottom=True,left=True,top=False,right=False,length=3,width=1,which='minor',direction='in')
        ax2.tick_params(bottom=False,left=False,top=True,right=False,length=6,width=1,which='major',direction='in')
        ax2.tick_params(bottom=False,left=False,top=False,right=False,length=6,width=1,which='minor',direction='in')

    plt.savefig(PlotTemplate2%(sbid,sbid,compno),dpi=300)
    plt.close()

    ##MAKE PLOT
    ##     A4 portrait plot
    fig = plt.figure(figsize=(8.3,11.7))
    fig_pad = 0.5
    nplots = 8
    
    #make nice fonts
    #rc('text', usetex=True)
    #rc('font',**{'family':'serif','serif':['serif'],'size':10})
    rc('font',**{'size':10}) # 'serif' not available on Nimbus- GWHG
            
    fig.subplots_adjust(wspace=0,hspace=fig_pad)
    plt.rc('xtick',labelsize='6')
    plt.rc('ytick',labelsize='6') 
        
    ##beam-forming ints:
    #use 5 MHz intervals
    ints=[i+0.5 for i in range(713,999,5)] ##calculate 5 MHz ints
    chunks=np.hstack([711.5,ints,999.5]) ##

    # Set dimension of figure
    for subplot in range(0,nplots):
    # Calculate range of data for subplot
        N = len(freq)/nplots
        ind_min = int(subplot*N)
        ind_max = int((subplot+1)*N-1)
        
        # Define data for plotting
        sub_x = freq[ind_min:ind_max]
        sub_x = [float(x) if np.isfinite(float(x)) else 0 for x in sub_x]
        sub_y = flux[ind_min:ind_max]
        sub_y = [x if np.isfinite(x) else 0 for x in sub_y]
        sub_y_opd = opd[ind_min:ind_max]
        sub_y_opd = [x if np.isfinite(x) else 0 for x in sub_y_opd]
        sub_n = noiseflux[ind_min:ind_max]
        sub_n = [x if np.isfinite(x) else 1. for x in sub_n]
        sub_n_opd = noiseopd[ind_min:ind_max]
        sub_n_opd = [x if np.isfinite(x) else 1. for x in sub_n_opd]
        sub_z = z[ind_min:ind_max]
        sub_z = [float(x) if np.isfinite(float(x)) else 0. for x in sub_z]
        
        # Initialize sub plot
        pos = subplot+1
        ax1 = fig.add_subplot(nplots,1,pos)
        # Set x and y labels for primary axis
        ax1.set_xlabel('')
        ax1.set_ylabel('')
        if float(subplot) == 0.5*nplots:
            ylabh = ax1.set_ylabel(r"$\Delta{S}/S_\mathrm{c}$", fontsize=10)
            yshift = 1.0+(0.5*fig_pad)
            ylabh.set_position((ylabh.get_position()[1],yshift))
        if float(subplot) == nplots-1.:
            xlabh = ax1.set_xlabel("Frequency (MHz)", fontsize=10)    
        if float(subplot) == 0:
            mktitle='Component %s - %s (%.3f Jy)'%(compno, compname, peak_flux)
            plt.suptitle(mktitle, x=0.5, y=0.95, horizontalalignment='center',fontsize=10)#,transform = ax1.transAxes)
            #plt.title('%s' %mktitle,fontsize=12)    

        # Set axis limits
        xmin = max(sub_x)
        xmax = min(sub_x)
        #print(xmin,xmax)
        #ymax= max(np.abs(flux))*1.2
        xxx = np.ma.masked_array(noiseflux, [not np.isfinite(x) for x in noiseflux])
        ymax = np.ma.median(xxx)*20.
        ymin = ymax*-1.
        yyy = np.ma.masked_array(noiseopd, [not np.isfinite(x) for x in noiseopd])
        ymaxopd = np.ma.median(yyy)*20.
        yminopd = ymaxopd*-1. 
        plt.xlim(xmin, xmax)
        if math.isnan(ymaxopd):
            continue
        else:        
            plt.ylim(yminopd, ymaxopd)



        # Plot spectrum
        plt.plot(sub_x, sub_y_opd, 'k-', linewidth=0.5, zorder=3)
        plt.axhline(color='r', linestyle='-', linewidth=0.5, zorder=2)
        plt.fill_between(sub_x, [-5.*x for x in sub_n_opd], [5.*x for x in sub_n_opd], facecolor=[0.8,0.8,0.8], edgecolor='none',zorder=1)
        ##mark bean forming intervals
        #for i in chunks:    
        #    plt.plot([i,i],[yminopd,ymaxopd], color='b', linestyle='-', linewidth=0.3, zorder=2)    
        ##add additional axes labels (redshift)
        label_inc = 0.01
        label_min = label_inc*np.floor(min(sub_z)/label_inc)
        label_max = label_inc*np.ceil(max(sub_z)/label_inc)
        labels = np.arange(label_min,label_max,label_inc)
        positions = [1420.405752/(1+label) for label in labels]
        x2label = r"$z_\mathrm{HI}$"
        labels = ['%.2f' % (label) for label in labels]
        ax1.get_xaxis().tick_bottom()
        ax2 = plt.gcf().add_axes(ax1.get_position(), sharey=ax1, frameon=False) 
        ax2.xaxis.tick_top()
        ax2.set_xticks(positions)
        ax2.set_xticklabels(labels)
        ax2.set_xlim(xmin, xmax)
        # Add x-axis labels
        if subplot == 0:
            ax1.text(0.5,1.3,x2label,horizontalalignment='center',fontsize=10,transform=ax1.transAxes)
            
        # Set minor ticks
        ax1.minorticks_on()
        #ax3.minorticks_on()
        # Set tick lengths
        ax1.tick_params(bottom=True,left=True,top=False,right=False,length=6,width=1,which='major',direction='in')
        ax1.tick_params(bottom=True,left=True,top=False,right=False,length=3,width=1,which='minor',direction='in')
        ax2.tick_params(bottom=False,left=False,top=True,right=False,length=6,width=1,which='major',direction='in')
        ax2.tick_params(bottom=False,left=False,top=False,right=False,length=6,width=1,which='minor',direction='in')

    plt.savefig(PlotTemplate%(sbid,sbid,compno),dpi=300)
    plt.close()

    return

##############################################################################################################
##############################################################################################################

## writing out ascii files for FLASHfinder (add opd + noise in one file)
def write_ascii(sbid,compid,compno,chan,freq,flux,z,noiseflux,opd,noiseopd):
    data_all = Table([chan,freq,z,flux,noiseflux,opd,noiseopd], names=['chan','freq(MHz)','redshift','flux(Jy)','noise(Jy)','opd','opdnoise'])
    data_flux = Table([freq,flux,noiseflux], names=['freq(MHz)','flux(Jy)','noise(Jy)'])
    data_opd = Table([freq,opd,noiseopd], names=['freq(MHz)','opd','opdnoise'])
    #ascii.write(data_all, '%s/spectra_plots/ascii_format/spectrum_contsub_SB%s_component_%s.txt'%(sbid,sbid,compno), include_names=['chan','freq(MHz)','redshift','flux(Jy)','noise(Jy)','opd','opdnoise'], format='commented_header', comment='#', delimiter=' ',overwrite=True)
    ascii.write(data_flux, AsciiTemplate2%(sbid,sbid,compno), include_names=['freq(MHz)','flux(Jy)','noise(Jy)'], format='commented_header', comment='#', delimiter=' ',overwrite=True)
    
    ascii.write(data_opd, AsciiTemplate1%(sbid,sbid,compno), include_names=['freq(MHz)','opd','opdnoise'], format='commented_header', comment='#', delimiter=' ',overwrite=True)
    return

##############################################################################################################
##############################################################################################################

def calc_specindex(I_0,alpha,beta,v0):
    S_v=[]
    v_all=[]
    for v in np.arange(711.5,1000.5):
        #np.log10(I)=np.log10(I_0)+alpha*log(v/v0)+beta*log(v/v0)**2
        #Intensity=np.log10(I_0)+alpha*np.log10(v/v0)+beta*np.log10(v/v0)**2
        #S=10**(Intensity)
        I=I_0*(v/v0)**(alpha+beta*np.log10(v/v0))
        S_v.append(I)
        v_all.append(v)
    return S_v

##############################################################################################################
##############################################################################################################

def tardirectory(path,name):
    ''' Create tarball of directories and files '''
    count = 0
    with tarfile.open(name, "w:gz") as thandle:
        for root, dirs, files in os.walk(path):
            for f in files:
                thandle.add(os.path.join(root,f))
                count += 1
    return count
##############################################################################################################
##############################################################################################################

def sendTar2Objstore(sbid,localpath,storepath,certfile,endpoint,project,bucket):
    ''' Store a tarball on the Acacia objectstore '''
    # The file we want to upload is fully defined in the local filesystem by:
    #       localpath + TARNAME%(sbid)
    # The object it will become on the objectstore is:
    #       project + '/' + bucket + '/' + storepath + '/' + TARNAME%(sbid)
    #
    # The 'storepath' complication is added because you can't have buckets within buckets,
    # but you often want to mimic that construct. So 'storepath' is just a string made to look
    # like a subdirectory path, eg "myPretendDirectory/myPretendSubdirectory"

    localname = TARNAME%(sbid)
    objname = storepath+'/'+localname
    (access_id,secret_id,quota) = get_access_keys(certfile,endpoint,project)
    obj = S3.OsS3FitsObject(bucket,objname,access_id,secret_id,endpoint)
    obj.uploadLargeFile(localpath,localname,progress=False)

##############################################################################################################
##############################################################################################################

def processComponent(sbid,filename,compid,cat_dict):
    #compno=filename.split('_')[-1].strip('.fits') 
    # GWHG - the above will not work for all filenames as strip() also removes chars multiple times, 
    # eg '15f.fits' will become '15', not '15f'
    # So do it like this:
    compno=os.path.splitext(filename.split('_')[-1])[0]
    print(f'    Processing {sbid} component {compno}, compid {compid}')

    try:
        spechdu = fits.open(filename) # - GWHG
    except:
        print("Can't find spectrum for %s" %compno)
    f0=spechdu[0].header['CRVAL4']
    df=spechdu[0].header['CDELT4']
    askapspec = spechdu[0].data  

    peak_flux=cat_dict[compno][3]
    compname=str(cat_dict[compno][0]).strip("b'")
    ra=cat_dict[compno][1]
    dec=cat_dict[compno][2]
    alpha_src=cat_dict[compno][4]
    curv_src=cat_dict[compno][5]

    chan=[]
    freq=[]
    flux=[]
    z=[]
    opd_approx=[]

    for i in np.arange(len(askapspec[:])):
        nu=(i*df+f0)/1e6
        dataflux=askapspec[i][0][0][0]
        dataopd=dataflux/(flux_pk)  ##just flux ratio - i.e. not in per cent
        freq.append(nu)
        chan.append(i)
        flux.append(dataflux)
        z.append(hi_rest/nu-1.0)
        opd_approx.append(dataopd)
    #find corresponding contcube spectra
    ##
    ##
    #### CONTCUBES NOT DOWNLOADED and EXTRACTED YET, BUT I'LL LEAVE THIS HERE SO WE CAN EASILY ADD IT LATER. EKM 11/4/22
    ## NEED TO CHECK PATH
    ##        
    #read in contcube spectra to calculate optical depth
    contcube_path=ContCubeTemplate%(sbid,sbid,compno) # - GWHG
    contflux_freq = []
    opd = []

    if os.path.exists(contcube_path):
        contcube=ascii.read(contcube_path,comment='#')

        contcube.rename_column('col1', 'chan')
        contcube.rename_column('col2', 'pixels')
        contcube.rename_column('col3', 'freq(MHz)')
        contcube.rename_column('col4', 'vel(km/s)')
        contcube.rename_column('col5', 'flux(Jy)')
        for i in contcube['flux(Jy)']:
            contflux_freq+=[i]*54     ##multiply each entry by 54 to get same number of channels, surely not the best way to do this!
        for i in np.arange(0,len(flux)):
            opd.append(flux[i]/contflux_freq[i])

    else:
        ##for sbids without contcubes (13298/15873)
        ##Calculate spectral index based on continuum catalogue:
        curv_src=0.0 ##didn't fit curvature in pilot-1 processing. Default set to -99.        
        if alpha_src=='-99.0':
            alpha_src==-0.7
        flux_cont=calc_specindex(float(peak_flux),float(alpha_src),curv_src,float(nu_0))
        for i in flux_cont:
            contflux_freq+=[i]*54     ##multiply each entry by 54 to get same number of channels, surely not the best way to do this!
        for i in np.arange(0,len(flux)):
            opd.append(flux[i]/contflux_freq[i])
    #find corresponding noise spectra 
    try:
        noisehdu = fits.open(NoiseTemplate%(sbid,sbid,compno))
        f0=noisehdu[0].header['CRVAL4']
        df=noisehdu[0].header['CDELT4']
        noisespec = noisehdu[0].data
    
        noiseflux=[]
        noiseopd=[]
    
        for i in np.arange(len(noisespec[:])):
            nu=(i*df+f0)/1e6
            datanoise=noisespec[i][0][0][0]
            dataopdnoise_approx=datanoise/(peak_flux)
            dataopdnoise=datanoise/contflux_freq[i]
            noiseflux.append(datanoise)
            noiseopd.append(dataopdnoise)
                
    except:
        print("No noise spectra for %s, find closest bright component (>50mJy)"%compno)
        #find closest match to noise_cat
        c = SkyCoord(ra=ra*u.degree, dec=dec*u.degree)
        catalog = SkyCoord(ra=noise_cat['ra']*u.degree, dec=noise_cat['dec']*u.degree)
        idx, d2d, d3d = c.match_to_catalog_sky(catalog)
        print(noise_cat[idx][0],d2d.to(u.arcmin),"away")
        noise_compno=noise_cat[idx][0]
        noisepath = NoiseTemplate%(sbid,sbid,noise_compno)
        if not os.path.exists(noisepath):
            print('noise spectra missing for some reason, find next closest source')
            noise_cat.remove_row(int(idx))
            catalog = SkyCoord(ra=noise_cat['ra']*u.degree, dec=noise_cat['dec']*u.degree)
            idx, d2d, d3d = c.match_to_catalog_sky(catalog)
            print(noise_cat[idx][0],d2d.to(u.arcmin),"away")
            noise_compno=noise_cat[idx][0]
            noisehdu = fits.open(NoiseTemplate%(sbid,sbid,noise_compno))
        else:
            print(noise_cat[idx][0],d2d.to(u.arcmin),"away")
            noise_compno=noise_cat[idx][0]
            noisehdu = fits.open(NoiseTemplate%(sbid,sbid,noise_compno))
            f0=noisehdu[0].header['CRVAL4']
            df=noisehdu[0].header['CDELT4']
            noisespec = noisehdu[0].data
    
            noiseflux=[]
            noiseopd=[]
    
            for i in np.arange(len(noisespec[:])):
                nu=(i*df+f0)/1e6
                datanoise=noisespec[i][0][0][0]
                dataopdnoise_approx=datanoise/(peak_flux)
                dataopdnoise=datanoise/contflux_freq[i]
                noiseflux.append(datanoise)
                noiseopd.append(dataopdnoise)
    
    ##Make outputs for FLASHfinder. Overwrites previous files everytime it is rerun.
    write_ascii(sbid,compid,compno,chan,freq,flux,z,noiseflux,opd,noiseopd)
    
    ##only plot bright sources because it takes too long. Can use this as a way to skip over the plotting step. 
    #if peak_flux>0.5:
    ##skip over sources already done
    plotfile=PlotTemplate%(sbid,sbid,compno)
    if not os.path.exists(plotfile) and PLOT:
        make_plot(freq,chan,flux,opd,noiseflux,noiseopd,z,compno, compname, peak_flux)        

#################################################################################################################
###################################################### Start main program #######################################

numfiles = 0
numcomponents = 0
sbid_list = []
starttime = time()
print(f'Started with sbids: {options.sbids}')
# Default override
if options.sbids=='all':
    sbid_lst=glob.glob(GlobTemplate) # - GWHG
    sbid_list = [sbid.split("/")[-1] for sbid in sbid_lst] # - GWHG
else:
    sbid_list=options.sbids


robjs = []
for sbid in sbid_list:
    print(f'SB: {sbid}')
    #create output directory for plots and ascii files - GWHG
    Path(OutputTemplate1%sbid).mkdir(parents=True,exist_ok=True)
    Path(OutputTemplate2%sbid).mkdir(parents=True,exist_ok=True)

    cat_dict={}

    ##Initialise table of bright sources for noise measurements
    noise_cat=Table(names=('id','ra','dec'),dtype=('S4', 'f8', 'f8'))

    ##Finding flux_pk to calc rough opd:
    catalogue=glob.glob(CatalogueTemplate % sbid) # GWHG
    table = votable.parse_single_table(catalogue[0])
    cat = table.array
    for line in cat:
        compid=line['component_id'] #SB13375_component_2228a
        compname=line['component_name'] #J023056-254131
        flux_int=line['flux_int'] #in mJy
        flux_pk=line['flux_peak'] #in mJy
        ra=line['ra_deg_cont']
        dec=line['dec_deg_cont']
        compno = str(compid).split('_')[-1].strip("'")    
        alpha=line['spectral_index']
        curv=line['spectral_curvature']
        nu_0=line['freq']
        cat_dict[compno]=compname,ra,dec,float(flux_pk)/1000.,alpha,curv ##convert to Jy for opd calc.
        ##Make catalogue of bright sources to use for noise measurements when noise_spec not available
        if float(flux_pk)>50.:
            noise_cat.add_row((compno, ra, dec))

    ## Process each component file in source_list
    source_list=glob.glob(SpecHduTemplate%sbid)
    numcomponents += len(source_list)

    # Spawn off each source for processing in parallel (upt to number of cores) - GWHG
    with ProcessPoolExecutor(NUMCORES) as exe:
        _ = [exe.submit(processComponent,sbid,filename,compid,cat_dict) for filename in source_list]


#################################################################################################################
################ Optional tarring and storing to Acacia of per SBID results  - GWHG #############################

    if ARCHIVE:
        print('Tarring results')
        numfiles += tardirectory(TARPATH%(sbid),TARNAME%(sbid))

        # Store on objectstore
        print('Sending to objectstore')
        localpath = os.getcwd() # where the tarball is on local drive - GWHG
        sendTar2Objstore(sbid,localpath,storepath,certfile,endpoint,project,bucket)
        print(f'tarball stored to Acacia for SB{sbid}')

print(f'Job took {time()-starttime} sec for {len(sbid_list)} SBs, num components = {numcomponents}, num output files = {numfiles}')   # 1640s for SB34571 
