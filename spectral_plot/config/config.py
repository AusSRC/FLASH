#####################################################################################
#
#   Configuration items for the spectral plotting program
#
#   GWH German, CSIRO, Nov 2022
#
#   This module is called by "plot_spectrals.py", which expects it to exist 
#   in the working directory
#
#####################################################################################
import os
import sys

##define constants:
hi_rest=1420.40575177
c=2.99792458e5

PLOT = True # Generate the plots - GWHG
ASCII = True # Generate the ascii files for the linefinder - GWHG
ARCHIVE = True # tar and push results to Acacia - GWHG

# DATA PATH templates - absolute
GlobTemplate = '/data/sourceSpectra/3*'
CatalogueTemplate = '/data/catalogues/selavy-image.i*.SB%s.cont.*taylor.0.restored*.components.xml'
SpecHduTemplate = '/data/sourceSpectra/%s/SourceSpectra/spec_*.fits'
ContCubeTemplate = '/data/contcubes/%s/spectra/spectrum_contcube_SB%s_component_%s.txt'
NoiseTemplate = '/data/noise/%s/NoiseSpectra/noise_SB%s_component_%s.fits'
OutputTemplate1 = '/data/outputs/%s/spectra_ascii/'
OutputTemplate2 = '/data/outputs/%s/spectra_plots/'
AsciiTemplate1 = OutputTemplate1 + 'SB%s_component_%s_opd.dat'
AsciiTemplate2 = OutputTemplate1 + 'SB%s_component_%s_flux.dat'
PlotTemplate = OutputTemplate2 + 'SB%s_component_%s_opd.png'
PlotTemplate2 = OutputTemplate2 + 'SB%s_component_%s_flux.png'

# Variables for optional tarring of output results
TARPATH = '/data/outputs/%s' # 'root' directory for tarring operation - GWHG
TARNAME = 'SB%s_output_plots_and_ascii.tar.gz'   # Template for tarball name - GWHG

# Variables for optional storage to Acacia objectstore
localtarpath = os.getcwd() # where the tarball is on local drive - GWHG
endpoint = "https://projects.pawsey.org.au"
project = "ja3"
bucket = "flash"
certfile = "certs.json"
storepath = 'pilot2_outputs' # where the tarball will be relative to the bucket - GWHG


