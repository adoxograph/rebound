#!/usr/bin/env python

import rebound as rb
import reboundx as rbx
import sys
import numpy as np

BINFILE = sys.argv[1]+'-InitialConditions.bin'

# load simulation from binary file
sim = rb.Simulation.from_file(BINFILE)

sim.integrator='whfast'
sim_t = sim.t
# sim.t=0
# sim.dt = sim.particles["Adrastea"].P*0.05
sim.dt=1/24/2
sim.status()

# Code begins here
# move simulation to common barycenter
sim.calculate_com(first=0, last=12)
sim.move_to_com()

times = np.linspace(sim_t,sim_t+(2*365.25),2*365.25*24)

# Add graritational harmonics J2 and J4 using reboundx. The reference radius 
# is 71,492 km and the known zonal harmonics are from Folkner, W. M., et al. 
# (2017), Jupiter gravity field estimated from the first two Juno orbits, 
# Geophys. Res. Lett., 44, 4694–4700, doi:10.1002/2017GL073140.

ps = sim.particles
rebx = rbx.Extras(sim)
rebx.add("gravitational_harmonics")

ps["Jupiter"].params["J2"] = 0.014696514
ps["Jupiter"].params["J4"] = -0.000586632
ps["Jupiter"].params["R_eq"] = 71492/1.796e8

for i,time in enumerate(times):
	#print(time)
	sim.integrate(time)
	print("{},{},{}".format(sim.t, sim.dt, sim.particles["Io"].e))