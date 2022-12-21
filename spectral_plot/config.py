#####################################################################################
#
#   Configuration items for the spectral plotting program
#
#   GWH German, CSIRO, Nov 2022
#
#   This module is called by "plot_spectrals.py", which expects it to exist 
#   in the working directory, or in a mounted /config directory (for containers).
#
#####################################################################################
import os
import sys

##define constants:
hi_rest=1420.40575177
c=2.99792458e5

PLOT = True # Generate the plots - GWHG
PEAKFLUX = 0.0 # Only generate the plots for components where the peak flux is over this value
ASCII = True # Generate the ascii files for the linefinder - GWHG
ARCHIVE = False # tar and push results to Acacia - GWHG
DEBUG = False
NUMCORES = 32 # Number of cores requested for multiprocessing - this will be limited to max available.

#################################### DATA PATH templates - absolute #################
# "/data" is the data directory set in run_slurm_spectral.sh. You can then 
# reflect any subdirectory structures here

GlobTemplate = '/data/sourceSpectra/4*' # only used if the sbid value from "run_slurm_spectrals.sh" is "all"

CatalogueTemplate = '/data/sourceSpectra/catalogues/selavy-image.i*.SB%s.cont.*taylor.0.restored*.components.xml' # subdirectory holding the image catalogues
SpecHduTemplate = '/data/sourceSpectra/%s/spec_*.fits' # the component files for the given sbid
ContCubeTemplate = '/data/contcubes/%s/spectrum_contcube_SB%s_component_%s.txt' # contcube spectra to calculate optical depth
NoiseTemplate = '/data/sourceSpectra/noise/%s/noise_SB%s_component_%s.fits' # the noise cubes
OutputTemplate1 = '/data/sourceSpectra/%s/spectra_ascii/' # where to create output ascii files
OutputTemplate2 = '/data/sourceSpectra/%s/spectra_plots/' # where to create output plot png files

## Leave these as they are unless you have good reason to change them
AsciiTemplate1 = OutputTemplate1 + 'SB%s_component_%s_opd.dat'
AsciiTemplate2 = OutputTemplate1 + 'SB%s_component_%s_flux.dat'
PlotTemplate = OutputTemplate2 + 'SB%s_component_%s_opd.png'
PlotTemplate2 = OutputTemplate2 + 'SB%s_component_%s_flux.png'

# Variables for optional tarring of output results
TARPATH = '/data/sourceSpectra/%s' # 'root' directory for tarring operation - GWHG
TARNAME = 'SB%s_output_plots_and_ascii.tar.gz'   # Template for tarball name - GWHG

# Variables for optional storage to Acacia objectstore
localtarpath = os.getcwd() # where the tarball is on local drive - GWHG
endpoint = "https://projects.pawsey.org.au"
project = "ja3"
bucket = "flash"
certfile = "certs.json" # holds the objectstore id strings for the project and/or user
storepath = 'pilot2_outputs' # where the tarball will be relative to the bucket - GWHG


