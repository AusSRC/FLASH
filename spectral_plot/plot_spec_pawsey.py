#!/usr/bin/env python

#################################################
#	
# 	Script to plot spectra output from casa
#	
#		Elizabeth Mahony, April 2021
# 	(with credit to James Allison as the plotting code mostly came from miriad_pipe.py)
#
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

# Set user options and defaults
parser = argparse.ArgumentParser()
parser.add_argument('--sbid', default='', type=str,
                    help='set input SBID')
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
	## 	A4 portrait plot
	fig = plt.figure(figsize=(8.3,11.7))
	fig_pad = 0.5
	nplots = 8
	
	#make nice fonts
	#rc('text', usetex=True)
	rc('font',**{'family':'serif','serif':['serif'],'size':10})
			
	fig.subplots_adjust(wspace=0,hspace=fig_pad)
	plt.rc('xtick',labelsize='6')
	plt.rc('ytick',labelsize='6') 
		
	##beam-forming ints:
	if sbid in ('11068','10849','10850','11051','11052','11053'):
		#use 5 MHz intervals
		ints=[i+0.5 for i in range(713,999,5)] ##calculate 5 MHz ints
		chunks=np.hstack([711.5,ints,999.5]) ##
	else:
		#use 9 MHz intervals
		ints=[i+0.5 for i in range(717,999,9)] ##calculate 9 MHz ints
		chunks=np.hstack([711.5,ints,999.5]) ##add in end points since BW doesn't divide evenly into 9mhz chunks

	# Set dimension of figure
	for subplot in range(0,nplots):
	# Calculate range of data for subplot
		N = len(freq)/nplots
		ind_min = int(subplot*N)
		ind_max = int((subplot+1)*N-1)
		
		# Define data for plotting
		#sub_x = freq[ind_min:ind_max]
		#sub_x = [0 if math.isnan(float(x)) else float(x) for x in sub_x]
		#sub_y = flux[ind_min:ind_max]
		#sub_y = [0 if math.isnan(x) else x for x in sub_y]
		#sub_y_opd = opd[ind_min:ind_max]
		#sub_y_opd = [0 if math.isnan(x) else x for x in sub_y_opd]
		#sub_n = noiseflux[ind_min:ind_max]
		#sub_n = [1. if math.isnan(x) else x for x in sub_n]
		#sub_n_opd = noiseopd[ind_min:ind_max]
		#sub_n_opd = [1. if math.isnan(x) else x for x in sub_n_opd]
		#sub_z = z[ind_min:ind_max]
		#sub_z = [0 if math.isnan(float(x)) else float(x) for x in sub_z]
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

	plt.savefig('%s/spectra_plots/SB%s_component_%s_flux.png'%(sbid,sbid,compno),dpi=300)
	plt.close()

	##MAKE PLOT
	## 	A4 portrait plot
	fig = plt.figure(figsize=(8.3,11.7))
	fig_pad = 0.5
	nplots = 8
	
	#make nice fonts
	#rc('text', usetex=True)
	rc('font',**{'family':'serif','serif':['serif'],'size':10})
			
	fig.subplots_adjust(wspace=0,hspace=fig_pad)
	plt.rc('xtick',labelsize='6')
	plt.rc('ytick',labelsize='6') 
		
	##beam-forming ints:
	if sbid in ('11068','10849','10850','11051','11052','11053'):
		#use 5 MHz intervals
		ints=[i+0.5 for i in range(713,999,5)] ##calculate 5 MHz ints
		chunks=np.hstack([711.5,ints,999.5]) ##
	else:
		#use 9 MHz intervals
		ints=[i+0.5 for i in range(717,999,9)] ##calculate 9 MHz ints
		chunks=np.hstack([711.5,ints,999.5]) ##add in end points since BW doesn't divide evenly into 9mhz chunks

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
		#	plt.plot([i,i],[yminopd,ymaxopd], color='b', linestyle='-', linewidth=0.3, zorder=2)	
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

	plt.savefig('%s/spectra_plots/SB%s_component_%s_opd.png'%(sbid,sbid,compno),dpi=300)
	plt.close()

	return


## writing out ascii files for FLASHfinder (add opd + noise in one file)
def write_ascii(sbid,compid,chan,freq,flux,z,noiseflux,opd,noiseopd):
	spectrum['redshift']=z
	spectrum['noise(Jy)']=noiseflux
	spectrum['opd']=opd
	spectrum['noiseopd']=noiseopd
	data_all = Table([chan,freq,z,flux,noiseflux,opd,noiseopd], names=['chan','freq(MHz)','redshift','flux(Jy)','noise(Jy)','opd','opdnoise'])
	data_flux = Table([freq,flux,noiseflux], names=['freq(MHz)','flux(Jy)','noise(Jy)'])
	data_opd = Table([freq,opd,noiseopd], names=['freq(MHz)','opd','opdnoise'])
	#ascii.write(data_all, '%s/spectra_plots/ascii_format/spectrum_contsub_SB%s_component_%s.txt'%(sbid,sbid,compno), include_names=['chan','freq(MHz)','redshift','flux(Jy)','noise(Jy)','opd','opdnoise'], format='commented_header', comment='#', delimiter=' ',overwrite=True)
	ascii.write(data_flux, '%s/spectra_ascii/SB%s_component_%s_flux.dat'%(sbid,sbid,compno), include_names=['freq(MHz)','flux(Jy)','noise(Jy)'], format='commented_header', comment='#', delimiter=' ',overwrite=True)
	ascii.write(data_opd, '%s/spectra_ascii/SB%s_component_%s_opd.dat'%(sbid,sbid,compno), include_names=['freq(MHz)','opd','opdnoise'], format='commented_header', comment='#', delimiter=' ',overwrite=True)
	return

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


########Start main program###########


##define constants:
hi_rest=1420.40575177
c=2.99792458e5

if options.sbid=='all':
	sbid_list=['13293','11068','13306','13294','13305','13284','13272','13270','13271','10849','11051','11052','13279','10850','11053','13291','13372','13281','13268','15212','13269','13278','15873','13290','13297','13296','13299','13298','13285','13283','13334','13335','13336','13273','15208','15209']
else:
	sbid_list=[options.sbid]	


for sbid in sbid_list:
	print(sbid)
	#create output directory for plots
	if not os.path.exists('%s/spectra_plots'%sbid):
		os.mkdir('%s/spectra_plots'%sbid)	
	if not os.path.exists('%s/spectra_ascii'%sbid):
		os.mkdir('%s/spectra_ascii'%sbid)	


	cat_dict={}

	##Initialise table of bright sources for noise measurements
	noise_cat=Table(names=('id','ra','dec'),dtype=('S4', 'f8', 'f8'))

	##Finding flux_pk to calc rough opd:
	catalogue=glob.glob('/group/askap/FLASH/casda/catalogues/selavy-image.i*.SB%s.cont.*taylor.0.restored*.components.xml'%(sbid))
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

	## for plotting all spectra:
	source_list=glob.glob('%s/spectra_contsub/spectrum_cont*.txt'%sbid)
	for filename in source_list:
		compno = filename.split('_')[-1].strip('.txt')

		spectrum=ascii.read(filename,comment='#')
	
		peak_flux=cat_dict[compno][3]
		compname=str(cat_dict[compno][0]).strip("b'")
		ra=cat_dict[compno][1]
		dec=cat_dict[compno][2]
		alpha_src=cat_dict[compno][4]
		curv_src=cat_dict[compno][5]
		#print(compname,ra,dec,peak_flux)
		chan=spectrum['chan']
		freq=spectrum['freq(MHz)']
		flux=spectrum['flux(Jy)']
		z=[hi_rest/float(nu)-1.0 for nu in freq]
		opd_approx=[i/peak_flux for i in flux]

		#find corresponding contcube spectra
		#read in contcube spectra to calculate optical depth
		contflux_freq=[]
		opd=[]
		contcube_path='/group/askap/FLASH/contcubes/%s/spectra/spectrum_contcube_SB%s_component_%s.txt'%(sbid,sbid,compno)
		if os.path.exists(contcube_path):
			contcube=ascii.read(contcube_path,comment='#')

			contcube.rename_column('col1', 'chan')
			contcube.rename_column('col2', 'pixels')
			contcube.rename_column('col3', 'freq(MHz)')
			contcube.rename_column('col4', 'vel(km/s)')
			contcube.rename_column('col5', 'flux(Jy)')
			for i in contcube['flux(Jy)']:
				contflux_freq+=[i]*54 	##multiply each entry by 54 to get same number of channels, surely not the best way to do this!
			for i in np.arange(0,len(flux.data)):
				opd.append(flux.data[i]/contflux_freq[i])
		else:
			##for sbids without contcubes (13298/15873)
			##Calculate spectral index based on continuum catalogue:
			curv_src=0.0 ##didn't fit curvature in pilot-1 processing. Default set to -99.		
			if alpha_src=='-99.0':
				alpha_src==-0.7
			flux_cont=calc_specindex(float(peak_flux),float(alpha_src),curv_src,float(nu_0))
			#v=np.arange(711.5, 1000.5, 1.0).tolist()
			for i in flux_cont:
				contflux_freq+=[i]*54 	##multiply each entry by 54 to get same number of channels, surely not the best way to do this!
			for i in np.arange(0,len(flux.data)):
				opd.append(flux.data[i]/contflux_freq[i])
				    
		#find corresponding noise spectra 
		try:
			noisehdu = fits.open('/group/askap/FLASH/casda/%s/NoiseSpectra/noise_SB%s_component_%s.fits'%(sbid,sbid,compno))
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
			noisepath = '/group/askap/FLASH/casda/%s/NoiseSpectra/noise_SB%s_component_%s.fits'%(sbid,sbid,noise_compno)
			if not os.path.exists(noisepath):
				print('noise spectra missing for some reason, find next closest source')
				noise_cat.remove_row(int(idx))
				catalog = SkyCoord(ra=noise_cat['ra']*u.degree, dec=noise_cat['dec']*u.degree)
				idx, d2d, d3d = c.match_to_catalog_sky(catalog)
				print(noise_cat[idx][0],d2d.to(u.arcmin),"away")
				noise_compno=noise_cat[idx][0]
				noisehdu = fits.open('/group/askap/FLASH/casda/%s/NoiseSpectra/noise_SB%s_component_%s.fits'%(sbid,sbid,noise_compno))
			else:
				print(noise_cat[idx][0],d2d.to(u.arcmin),"away")
				noise_compno=noise_cat[idx][0]
				noisehdu = fits.open('/group/askap/FLASH/casda/%s/NoiseSpectra/noise_SB%s_component_%s.fits'%(sbid,sbid,noise_compno))
#			noisehdu = fits.open('/group/askap/FLASH/casda/%s/NoiseSpectra/noise_SB%s_component_%s.fits'%(sbid,sbid,noise_compno))
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
				dataopdnoise_approx=datanoise/(peak_flux)
				noiseflux.append(datanoise)
				noiseopd.append(dataopdnoise)
		
		write_ascii(sbid,compid,chan,freq,flux,z,noiseflux,opd,noiseopd)
		##only plot bright sources because it takes too long
#		if peak_flux>0.045:
		##skip over sources already done
		plotfile='%s/spectra_plots/SB%s_component_%s_opd.png'%(sbid,sbid,compno)
		if not os.path.exists(plotfile):
			print("plotting %s"%compno)
			make_plot(freq,chan,flux,opd,noiseflux,noiseopd,z,compno, compname, peak_flux)		
