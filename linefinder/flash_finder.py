#!/usr/bin/env python

#################################
#       flash_finder.py         #
#                               #
#  James Richard Allison (2018) #
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
else: # Force environment into python!!
    import shlex
    import subprocess

    command = shlex.split("bash -c 'source ~/set_local_env.sh && env'")
    proc = subprocess.Popen(command, stdout = subprocess.PIPE)
    for line in proc.stdout:
        (key, _, value) = line.decode().partition("=")
        os.environ[key] = value
    proc.communicate()
    print(f"Forced PYMULTINEST into environ: {os.environ['PYMULTINEST']}",flush=True)
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

# Switch off warnings
warnings.simplefilter("ignore")

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
# By default, the initialisation file is expected to be '/config/linefinder.ini' (for container
# reasons). However, this can be overridden on the command line with '--inifile <filepath>'
print(f'ini file = {options.inifile}')
if options.inifile:
    options = checkOptionsOverride(options,filename=options.inifile)
else:
    options = checkOptionsOverride(options)

# Initialise required directories
initialize_directories(options)

# Switch on mpi
mpi_size = 1
mpi_rank = 0
if options.mpi_switch:
    import mpi4py
    from mpi4py import MPI
    mpi_comm = MPI.COMM_WORLD
    mpi_size = mpi_comm.Get_size()
    mpi_rank = mpi_comm.Get_rank()

starttime = time()
# Determine if CPU should do the following
if (mpi_rank == 0) or (not options.init_MPI):
    
    print('\n\n******************************************************************************')
    print('                                 FLASH FINDER')
    print('')
    print('Python program to use MultiNest for spectral-line detection and modelling')
    print('')
    print('Copyright 2018 James R. Allison. All rights reserved.')
    print('******************************************************************************\n')

    # Read source information from file or list spectra in directory
    if (mpi_rank == 0):

        source_list = Table()
        if os.path.exists(options.data_path+'sources.log'):
            source_list = ascii.read(options.data_path+'sources.log',format='commented_header',comment='#')
        else:
            source_list['name'] = glob(options.data_path+'/*opd.dat')
            index = 0
            for index in np.arange(0,len(source_list['name'])):
                name = source_list['name'][index].split('/')[-1]
                source_list['name'][index] = name.split('.dat')[0]
                index += 1

        # Check for required information
        if 'name' not in source_list.colnames:
            print('\nCPU %d:Please specify source names in %s\n' % (mpi_rank,options.data_path+'sources.log'))
            sys.exit(1)

    # Distribute source list amongst processors
    if options.mpi_switch:

        if (mpi_rank == 0):
            list_chunks = [[] for _ in range(mpi_size)]
            for i, list_chunk in enumerate(source_list):
                list_chunks[i % mpi_size].append(list_chunk)
        else:
            list_chunks = None

    # Wait for all processors to reach this point
    if options.mpi_switch:
        mpi_comm.Barrier()

    if options.mpi_switch:
        source_list = mpi_comm.scatter(list_chunks,root=0)

    # Wait for all processors to reach this point
    if options.mpi_switch:
        mpi_comm.Barrier()

    # Initialize output results file
    if (mpi_rank == 0):
        print('\nCPU %d: Initializing output results file.\n'% (mpi_rank))
        source = Source()
        model = Model()
        model.input.generate_model(options,source)
        initialize_resultsfile(options,model)

    # Wait for all processors to reach this point
    if options.mpi_switch:
        mpi_comm.Barrier()

    # Loop program over each source spectral data 
    source_count = 0
    print("looping over sources")
    for line in source_list:
        # Increment source count
        source_count += 1

        # Initialize source object
        source = Source()

        # Allocate information on the source
        source.number = source_count
        source.info = line

        # Report source name 
        print('\nCPU %d: Working on Source %s.\n' % (mpi_rank,source.info['name']))

        # Assign output root name
        options.out_root = '%s/%s' % (options.out_path,source.info['name'])

        # Generate spectral data
        source.spectrum.filename = '%s/%s.dat' % (options.data_path,source.info['name'])
        if os.path.exists(source.spectrum.filename):
            source.spectrum.generate_data(options)
        else:
            print('\nCPU %d: Spectrum for source %s does not exist. Moving on.\n' % (mpi_rank,source.info['name']))
            continue
            
        # Initialize and generate model object
        model = Model()
        model.input.generate_model(options,source)

        # Calculate the null evidence
        empty = np.zeros(source.spectrum.ndata)
        chisq = calculate_chisquared(options,source.spectrum,empty)
        model.output.null.logZ = -0.5*chisq

        # Initialize MultiNest arguments
        mnest_args = initialize_mnest(options,source,model)

        # Run pymultinest to fit for continuum only
        if 'continuum' in model.input.types:

            # Print message to screen
            print('\nCPU %d: Started MultiNest for continuum model\n' % (mpi_rank))

            # Run pymultinest
            mnest_args['n_dims'] = model.input.cont_ndims
            mnest_args['n_params'] = model.input.cont_ndims
            mnest_args['n_clustering_params'] = 0
            mnest_args['outputfiles_basename'] = options.out_root + '_continuum_'
            mnest_args['multimodal'] = False
            pymultinest.run(**mnest_args)

            # Print message to screen
            print('\nCPU %d: Finished MultiNest for continuum model\n' % (mpi_rank))

            # Obtain output
            model.output.cont = pymultinest.Analyzer(n_params=mnest_args['n_params'],outputfiles_basename=mnest_args['outputfiles_basename'])

            # Update null evidence to include continuum-only model evidence
            model.output.null.logZ += model.output.cont.get_stats()['global evidence']

        # Run habs nest to fit for spectral-lines

        # Print message to screen
        print('\nCPU %d: Started MultiNest for spectral line model\n' % (mpi_rank))

        # Run pymultinest
        mnest_args['n_dims'] = model.input.all_ndims
        mnest_args['n_params'] = model.input.nparams
        mnest_args['n_clustering_params'] = 3
        mnest_args['outputfiles_basename'] = options.out_root + '_spectline_'
        mnest_args['multimodal'] = options.mmodal
        mnest_args['null_log_evidence'] = -1.e99 # options.detection_limit
        mnest_args['mode_tolerance'] = -1.e99 # options.detection_limit
        mnest_args['max_modes'] = 200 # sets max mem for modes - default is 100
        pymultinest.run(**mnest_args)

        # Print message to screen
        print('\nCPU %d: Finished MultiNest for spectral line model\n' % (mpi_rank))

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
            print('\nCPU %d, Source %s: 1 spectral line detected\n' % (mpi_rank,source.info['name']))
        else:
            print('\nCPU %d, Source %s: %d spectral lines detected\n' % (mpi_rank,source.info['name'],model.output.ndetections))

        # Write results to file
        write_resultsfile(options,source,model)

        # Make grahpical output
        if options.plot_switch:
            from plotting import *
            print('CPU %d, Source %s: Making graphical output\n' % (mpi_rank,source.info['name']))

            # Make plot of posterior probabilities for absorption parameters
            posterior_plot(options,source,model)

            # Make plot of best-fitting spectrum for each mode
            bestfit_spectrum(options,source,model)

timed = time() - starttime
print(f"Linefinder took {timed:.2f} sec")
