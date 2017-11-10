#!/usr/bin/env python

##################################
# Create displacements for pwmat #
##################################

import sys
import os

try:
    import numpy as np
except ImportError:
    print("\033[93m\n ##?| numpy module may be not available ##\n\033[0m")

try:
    from phonopy import Phonopy, PhonopyGruneisen, PhonopyQHA, __version__
    from phonopy.cui.settings import PhonopyConfParser
    from phonopy.cui.show_symmetry import check_symmetry
    from phonopy.structure.cells import print_cell, determinant
    from phonopy.structure.atoms import atom_data, symbol_map
    from phonopy.interface.phonopy_yaml import PhonopyYaml
    phonopy_version = __version__
except ImportError:
    print("\033[93m\n ##?| phonopy package may be not available ##\n\033[0m")

try:
    import phmat.file_IO as file_IO
    from phmat.interface import read_crystal_structure, get_default_physical_units, create_FORCE_SETS
    from phmat.cui.phonopy_argparse import get_parser
except ImportError:
    print("\033[93m\n ##?| interface to pwmat package may be not available ##\n\033[0m")

__author__  = "Paul Chern"
__email__   = "peng.chen.iphy@gmail.com"
__licence__ = "GPL"
__date__    = "Nov. 2017"

def print_phononpy():
    print("                                                                          ")
    print(" -------------------------------------------------------------------------")
    print("                        Welcome to PWmat.                                 ")
    print("                        Phonopy Interface to PWmat                        ")
    print("                        Enjoy it and good luck                            ")
    print("                        Author : Peng Chen                                ")
    print("                        Email : peng.chen.iphy@gmail.com                  ")
    print(" =========================================================================")
    print("                                                                          ")
    print("""        _
  _ __ | |__   ___  _ __   ___   _ __  _   _
 | '_ \| '_ \ / _ \| '_ \ / _ \ | '_ \| | | |
 | |_) | | | | (_) | | | | (_) || |_) | |_| |
 | .__/|_| |_|\___/|_| |_|\___(_) .__/ \__, |
 |_|                            |_|    |___/  interface to PWmat""")

def print_version(version):
    try:
        import pkg_resources
        ver = pkg_resources.require("phonopy")[0].version.split('.')
        if len(ver) > 3:
            rev = ver[3]
            print(('%s-r%s' % (version, rev)).rjust(44))
        else:
            print(('%s' % version).rjust(44))
    except ImportError:
        print(('%s' % version).rjust(44))
    print('')

def print_end():
    print("""                 _
   ___ _ __   __| |
  / _ \ '_ \ / _` |
 |  __/ | | | (_| |
  \___|_| |_|\__,_|
""")

def print_error():
    print("""  ___ _ __ _ __ ___  _ __
 / _ \ '__| '__/ _ \| '__|
|  __/ |  | | | (_) | |
 \___|_|  |_|  \___/|_|
""")

def print_attention(attention_text):
    print("*" * 67)
    print(attention_text)
    print("*" * 67)
    print('')

def print_error_message(message):
    print('')
    print(message)

def file_exists(filename, log_level):
    if os.path.exists(filename):
        return True
    else:
        error_text = "%s not found." % filename
        print_error_message(error_text)
        if log_level > 0:
            print_error()
        sys.exit(1)

def finalize_phonopy(log_level,
                     phonopy_conf,
                     phonon,
                     interface_mode,
                     filename="phonopy.yaml"):
    if log_level > 0:
        phpy_yaml = PhonopyYaml(configuration=phonopy_conf.get_configures(),
                                calculator=interface_mode)
        phpy_yaml.set_phonon_info(phonon)
        with open(filename, 'w') as w:
            w.write(str(phpy_yaml))
        print_end()
    sys.exit(0)

def print_cells(phonon, unitcell_filename):
    print("Crsytal structure is read from \'%s\'." % unitcell_filename)
    supercell = phonon.get_supercell()
    unitcell = phonon.get_unitcell()
    primitive = phonon.get_primitive()
    p2p_map = primitive.get_primitive_to_primitive_map()
    mapping = np.array(
        [p2p_map[x] for x in primitive.get_supercell_to_primitive_map()],
        dtype='intc')
    s_indep_atoms = phonon.get_symmetry().get_independent_atoms()
    p_indep_atoms = mapping[s_indep_atoms]
    if unitcell.get_number_of_atoms() == primitive.get_number_of_atoms():
        print("-" * 32 + " unit cell " + "-" * 33)
        print_cell(primitive, stars=p_indep_atoms)
    else:
        u2s_map = supercell.get_unitcell_to_supercell_map()
        print("-" * 30 + " primitive cell " + "-" * 30)
        print_cell(primitive, stars=p_indep_atoms)
        print("-" * 32 + " unit cell " +  "-" * 33) # 32 + 11 + 33 = 76
        u2u_map = supercell.get_unitcell_to_unitcell_map()
        u_indep_atoms = [u2u_map[x] for x in s_indep_atoms]
        print_cell(unitcell, mapping=mapping[u2s_map], stars=u_indep_atoms)
    print("-" * 32 + " super cell " + "-" * 32)
    print_cell(supercell, mapping=mapping, stars=s_indep_atoms)
    print("-" * 76)

def print_settings(settings):
    run_mode = settings.get_run_mode()
    if run_mode == 'band':
        print("Band structure mode")
    if run_mode == 'mesh':
        print("Mesh sampling mode")
    if run_mode == 'band_mesh':
        print("Band structure and mesh sampling mode")
    if run_mode == 'anime':
        print("Animation mode")
    if run_mode == 'modulation':
        print("Modulation mode")
    if run_mode == 'irreps':
        print("Ir-representation mode")
    if run_mode == 'qpoints':
        if settings.get_write_dynamical_matrices():
            print("QPOINTS mode (dynamical matrices written out)")
        else:
            print("QPOINTS mode")
    if (run_mode == 'band' or
        run_mode == 'mesh' or
        run_mode == 'qpoints') and settings.get_is_group_velocity():
        gv_delta_q = settings.get_group_velocity_delta_q()
        if gv_delta_q is not None:
            print("  With group velocity calculation (dq=%3.1e)" % gv_delta_q)
        else:
            print('')
    if run_mode == 'displacements':
        print("Creating displacements")
        if not settings.get_is_plusminus_displacement() == 'auto':
            if settings.get_is_plusminus_displacement():
                print("  Plus Minus displacement: full plus minus directions")
            else:
                print("  Plus Minus displacement: only one direction")
        if not settings.get_is_diagonal_displacement():
            print("  Diagonal displacement: off")

    print("Settings:")
    if settings.get_is_nac():
        print("  Non-analytical term correction: on")
    if settings.get_fc_spg_symmetry():
        print("  Enforce space group symmetry to force constants: on")
    if settings.get_fc_symmetry_iteration() > 0:
        print("  Force constants symmetrization: %d times" %
              settings.get_fc_symmetry_iteration())
    if settings.get_lapack_solver():
        print("  Use Lapack solver via Lapacke: on")
    if run_mode == 'mesh' or run_mode == 'band_mesh':
        print("  Sampling mesh: %s" % np.array(settings.get_mesh()[0]))
        if settings.get_is_thermal_properties():
            cutoff_freq = settings.get_cutoff_frequency()
            if cutoff_freq is None:
                pass
            elif cutoff_freq < 0:
                print("  - Thermal properties are calculatd with "
                      "absolute phonon frequnecy.")
            else:
                print("  - Phonon frequencies > %f are used to calculate "
                      "thermal properties." % cutoff_freq)
    if (np.diag(np.diag(settings.get_supercell_matrix())) \
            - settings.get_supercell_matrix()).any():
        print("  Supercell matrix:")
        for v in settings.get_supercell_matrix():
            print("    %s" % v)
    else:
        print("  Supercell: %s" % np.diag(settings.get_supercell_matrix()))
    if settings.get_primitive_matrix() is not None:
        print("  Primitive axis:")
        for v in settings.get_primitive_matrix():
            print("    %s" % v)

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

#
# Phonopy interface mode
#
if options.wien2k_mode:
    interface_mode = 'wien2k'
    from phonopy.interface.wien2k import write_supercells_with_displacements
elif options.abinit_mode:
    interface_mode = 'abinit'
    from phonopy.interface.abinit import write_supercells_with_displacements
elif options.pwscf_mode:
    interface_mode = 'pwscf'
    from phonopy.interface.pwscf import write_supercells_with_displacements
elif options.elk_mode:
    interface_mode = 'elk'
    from phonopy.interface.elk import write_supercells_with_displacements
elif options.siesta_mode:
    interface_mode = 'siesta'
    from phonopy.interface.siesta import write_supercells_with_displacements
elif options.crystal_mode:
    interface_mode = 'crystal'
    from phonopy.interface.crystal import write_supercells_with_displacements
elif options.pwmat_mode:
    interface_mode = 'pwmat'
    from phmat.interface.pwmat import write_supercells_with_displacements
else:
    if options.vasp_mode:
        interface_mode = 'vasp'
    else:
        interface_mode = None
    from phonopy.interface.vasp import write_supercells_with_displacements
    from phonopy.interface.vasp import create_FORCE_CONSTANTS

physical_units = get_default_physical_units(interface_mode)

if options.is_graph_save:
    import matplotlib
    matplotlib.use('Agg')

################
# Phonopy logo #
################

if log_level > 0:
    print_phononpy()
    print_version(phonopy_version)

##########################
# Integrated helper tools #
###########################

# Create FORCE_SETS (-f or --force_sets)
if options.force_sets_mode or options.force_sets_zero_mode:
    file_exists('disp.yaml', log_level)
    for filename in args:
        file_exists(filename, log_level)
    error_num = create_FORCE_SETS(
        interface_mode,
        args,
        options.symprec,
        is_wien2k_p1=options.is_wien2k_p1,
        force_sets_zero_mode=options.force_sets_zero_mode,
        log_level=log_level)
    if log_level > 0:
        print_end()
    sys.exit(error_num)

# Create FORCE_CONSTANTS (--fc or --force_constants)
if options.force_constants_mode:
    if len(args) > 0:
        file_exists(args[0], log_level)
        error_num = create_FORCE_CONSTANTS(args[0],
                                           options.is_hdf5,
                                           log_level)
    else:
        print_error_message("Please specify vasprun.xml.")
        error_num = 1

    if log_level > 0:
        print_end()
    sys.exit(error_num)

#########################
# Read phonopy settings #
#########################
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
    interface_mode=interface_mode,
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

##########################
# Phonopy initialization #
##########################
run_mode = settings.get_run_mode()

if settings.get_supercell_matrix() is None:
    print_error_message("Supercell matrix (DIM or --dim) is not found.")
    if log_level > 0:
        print_end()
    sys.exit(1)

# Prepare phonopy object
if run_mode == 'displacements':
    supercell_dimension = [x for x in options.supercell_dimension.split()]
    phonon = Phonopy(unitcell,
                     settings.get_supercell_matrix(),
                     symprec=options.symprec,
                     is_symmetry=settings.get_is_symmetry(),
                     log_level=log_level)
else: # Read FORCE_SETS, FORCE_CONSTANTS, or force_constants.hdf5
    num_atom = unitcell.get_number_of_atoms()
    num_satom = determinant(settings.get_supercell_matrix()) * num_atom
    if settings.get_is_force_constants() == 'read':
        if settings.get_is_hdf5():
            try:
                import h5py
            except ImportError:
                print_error_message("You need to install python-h5py.")
                if log_level > 0:
                    print_end()
                sys.exit(1)

            if file_exists("force_constants.hdf5", log_level):
                fc = file_IO.read_force_constants_hdf5("force_constants.hdf5")
                fc_filename = "force_constants.hdf5"

        elif file_exists("FORCE_CONSTANTS", log_level):
            fc = file_IO.parse_FORCE_CONSTANTS(filename="FORCE_CONSTANTS")
            fc_filename = "FORCE_CONSTANTS"

        if log_level > 0:
            print("Force constants are read from %s." % fc_filename)

        if fc.shape[0] != num_satom:
            error_text = ("Number of atoms in supercell is not consistent with "
                          "the matrix shape of\nforce constants read from ")
            if settings.get_is_hdf5():
                error_text += "force_constants.hdf5.\n"
            else:
                error_text += "FORCE_CONSTANTS.\n"
            error_text += ("Please carefully check DIM, FORCE_CONSTANTS, "
                           "and %s.") % unitcell_filename
            print_error_message(error_text)
            if log_level > 0:
                print_end()
            sys.exit(1)

    elif file_exists("FORCE_SETS", log_level):
        force_sets = file_IO.parse_FORCE_SETS()
        if force_sets['natom'] != num_satom:
            error_text = "Number of atoms in supercell is not consistent with "
            error_text += "the data in FORCE_SETS.\n"
            error_text += ("Please carefully check DIM, FORCE_SETS,"
                           " and %s") % unitcell_filename
            print_error_message(error_text)
            if log_level > 0:
                print_end()
            sys.exit(1)

    # Overwrite frequency unit conversion factor
    if settings.get_frequency_conversion_factor() is not None:
        physical_units['factor'] = settings.get_frequency_conversion_factor()

    phonon = Phonopy(unitcell,
                     settings.get_supercell_matrix(),
                     primitive_matrix=settings.get_primitive_matrix(),
                     factor=physical_units['factor'],
                     dynamical_matrix_decimals=settings.get_dm_decimals(),
                     force_constants_decimals=settings.get_fc_decimals(),
                     symprec=options.symprec,
                     is_symmetry=settings.get_is_symmetry(),
                     use_lapack_solver=settings.get_lapack_solver(),
                     log_level=log_level)

supercell = phonon.get_supercell()
primitive = phonon.get_primitive()

# Set atomic masses of primitive cell
if settings.get_masses() is not None:
    phonon.set_masses(settings.get_masses())

# Show logs
if log_level > 0:
    print("Python version %d.%d.%d" % sys.version_info[:3])
    import phonopy.structure.spglib as spglib
    print("Spglib version %d.%d.%d" % spglib.get_version())
    if interface_mode:
        print("Calculator interface: %s" % interface_mode)
    print_settings(settings)
    if magmoms is None:
        print("Spacegroup: %s" %
              phonon.get_symmetry().get_international_table())

# Print cells
if log_level > 1:
    print_cells(phonon, unitcell_filename)

#################################
# Create displacements and exit #
#################################
if run_mode == 'displacements':
    if settings.get_displacement_distance() is None:
        if (interface_mode == 'wien2k' or
            interface_mode == 'abinit' or
            interface_mode == 'elk' or
            interface_mode == 'pwscf' or
            interface_mode == 'siesta'):
            displacement_distance = 0.02
        elif interface_mode == 'crystal':
            displacement_distance = 0.01
        elif interface_mode == 'pwmat':
            displacement_distance = 0.01
        else: # default or vasp
            displacement_distance = 0.01
    else:
        displacement_distance = settings.get_displacement_distance()

    phonon.generate_displacements(
        distance=displacement_distance,
        is_plusminus=settings.get_is_plusminus_displacement(),
        is_diagonal=settings.get_is_diagonal_displacement(),
        is_trigonal=settings.get_is_trigonal_displacement())
    displacements = phonon.get_displacements()
    directions = phonon.get_displacement_directions()
    file_IO.write_disp_yaml(displacements,
                            supercell,
                            directions=directions)

    # Write supercells with displacements
    cells_with_disps = phonon.get_supercells_with_displacements()

    if interface_mode == 'wien2k':
        npts, r0s, rmts = optional_structure_file_information[1:4]
        write_supercells_with_displacements(
            supercell,
            cells_with_disps,
            npts,
            r0s,
            rmts,
            settings.get_supercell_matrix(),
            filename=unitcell_filename)
    elif interface_mode == 'abinit':
        write_supercells_with_displacements(supercell, cells_with_disps)
    elif (interface_mode == 'pwscf' or
          interface_mode == 'elk' or
          interface_mode == 'siesta'):
        write_supercells_with_displacements(
            supercell,
            cells_with_disps,
            optional_structure_file_information[1])
    elif interface_mode == 'crystal':
        conv_numbers = optional_structure_file_information[1]
        write_supercells_with_displacements(supercell,
                                            cells_with_disps,
                                            conv_numbers,
                                            settings.get_supercell_matrix(),
                                            template_file="TEMPLATE")
    elif interface_mode == 'pwmat':
        write_supercells_with_displacements(supercell, cells_with_disps, supercell_dimension = 'x'.join(supercell_dimension))
    else: # default or vasp
        write_supercells_with_displacements(supercell, cells_with_disps)

    if log_level > 0:
        print('')
        print("disp.yaml and supercells have been created.")

    finalize_phonopy(log_level,
                     phonopy_conf,
                     phonon,
                     interface_mode,
                     filename="phonon/phonopy_disp.yaml")

########################################
# Preparations for phonon calculations #
########################################
if settings.get_is_force_constants() == 'read':
    phonon.set_force_constants(fc)
elif os.path.exists("FORCE_SETS"):
    phonon.set_displacement_dataset(force_sets)
    if log_level > 0:
        print("Computing force constants...")

    if (settings.get_is_force_constants() == "write" or
        settings.get_fc_symmetry_iteration() > 0 or
        settings.get_fc_spg_symmetry()):
        # Need to calculate full force constant tensors
        phonon.produce_force_constants(
            computation_algorithm=settings.get_fc_computation_algorithm())
    else: # Only force constants between atoms in primitive cell and in supercell
        phonon.produce_force_constants(
            calculate_full_force_constants=False,
            computation_algorithm=settings.get_fc_computation_algorithm())

# Non-analytical term correction (LO-TO splitting)
if settings.get_is_nac():
    if file_exists("BORN", log_level):
        nac_params = file_IO.get_born_parameters(
            open("BORN"),
            primitive,
            phonon.get_primitive_symmetry())
        if not nac_params:
            error_text = "BORN file could not be read correctly."
            print_error_message(error_text)
            if log_level > 0:
                print_end()
            sys.exit(1)
        if nac_params['factor'] == None:
            nac_params['factor'] = physical_units['nac_factor']
        phonon.set_nac_params(nac_params=nac_params)

        if log_level > 1:
            print("-" * 27 + " Dielectric constant " + "-" * 28)
            for v in nac_params['dielectric']:
                print("         %12.7f %12.7f %12.7f" % tuple(v))
            print("-" * 26 + " Born effective charges " + "-" * 26)
            symbols = primitive.get_chemical_symbols()
            for i, (z, s) in enumerate(zip(nac_params['born'], symbols)):
                for j, v in enumerate(z):
                    if j == 0:
                        text = "%5d %-2s" % (i + 1, s)
                    else:
                        text = "        "
                    print("%s %12.7f %12.7f %12.7f" % ((text,) + tuple(v)))
            print("-" * 76)

# Impose cutoff radius on force constants
cutoff_radius = settings.get_cutoff_radius()
if cutoff_radius:
    phonon.set_force_constants_zero_with_radius(cutoff_radius)

# Enforce space group symmetry to force constants
if settings.get_fc_spg_symmetry():
    if log_level > 0:
        print('')
        print("Force constants are symmetrized by space group operations.")
        print("This may take some time...")
    phonon.symmetrize_force_constants_by_space_group()
    file_IO.write_FORCE_CONSTANTS(phonon.get_force_constants(),
                                  filename='FORCE_CONSTANTS_SPG')
    if log_level > 0:
        print("Symmetrized force constants are written into "
              "FORCE_CONSTANTS_SPG.")

# Imporse translational invariance and index permulation symmetry to
# force constants
if settings.get_fc_symmetry_iteration() > 0:
    phonon.symmetrize_force_constants(settings.get_fc_symmetry_iteration())

# Write FORCE_CONSTANTS
if settings.get_is_force_constants() == "write":
    if settings.get_is_hdf5():
        file_IO.write_force_constants_to_hdf5(phonon.get_force_constants())
        if log_level > 0:
            print("Force constants are written into force_constants.hdf5.")
    else:
        file_IO.write_FORCE_CONSTANTS(phonon.get_force_constants())
        if log_level > 0:
            print("Force constants are written into FORCE_CONSTANTS.")

# Show the rotational invariance condition (just show!)
if settings.get_is_rotational_invariance():
    phonon.get_rotational_condition_of_fc()

# Atomic species without mass case
symbols_with_no_mass = []
if primitive.get_masses() is None:
    for s in primitive.get_chemical_symbols():
        if (atom_data[symbol_map[s]][3] is None and
            s not in symbols_with_no_mass):
            symbols_with_no_mass.append(s)
            print_error_message(
                "Atomic mass of \'%s\' is not implemented in phonopy." % s)
            print_error_message("MASS tag can be used to set atomic masses.")

if len(symbols_with_no_mass) > 0:
    if log_level > 0:
        print_end()
    sys.exit(1)

# Group velocity
if settings.get_is_group_velocity():
    phonon.set_group_velocity(q_length=settings.get_group_velocity_delta_q())

#######################
# Phonon calculations #
#######################

# QPOINTS mode
if run_mode == 'qpoints':
    if settings.get_qpoints():
        q_points = settings.get_qpoints()
        if log_level > 0:
            print("Q-points that will be calculated at:")
            for q in q_points:
                print("    %s" % q)
    else:
        q_points = file_IO.parse_QPOINTS()
        if log_level > 0:
            print("Frequencies at q-points given by QPOINTS:")
    phonon.set_qpoints_phonon(
        q_points,
        nac_q_direction=settings.get_nac_q_direction(),
        is_eigenvectors=settings.get_is_eigenvectors(),
        write_dynamical_matrices=settings.get_write_dynamical_matrices())

    if settings.get_is_hdf5():
        phonon.write_hdf5_qpoints_phonon()
    else:
        phonon.write_yaml_qpoints_phonon()

# Band structure and mesh sampling
elif run_mode == 'band' or run_mode == 'mesh' or run_mode == 'band_mesh':
    if run_mode == 'band' or run_mode == 'band_mesh':
        bands = settings.get_bands()
        if log_level > 0:
            print("Reciprocal space paths in reduced coordinates:")
            for band in bands:
                print("[%5.2f %5.2f %5.2f] --> [%5.2f %5.2f %5.2f]" %
                      (tuple(band[0]) + tuple(band[-1])))

        phonon.set_band_structure(
            bands,
            is_eigenvectors=settings.get_is_eigenvectors(),
            is_band_connection=settings.get_is_band_connection())
        if interface_mode is None:
            comment = None
        else:
            comment = {'calculator': interface_mode}

        if settings.get_is_hdf5():
            phonon.write_hdf5_band_structure(labels=settings.get_band_labels(),
                                             comment=comment)
        else:
            phonon.write_yaml_band_structure(labels=settings.get_band_labels(),
                                             comment=comment)

        if options.is_graph_plot and run_mode != 'band_mesh':
            plot = phonon.plot_band_structure(labels=settings.get_band_labels())
            if options.is_graph_save:
                plot.savefig('band.pdf')
            else:
                plot.show()

    if run_mode == 'mesh' or run_mode == 'band_mesh':
        (mesh,
         mesh_shift,
         t_symmetry,
         q_symmetry,
         is_gamma_center) =  settings.get_mesh()

        if (settings.get_is_thermal_displacements() or
            settings.get_is_thermal_displacement_matrices()):
            phonon.set_iter_mesh(mesh,
                                 mesh_shift,
                                 is_time_reversal=t_symmetry,
                                 is_mesh_symmetry=q_symmetry,
                                 is_eigenvectors=settings.get_is_eigenvectors(),
                                 is_gamma_center=settings.get_is_gamma_center())
        else:
            phonon.set_mesh(mesh,
                            mesh_shift,
                            is_time_reversal=t_symmetry,
                            is_mesh_symmetry=q_symmetry,
                            is_eigenvectors=settings.get_is_eigenvectors(),
                            is_gamma_center=settings.get_is_gamma_center(),
                            run_immediately=False)
            weights = phonon.get_mesh()[1]
            if log_level > 0:
                if q_symmetry:
                    print("Number of irreducible q-points on sampling mesh: "
                          "%d/%d" % (weights.shape[0], np.prod(mesh)))
                else:
                    print("Number of q-points on sampling mesh: %d" %
                          weights.shape[0])
                print("Calculating phonons on sampling mesh...")
    
            phonon.run_mesh()

            if settings.get_write_mesh():
                if settings.get_is_hdf5():
                    phonon.write_hdf5_mesh()
                else:
                    phonon.write_yaml_mesh()

        # Thermal property
        if settings.get_is_thermal_properties():

            if log_level > 0:
                if settings.get_is_projected_thermal_properties():
                    print("Calculating projected thermal properties...")
                else:
                    print("Calculating thermal properties...")
            tprop_range = settings.get_thermal_property_range()
            tstep = tprop_range['step']
            tmax = tprop_range['max']
            tmin = tprop_range['min']
            phonon.set_thermal_properties(
                tstep,
                tmax,
                tmin,
                is_projection=settings.get_is_projected_thermal_properties(),
                band_indices=settings.get_band_indices(),
                cutoff_frequency=settings.get_cutoff_frequency(),
                pretend_real=settings.get_pretend_real())
            phonon.write_yaml_thermal_properties()

            if log_level > 0:
                print("#%11s %15s%15s%15s%15s" % ('T [K]',
                                                  'F [kJ/mol]',
                                                  'S [J/K/mol]',
                                                  'C_v [J/K/mol]',
                                                  'E [kJ/mol]'))
                (temps,
                 fe,
                 entropy,
                 heat_capacity) = phonon.get_thermal_properties()
                for T, F, S, CV in zip(temps, fe, entropy, heat_capacity):
                    print(("%12.3f " + "%15.7f" * 4) %
                          (T, F, S, CV, F + T * S / 1000))

            if options.is_graph_plot:
                plot = phonon.plot_thermal_properties()
                if options.is_graph_save:
                    plot.savefig('thermal_properties.pdf')
                else:
                    plot.show()

        # Thermal displacements
        elif settings.get_is_thermal_displacements():
            p_direction = settings.get_projection_direction()
            if log_level > 0 and p_direction is not None:
                c_direction = np.dot(p_direction, primitive.get_cell())
                c_direction /= np.linalg.norm(c_direction)
                print("Projection direction: [%6.3f %6.3f %6.3f] "
                      "(fractional)" % tuple(p_direction))
                print("                      [%6.3f %6.3f %6.3f] "
                      "(Cartesian)" % tuple(c_direction))
            if log_level > 0:
                print("Calculating thermal displacements...")
            tprop_range = settings.get_thermal_property_range()
            tstep = tprop_range['step']
            tmax = tprop_range['max']
            tmin = tprop_range['min']
            phonon.set_thermal_displacements(
                tstep,
                tmax,
                tmin,
                direction=p_direction,
                cutoff_frequency=settings.get_cutoff_frequency())
            phonon.write_yaml_thermal_displacements()

            if options.is_graph_plot:
                plot = phonon.plot_thermal_displacements(options.is_legend)
                if options.is_graph_save:
                    plot.savefig('thermal_displacement.pdf')
                else:
                    plot.show()

        # Thermal displacement matrices
        elif settings.get_is_thermal_displacement_matrices():
            if log_level > 0:
                print("Calculating thermal displacement matrices...")
            tprop_range = settings.get_thermal_property_range()
            t_step = tprop_range['step']
            t_max = tprop_range['max']
            t_min = tprop_range['min']
            t_cif = settings.get_thermal_displacement_matrix_temperature()
            phonon.set_thermal_displacement_matrices(
                t_step=t_step,
                t_max=t_max,
                t_min=t_min,
                cutoff_frequency=settings.get_cutoff_frequency(),
                t_cif=t_cif)
            phonon.write_yaml_thermal_displacement_matrices()
            if t_cif is not None:
                phonon.write_thermal_displacement_matrix_to_cif(0)

        # Thermal distances
        elif settings.get_is_thermal_distances():
            if log_level > 0:
                print("Calculating thermal distances...")
            tprop_range = settings.get_thermal_property_range()
            tstep = tprop_range['step']
            tmax = tprop_range['max']
            tmin = tprop_range['min']
            phonon.set_thermal_distances(
                settings.get_thermal_atom_pairs(),
                tstep,
                tmax,
                tmin,
                cutoff_frequency=settings.get_cutoff_frequency())
            phonon.write_yaml_thermal_distances()

        # Partial DOS
        elif settings.get_pdos_indices() is not None:
            p_direction = settings.get_projection_direction()
            if (log_level > 0 and
                p_direction is not None and
                not settings.get_xyz_projection()):
                c_direction = np.dot(p_direction, primitive.get_cell())
                c_direction /= np.linalg.norm(c_direction)
                print("Projection direction: [%6.3f %6.3f %6.3f] "
                      "(fractional)" % tuple(p_direction))
                print("                      [%6.3f %6.3f %6.3f] "
                      "(Cartesian)" % tuple(c_direction))
            if log_level > 0:
                print("Calculating partial PDOS...")
            dos_range = settings.get_dos_range()
            phonon.set_partial_DOS(
                sigma=settings.get_sigma(),
                freq_min=dos_range['min'],
                freq_max=dos_range['max'],
                freq_pitch=dos_range['step'],
                tetrahedron_method=settings.get_is_tetrahedron_method(),
                direction=p_direction,
                xyz_projection=settings.get_xyz_projection())
            phonon.write_partial_DOS()

            if options.is_graph_plot:
                pdos_indices = settings.get_pdos_indices()
                if not pdos_indices:
                    num_atom = primitive.get_number_of_atoms()
                    pdos_indices = [np.arange(num_atom) * 3 + i
                                    for i in range(3)]

            if options.is_graph_plot and run_mode != 'band_mesh':
                plot = phonon.plot_partial_DOS(
                    pdos_indices=pdos_indices,
                    legend=([np.array(x) + 1 for x in pdos_indices]))
                if options.is_graph_save:
                    plot.savefig('partial_dos.pdf')
                else:
                    plot.show()

        # Total DOS
        elif (options.is_graph_plot or settings.get_is_dos_mode()):
            dos_range = settings.get_dos_range()

            phonon.set_total_DOS(
                sigma=settings.get_sigma(),
                freq_min=dos_range['min'],
                freq_max=dos_range['max'],
                freq_pitch=dos_range['step'],
                tetrahedron_method=settings.get_is_tetrahedron_method())

            if log_level > 0:
                print("Calculating DOS...")

            if settings.get_fits_Debye_model():
                phonon.set_Debye_frequency()
                if log_level > 0:
                    debye_freq = phonon.get_Debye_frequency()
                    print("Debye frequency: %10.5f" % debye_freq)
            phonon.write_total_DOS()

            if options.is_graph_plot and run_mode != 'band_mesh':
                plot = phonon.plot_total_DOS()
                if options.is_graph_save:
                    plot.savefig('total_dos.pdf')
                else:
                    plot.show()

        elif settings.get_is_moment():
            dos_range = settings.get_dos_range()
            freq_min = dos_range['min']
            freq_max = dos_range['max']
            if log_level > 0:
                text = "Calculating moment of phonon states distribution"
                if freq_min is None and freq_max is None:
                    text += "..."
                elif freq_min is None and freq_max is not None:
                    text += "\nbelow frequency %.3f..." % freq_max
                elif freq_min is not None and freq_max is None:
                    text += "\nabove frequency %.3f..." % freq_min
                elif freq_min is not None and freq_max is not None:
                    text += ("\nbetween frequencies %.3f and %.3f..." %
                             (freq_min, freq_max))
            print(text)
            print('')
            print("Order|   Total   |   Projected to atoms")
            if settings.get_moment_order() is not None:
                phonon.set_moment(order=settings.get_moment_order(),
                                  freq_min=freq_min,
                                  freq_max=freq_max,
                                  is_projection=False)
                total_moment = phonon.get_moment()
                phonon.set_moment(order=settings.get_moment_order(),
                                  freq_min=freq_min,
                                  freq_max=freq_max,
                                  is_projection=True)
                text = " %3d |%10.5f | " % (settings.get_moment_order(),
                                            total_moment)
                for m in phonon.get_moment():
                    text += "%10.5f " % m
                print(text)
            else:
                for i in range(3):
                    phonon.set_moment(order=i,
                                      freq_min=freq_min,
                                      freq_max=freq_max,
                                      is_projection=False)
                    total_moment = phonon.get_moment()
                    phonon.set_moment(order=i,
                                      freq_min=freq_min,
                                      freq_max=freq_max,
                                      is_projection=True)
                    text = " %3d |%10.5f | " % (i, total_moment)
                    for m in phonon.get_moment():
                        text += "%10.5f " % m
                    print(text)

    if (run_mode == 'band_mesh' and
        options.is_graph_plot and
        not settings.get_is_thermal_properties() and
        not settings.get_is_thermal_displacements() and
        not settings.get_is_thermal_displacement_matrices() and
        not settings.get_is_thermal_distances()):
        if settings.get_pdos_indices() is not None:
            plot = phonon.plot_band_structure_and_dos(
                pdos_indices=pdos_indices,
                labels=settings.get_band_labels())
        else:
            plot = phonon.plot_band_structure_and_dos(
                labels=settings.get_band_labels())
        if options.is_graph_save:
            plot.savefig('band_dos.pdf')
        else:
            plot.show()


# Animation
elif run_mode == 'anime':
    anime_type = settings.get_anime_type()
    if anime_type == "v_sim":
        q_point = settings.get_anime_qpoint()
        amplitude = settings.get_anime_amplitude()
        phonon.write_animation(q_point=q_point,
                               anime_type='v_sim',
                               amplitude=amplitude)
        if log_level > 0:
            print("Animation type: v_sim")
            print("q-point: [%6.3f %6.3f %6.3f]" % tuple(q_point))
    else:
        amplitude = settings.get_anime_amplitude()
        band_index = settings.get_anime_band_index()
        division = settings.get_anime_division()
        shift = settings.get_anime_shift()
        phonon.write_animation(anime_type=anime_type,
                               band_index=band_index,
                               amplitude=amplitude,
                               num_div=division,
                               shift=shift)

        if log_level > 0:
            print("Animation type: %s" % anime_type)
            print("amplitude: %f" % amplitude)
            if anime_type != "jmol":
                print("band index: %d" % band_index)
                print("Number of images: %d" % division)

# Modulation
elif run_mode == 'modulation':
    mod_setting = settings.get_modulation()
    phonon_modes = mod_setting['modulations']
    dimension = mod_setting['dimension']
    if 'delta_q' in mod_setting:
        delta_q = mod_setting['delta_q']
    else:
        delta_q = None
    derivative_order = mod_setting['order']

    phonon.set_modulations(dimension,
                           phonon_modes,
                           delta_q=delta_q,
                           derivative_order=derivative_order,
                           nac_q_direction=settings.get_nac_q_direction())
    phonon.write_modulations()
    phonon.write_yaml_modulations()

# Ir-representation
elif run_mode == 'irreps':
    if phonon.set_irreps(settings.get_irreps_q_point(),
                         is_little_cogroup=settings.get_is_little_cogroup(),
                         nac_q_direction=settings.get_nac_q_direction(),
                         degeneracy_tolerance=settings.get_irreps_tolerance()):
        show_irreps = settings.get_show_irreps()
        phonon.show_irreps(show_irreps)
        phonon.write_yaml_irreps(show_irreps)

else:
    print("-" * 76)
    print(" One of the following run modes may be specified for phonon "
          "calculations.")
    for mode in ['Mesh sampling (MP, --mesh)',
                 'Q-points (QPOINTS, --qpoints)',
                 'Band structure (BAND, --band)',
                 'Animation (ANIME, --anime)',
                 'Modulation (MODULATION, --modulation)',
                 'Characters of Irreps (IRREPS, --irreps)',
                 'Create displacements (-d)']:
        print(" - %s" % mode)
    print("-" * 76)

########################
# Phonopy finalization #
########################
finalize_phonopy(log_level, phonopy_conf, phonon, interface_mode)
