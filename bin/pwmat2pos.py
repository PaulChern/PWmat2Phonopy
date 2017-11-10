#!/usr/bin/env python

import sys
import os

try:
    import numpy as np
except ImportError:
    print("\033[93m\n ##?| numpy module may be not available ##\n\033[0m")

try:
    import pwmat2phonopy.file_IO as file_IO
    from pwmat2phonopy.interface.pwmat import write_poscar
    from pwmat2phonopy.interface import read_crystal_structure, get_default_physical_units, create_FORCE_SETS
    from pwmat2phonopy.cui.settings import PhonopyConfParser
    from pwmat2phonopy.cui.phonopy_argparse import get_parser
except ImportError:
    print("\033[93m\n ##?| interface to pwmat package may be not available ##\n\033[0m")

__author__  = "Paul Chern"
__email__   = "peng.chen.iphy@gmail.com"
__licence__ = "GPL"
__date__    = "Nov. 2017"


###########################
# Primitive option parser #
###########################

parser = get_parser()
(options, args) = parser.parse_args()
option_list = parser.option_list

# Set log level
log_level = 1
if options.verbose:
    log_level = 2
if options.quiet or options.is_check_symmetry:
    log_level = 0
if options.loglevel is not None:
    log_level = options.loglevel

#################
# parsing input #
#################
if len(args) > 0:
    if file_exists(args[0], log_level):
        phonopy_conf = PhonopyConfParser(filename=args[0],
                                         options=options,
                                         option_list=option_list)
        settings = phonopy_conf.get_settings()
else:
    phonopy_conf = PhonopyConfParser(options=options,
                                     option_list=option_list)
    settings = phonopy_conf.get_settings()

##################
# Read unit cell #
##################
unitcell, optional_structure_file_information = read_crystal_structure(
    filename=settings.get_cell_filename(),
    interface_mode='pwmat',
    chemical_symbols=settings.get_chemical_symbols(),
    yaml_mode=settings.get_yaml_mode())
unitcell_filename = optional_structure_file_information[0]

if unitcell is None:
    print_error_message("Crystal structure file of %s could not be found." %
                        unitcell_filename)
    if log_level > 0:
        print_error()
    sys.exit(1)

# Check unit cell
if np.linalg.det(unitcell.get_cell()) < 0.0:
    print_error_message("Lattice vectors have to follow the right-hand rule.")
    if log_level > 0:
        print_end()
    sys.exit(1)

# Set magnetic moments
magmoms = settings.get_magnetic_moments()
if magmoms is not None:
    if len(magmoms) == unitcell.get_number_of_atoms():
        unitcell.set_magnetic_moments(magmoms)
    else:
        error_text = "Invalid MAGMOM setting"
        print_error_message(error_text)
        if log_level > 0:
            print_end()
        sys.exit(1)

################################################
# Check crystal symmetry and exit (--symmetry) #
################################################
if options.is_check_symmetry:
    check_symmetry(unitcell,
                   primitive_axis=settings.get_primitive_matrix(),
                   symprec=options.symprec,
                   distance_to_A=physical_units['distance_to_A'],
                   phonopy_version=phonopy_version)
    if log_level > 0:
        print_end()
    sys.exit(0)

#############
# pwmat2pos #
#############

write_poscar(unitcell, filename=options.cell_filename)

