#!/usr/bin/env python

import rebound as rb
import reboundx as rbx
import addons
from argparse import ArgumentParser as ap
import configparser 
from astropy.time import Time
import datetime
import sys
from pathlib import Path
import numpy as np
import configparser

# parse commandline arguments
parser = ap(description='Reads command line arguments and builds configuration '\
			'file. With no other arguments provided, the configuration file for'\
			' <project_name> is used. If there is no configuration file found '	\
			'the program will build a new config file using the defaults as '	\
			'well as arguments if provided. -n will overwrite an existing file '\
			'without warning otherwise an existing configuration file is '		\
			'updated with the arguments provided' )
parser.add_argument('project_name', 
					type		= str,
					help		= 'Id of the project. (example: JSS-LR-12S for '\
								  '"Jupiter-Satellite-System-Long-Run-12-Satell'\
								  'ites). <project_name> is used in all project'\
								  ' related files.  Use whatever rocks your '	\
								  'boat! ')
parser.add_argument('-n', '--new', 											
					action		= 'store_const',
					const 		= True,
					help 		= 'writes a new ini file with the default '		\
								  'settings')
parser.add_argument('-r', '--rebuild', 											
					action		= 'store_const',
					const 		= True,
					help 		= 'force rebuild binary file. Use this one '	\
								  'after you have changed the config file by'	\
								  'editing outside this program')
parser.add_argument('-l', '--list_of_bodies', 
	                action		= 'store', 
	                type 		= str, 
	                nargs 		= '*', 
					help		= 'List of bodies for the model, separated by '	\
								  'blanks.')
parser.add_argument('-a', '--add_to_sun', 
	                action		= 'store', 
	                type 		= str, 
	                nargs 		= '*', 
					help		= 'List of bodies for the model, that are '		\
								  'added to the mass of the sun. Make sure to '	\
								  'use planets plus their satellite systems '	\
								  'i.e. "Earth barycenter"')
parser.add_argument('-u', '--units', 
	                action		= 'store', 
	                type 		= str, 
	                nargs 		= '*', 
					help		= 'List of units used in the model. Default is '\
								  'au, yr, and msun')			
parser.add_argument('-s', '--start_time', 
					action		= 'store', 
					type		= str, 
					help		= 'Date and time of ephemeris in the format '	\
								  '"YYYY-MM-DD HH:MM" the default is set '	\
								  'to 2000-01-01 12:00:00.0 "-s now" sets '		\
								  'start_time to now. If the date entered is '	\
								  'not valid or not in the right format the '	\
								  'date is set to the default value.')
parser.add_argument('-d', '--dt', 
					action		= 'store', 
					type		= str, 
					help		= 'Timestep for model. Depending on the '		\
								  'underlying integrator dt should be between '	\
								  '10%% and 25%% of the orbital period or about '	\
								  '0.6rad to 1.5rad. the default here is 1hour'	\
								  'whicgh needs to be set accordingly. ias15 '	\
								  'is using an adaptive timestep.')
parser.add_argument('-t', '--tmax', 
					action		= 'store', 
					type		= str, 
					help		= 'Max duration of model. Default is 10,000yr.')
parser.add_argument('-I', '--integrator', 
					action		= 'store', 
					type		= str, 
					help		= 'Set integrator used in rebound. Choices are '\
							      '"ias15" (def.), "whfast", "sei", "leapfrog",'\
							      '"hermes", "janus", "mercurius", "bs". See '	\
							      'rebound docs for details.')
parser.add_argument('-G', '--gravity', 
					action		= 'store', 
					type		= str, 
					help		= 'Set gavity module used in rebound. Choices '	\
							      'are "none", "basic" (def.), "compensated" '	\
							      '"tree". See rebound docs for details')
parser.add_argument('-C', '--collision', 
					action		='store',
					type		= str, 
					help		= 'Set collision module used in rebound. Choices '\
							      'are "none" (default), "direct", "tree", '	\
							      '"mercurius", "direct". See rebound docs for '\
							      'details')
parser.add_argument('-V', '--version', 
					action		= 'version', 
					version		= '%(prog)s 0.1')

clarg = parser.parse_args()

# Flags that require a rebuild

if not clarg.rebuild:
	CONFIGFILE = clarg.project_name+'.cfg'

	# check if configfile exists	
	if not Path(CONFIGFILE).exists():
		clarg.new = True
	
	# check if -n flag is set and write a complete new file now based on commandline
	# arguments and defaults for variables where no command line argument is set 
	# If -n is not set, update configfile with new commandline arguments
	if not (clarg.new):
		if (len(sys.argv)) > 2:
			addons.configWrite(CONFIGFILE, clarg, sys.argv, True)
			clarg.new = True	
	else:
		addons.configWrite(CONFIGFILE, clarg, sys.argv, False)
else:clarg.new = True
	
# Check if configuration file was changed
# Build a new binfile if configuration file was changed 
if clarg.new:addons.initReboundBinaryFile(clarg.project_name, sys.argv)


BINFILE 	= clarg.project_name+'-InitialConditions.bin'
CONFIGFILE 	= clarg.project_name+'.cfg'

# load simulation from binary file
sim 		= rb.Simulation.from_file(BINFILE)
   
# read in config file
cfin 		= configparser.ConfigParser()
cfin.read(CONFIGFILE)

sim_units 	= addons.configStr2List(cfin['Simulation']['units'])
sim.tmax  	= float(cfin['Simulation']['tmax'])

print("---------------------------------\nsim.G:\t\t\t{}\nsim.units:\t\t{}\nsim.tmax:\t\t{}".format(sim.G, sim_units, sim.tmax))
sim.status()

sim.G 		= 4*(np.pi*np.pi)		# correction for G to be 4Pi^2
sim_t 		= sim.t 				# save Julian Day (startdate) 
sim.t 		= 0						# set simulation time to 0
# sim.dt = sim.particles["Adrastea"].P*0.05
# sim.dt=1/365.25/24/2
sim_n_out 	= sim.tmax*365.25*24 	# Number of output steps in integration
times 		= np.linspace(0.,sim.tmax,sim_n_out)

# move simulation to common barycenter
sim.calculate_com(first=0, last=12)
sim.move_to_com()

# Add gravitational harmonics J2 and J4 using reboundx. The reference radius 
# is 71,492 km and the known zonal harmonics are from Folkner, W. M., et al. 
# (2017), Jupiter gravity field estimated from the first two Juno orbits, 
# Geophys. Res. Lett., 44, 4694–4700, doi:10.1002/2017GL073140.

ps 			= sim.particles
rebx 		= rbx.Extras(sim)
rebx.add("gravitational_harmonics")

ps["Jupiter"].params["J2"] = 0.014696514
ps["Jupiter"].params["J4"] = -0.000586632
ps["Jupiter"].params["R_eq"] = 71492/1.496e8

#for time in range (0, int(2*365.25*24),1):
#	sim.integrate(time*(sim.dt*2))

for i,time in enumerate(times):
	sim.integrate(time)
	print("{},{},{},{}".format(sim.t,sim.dt,sim_t+(sim.t*365.25),sim.particles["Io"].e))


