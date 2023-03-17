#!/usr/bin/env python

#################################
#    flash_finder_NOMPI.py      #

#                               #
#  James Richard Allison (2018) #
#
#  Modified Gordon German (2022)#
#  - removed MPI dependency     #
#  - added multiprocessing      #
#################################

# Import installed python modules
import os
import sys
import string
import numpy as np
import warnings
from astropy.io import ascii
from astropy.table import Table
from glob import glob
if 'PYMULTINEST' in os.environ:
    sys.path.append(os.environ['PYMULTINEST'])
import pymultinest

# Import habs nest python modules
from options import *
from data import *
from model import *
from conversions import *
from initialize import *
from fitting import *
from output import *
from time import time

from plotting import *
# Switch off warnings
warnings.simplefilter("ignore")

# Initialise required directories
initialize_directories(options)

# Multiprocessing -GWHG:
from concurrent.futures import ProcessPoolExecutor
PROCESS = True

starttime = time()


##############################################################################################################################
##############################################################################################################################


def checkOptionsOverride(options,filename="/config/linefinder.ini"):
    ''' Check if any of the command-line arguments are to be over-ridden'''

    with open(filename) as f:
        for line in f:
            # Ignore comments
            if line.startswith("#") or not line.strip():
                continue
            # spilt and strip whitespace
            attr,val = line.split(":")
            attr = attr.strip()
            val = val.strip()

            # process values - check if boolean, int, float or string
            if val == "True":
                setattr(options,attr,True)
            elif val == "False":
                setattr(options,attr,False)
            else:
                try:
                    val = int(val)
                except ValueError:
                    try:
                        val = float(val)
                    except ValueError:
                        pass
                setattr(options,attr,val)
    return options

##############################################################################################################################
##############################################################################################################################

def processSource(line,source_count,proc_num):
    ''' one process per source is run under a ProcessPoolExecutor '''

    

    # Initialize source object
    source = Source()

    # Allocate information on the source
    source.number = source_count
    source.info = line

    # Report source name 
    print(f"\nProcess {proc_num}: Working on Source {source.info['name']}\n")

    # Assign output root name
    options.out_root = '%s/%s' % (options.out_path,source.info['name'])

    # Generate spectral data
    source.spectrum.filename = '%s/%s.dat' % (options.data_path,source.info['name'])
    if os.path.exists(source.spectrum.filename):
        source.spectrum.generate_data(options)
    else:
        print(f"\nProcess {proc_num}: Spectrum for source {source.info['name']} does not exist. Ignoring it.\n")
        return
        
    # Initialize and generate model object
    model = Model()
    model.input.generate_model(options,source)
    initialize_resultsfile(options,model,os.getpid())

    # Calculate the null evidence
    empty = np.zeros(source.spectrum.ndata)
    chisq = calculate_chisquared(options,source.spectrum,empty)
    model.output.null.logZ = -0.5*chisq

    mnest_args = initialize_mnest(options,source,model)

    # Run pymultinest to fit for continuum only
    if 'continuum' in model.input.types:

        # Print message to screen
        print(f'\nProcess {proc_num}: Started MultiNest for continuum model\n')

        # Run pymultinest
        mnest_args['n_dims'] = model.input.cont_ndims
        mnest_args['n_params'] = model.input.cont_ndims
        mnest_args['n_clustering_params'] = 0
        mnest_args['outputfiles_basename'] = options.out_root + '_continuum_'
        mnest_args['multimodal'] = False
        pymultinest.run(**mnest_args)

        # Print message to screen
        print(f'\nProcess {proc_num}: Finished MultiNest for continuum model\n')

        # Obtain output
        model.output.cont = pymultinest.Analyzer(n_params=mnest_args['n_params'],outputfiles_basename=mnest_args['outputfiles_basename'])

        # Update null evidence to include continuum-only model evidence
        model.output.null.logZ += model.output.cont.get_stats()['global evidence']

    # Run habs nest to fit for spectral-lines

    # Print message to screen
    print(f'\nProcess {proc_num}: Started MultiNest for spectral line model\n')

    # Run pymultinest
    mnest_args['n_dims'] = model.input.all_ndims
    mnest_args['n_params'] = model.input.nparams
    mnest_args['n_clustering_params'] = 3
    mnest_args['outputfiles_basename'] = options.out_root + '_spectline_'
    mnest_args['multimodal'] = options.mmodal
    mnest_args['null_log_evidence'] = -1.e99 # options.detection_limit
    mnest_args['mode_tolerance'] = -1.e99 # options.detection_limit
    pymultinest.run(**mnest_args)

    # Print message to screen
    print(f'\nProcess {proc_num}: Finished MultiNest for spectral line model\n')

    # Obtain output
    pymultinest.Analyzer.get_separated_stats = get_separated_stats
    model.output.sline = pymultinest.Analyzer(n_params=mnest_args['n_params'],outputfiles_basename=mnest_args['outputfiles_basename'])
    if options.mmodal:
        model.output.sline.get_separated_stats()

    # Report the number of detections
    model.output.ndetections = 0
    for mode in model.output.sline.get_mode_stats()['modes']:
        mode_evidence = mode['local log-evidence']            
        if mode_evidence >= options.detection_limit:
            model.output.ndetections += 1
    if model.output.ndetections == 1:
        print(f"\nProcess {proc_num}, Source {source.info['name']}: 1 spectral line detected\n")
    else:
        print(f"\nProcess {proc_num}, Source {source.info['name']}: {model.output.ndetections} spectral lines detected\n")

    # Write results to file
    write_resultsfile(options,source,model,os.getpid())

    # Make grahpical output
    if options.plot_switch:
        print(f"Process {proc_num}, Source {source.info['name']}: Making graphical output\n")

        # Make plot of posterior probabilities for absorption parameters
        posterior_plot(options,source,model)

        # Make plot of best-fitting spectrum for each mode
        bestfit_spectrum(options,source,model)

    return

##############################################################################################################################
############################################ START MAIN PROGRAM ##############################################################
# Number of threads requested for data partitioning - GWHG
NUMTHREADS = options.numthreads if options.numthreads < (os.cpu_count()-1) else (os.cpu_count()-1)
    
print('\n\n******************************************************************************')
print('                                 FLASH FINDER')
print('')
print('Python program to use MultiNest for spectral-line detection and modelling')
print('')
print('Copyright 2018 James R. Allison. All rights reserved.')
print('')
print(f'Number threads for data partition: {NUMTHREADS}')
print('******************************************************************************\n')

# By default, the initialisation file is expected to be '/config/linefinder.ini' (for container
# reasons). However, this can be overridden on the command line with '--inifile <filepath>'
print(f'ini file = {options.inifile}')
if options.inifile:
    options = checkOptionsOverride(options,filename=options.inifile)
else:
    options = checkOptionsOverride(options)

# Read source information from file or list spectra in directory
source_list = Table()
if os.path.exists(options.sourcelog):
    source_list = ascii.read(options.sourcelog,format='commented_header',comment='#')
else:
    source_list['name'] = glob(options.data_path+'/*opd.dat')
    index = 0
    for index in np.arange(0,len(source_list['name'])):
        name = source_list['name'][index].split('/')[-1]
        source_list['name'][index] = name.split('.dat')[0]
        index += 1

# Check for required information
if 'name' not in source_list.colnames:
    print(f"\nPlease specify source names in {options.data_path+'sources.log'}\n")
    sys.exit(1)

print('\nInitializing output results file.\n')
source = Source()
model = Model()
model.input.generate_model(options,source)

if PROCESS:

    # Loop program over each source spectral data 
    print("looping over sources")
    with ProcessPoolExecutor(max_workers=NUMTHREADS) as exe:
        _ = [exe.submit(processSource,line,sourcenum,sourcenum) for sourcenum,line in enumerate(source_list)]

timed = time() - starttime
print(f"Linefinder took {timed:.2f} sec for {len(source_list)} components")
