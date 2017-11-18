# Copyright (C) 2011 Atsushi Togo
# All rights reserved.
#
# This file is part of phonopy.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in
#   the documentation and/or other materials provided with the
#   distribution.
#
# * Neither the name of the phonopy project nor the names of its
#   contributors may be used to endorse or promote products derived
#   from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import sys
import os
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import io
import numpy as np
from phonopy.structure.atoms import PhonopyAtoms as Atoms
from phonopy.structure.atoms import symbol_map, atom_data
from phonopy.structure.cells import get_primitive, get_supercell
from phonopy.structure.symmetry import (Symmetry, get_site_symmetry,
                                        get_pointgroup_operations)
from phonopy.harmonic.force_constants import similarity_transformation
from phonopy.file_IO import (write_FORCE_SETS, write_force_constants_to_hdf5,
                             write_FORCE_CONSTANTS)

def parse_set_of_forces(num_atoms,
                        forces_filenames,
                        use_expat=True,
                        verbose=True):
    if verbose:
        sys.stdout.write("counter (file index): ")

    count = 0
    is_parsed = True
    force_sets = []
    force_files = forces_filenames

    for filename in force_files:
        with open(filename) as infile :
            lines = infile.readlines()

        force = []
        for i in range(1, num_atoms + 1):
            force.append([float(x) for x in lines[i].split()[1:4]])
        force = -1*np.array(force)

        force_sets.append(force)

        if verbose:
            sys.stdout.write("%d " % (count + 1))
        count += 1

        if not check_forces(force_sets[-1], num_atoms, filename):
            is_parsed = False

    if verbose:
        print('')

    if is_parsed:
        return force_sets
    else:
        return []

def check_forces(forces, num_atom, filename, verbose=True):
    if len(forces) != num_atom:
        if verbose:
            stars = '*' * len(filename)
            sys.stdout.write("\n")
            sys.stdout.write("***************%s***************\n" % stars)
            sys.stdout.write("***** Parsing \"%s\" failed. *****\n" % filename)
            sys.stdout.write("***************%s***************\n" % stars)
        return False
    else:
        return True

def get_drift_forces(forces, filename=None, verbose=True):
    drift_force = np.sum(forces, axis=0) / len(forces)

    if verbose:
        if filename is None:
            print("Drift force: %12.8f %12.8f %12.8f to be subtracted"
                  % tuple(drift_force))
        else:
            print("Drift force of \"%s\" to be subtracted" % filename)
            print("%12.8f %12.8f %12.8f" % tuple(drift_force))
        sys.stdout.flush()

    return drift_force

def create_FORCE_CONSTANTS(filename, is_hdf5, log_level):
    fc_and_atom_types = parse_force_constants(filename)

    if not fc_and_atom_types:
        print('')
        print("\'%s\' dones not contain necessary information." % filename)
        return 1

    force_constants, atom_types = fc_and_atom_types
    if is_hdf5:
        try:
            import h5py
        except ImportError:
            print('')
            print("You need to install python-h5py.")
            return 1

        write_force_constants_to_hdf5(force_constants)
        if log_level > 0:
            print("force_constants.hdf5 has been created from vasprun.xml.")
    else:
        write_FORCE_CONSTANTS(force_constants)
        if log_level > 0:
            print("FORCE_CONSTANTS has been created from vasprun.xml.")

    if log_level > 0:
        print("Atom types: %s" % (" ".join(atom_types)))
    return 0

def parse_force_constants(filename):
    """Return force constants and chemical elements

    Args:
        filename (str): Filename

    Returns:
        tuple: force constants and chemical elements

    """

    vasprun = Vasprun(io.open(filename, "rb"))
    return vasprun.read_force_constants()


#
# read PWmat atom.config
#
def read_pwmat(filename, symbols=None):
    with open(filename) as infile :
        lines = infile.readlines()
    return _get_atoms_from_atom_config(lines, symbols)

def read_pwmat_from_strings(strings, symbols=None):
    return _get_atoms_from_atom_config(StringIO(strings).readlines(), symbols)

def _get_atoms_from_atom_config(lines, symbols):
    num_atoms = int(lines[0].split()[0])
    num_lines = len(lines)

    cell = []
    for i in range(2, 5):
        cell.append([float(x) for x in lines[i].split()[:3]])
    cell = np.array(cell)

    line_at = 6

    positions = []
    for i in range(line_at, line_at + num_atoms):
        positions.append([float(x) for x in lines[i].split()[1:4]])

    atoms_z = []
    expand_symbols = []
    for i in range(line_at, line_at + num_atoms):
        zatom = int(lines[i].split()[0])
        atoms_z.append(zatom)
        expand_symbols.append(atom_data[zatom][1])

    atoms = Atoms(symbols=expand_symbols,
                  cell=cell,
                  scaled_positions=positions)

    return atoms

def _is_exist_symbols(symbols):
    for s in symbols:
        if not (s in symbol_map):
            return False
    return True

def _expand_symbols(num_atoms, symbols=None):
    expanded_symbols = []
    is_symbols = True
    if symbols is None:
        is_symbols = False
    else:
        if len(symbols) != len(num_atoms):
            is_symbols = False
        else:
            for s in symbols:
                if not s in symbol_map:
                    is_symbols = False
                    break

    if is_symbols:
        for s, num in zip(symbols, num_atoms):
            expanded_symbols += [s] * num
    else:
        for i, num in enumerate(num_atoms):
            expanded_symbols += [atom_data[i+1][1]] * num

    return expanded_symbols

#
# write vasp POSCAR
#
def write_pwmat(filename, atoms, direct=True):
    lines = get_pwmat_structure_lines(atoms, direct=direct)
    with open(filename, 'w') as w:
        w.write("\n".join(lines))

def write_unitcell(unitcell,
                   filename="vasp"):
    write_pwmat(filename+".pwmat", unitcell, direct=True)

def write_supercells_with_displacements(supercell,
                                        cells_with_displacements,
                                        pre_filename="atom.config",
                                        supercell_dimension="1x1x1",
                                        width=3):
    #os.mkdir('phonon/forces-residual')
    #write_pwmat('phonon/forces-residual/' + 'atom.config', supercell, direct=True)
    write_pwmat('phonon/' + 'atom_'+supercell_dimension+'.config', supercell, direct=True)
    for i, cell in enumerate(cells_with_displacements):
        if cell is not None:
            pwmat_dir = "{pre_filename}-{0:0{width}}".format(i + 1, pre_filename="forces", width=width)
            pwmat_struct = "{pre_filename}-{0:0{width}}".format(i + 1, pre_filename=pre_filename, width=width)
            os.mkdir('phonon/' + pwmat_dir)
            write_pwmat(os.path.join('phonon/' + pwmat_dir, pre_filename),
                       cell,
                       direct=True)

    _write_magnetic_moments(supercell)

def write_vasp(filename, atoms, direct=True):
    lines = get_vasp_structure_lines(atoms, direct=direct)
    with open(filename, 'w') as w:
        w.write("\n".join(lines))

def write_poscar(unitcell,
                 filename="pwmat"):
    write_vasp(filename+".vasp", unitcell, direct=True)

def _write_magnetic_moments(cell):
    magmoms = cell.get_magnetic_moments()
    if magmoms is not  None:
        w = open("MAGMOM", 'w')
        (num_atoms,
         symbols,
         scaled_positions,
         sort_list) = sort_positions_by_symbols(cell.get_chemical_symbols(),
                                                cell.get_scaled_positions())
        w.write(" MAGMOM = ")
        for i in sort_list:
            w.write("%f " % magmoms[i])
        w.write("\n")
        w.close()

def get_scaled_positions_lines(scaled_positions):
    return "\n".join(_get_scaled_positions_lines(scaled_positions))

def _get_scaled_positions_lines(scaled_positions, atoms_Z):
    lines = []
    for i, vec in enumerate(scaled_positions):
        line_str = str(atoms_Z[i]) + "    "
        for x in (vec - np.rint(vec)):
            if float('%20.16f' % x) < 0.0:
                line_str += "%20.16f" % (x + 1.0)
            else:
                line_str += "%20.16f" % (x)
        line_str += "    0  0  0"

        lines.append(line_str)

    return lines

def _get_vasp_scaled_positions_lines(scaled_positions):
    lines = []
    for i, vec in enumerate(scaled_positions):
        line_str=''
        for x in (vec - np.rint(vec)):
            if float('%20.16f' % x) < 0.0:
                line_str += "%20.16f" % (x + 1.0)
            else:
                line_str += "%20.16f" % (x)

        lines.append(line_str)

    return lines

def sort_positions_by_symbols(symbols, positions):
    reduced_symbols = _get_reduced_symbols(symbols)
    sorted_positions = []
    sort_list = []
    num_atoms = np.zeros(len(reduced_symbols), dtype=int)
    for i, rs in enumerate(reduced_symbols):
        for j, (s, p) in enumerate(zip(symbols, positions)):
            if rs == s:
                sorted_positions.append(p)
                sort_list.append(j)
                num_atoms[i] += 1
    return num_atoms, reduced_symbols, np.array(sorted_positions), sort_list

def get_vasp_structure_lines(atoms, direct=True, is_vasp5=False):
    atoms_Z = atoms.get_atomic_numbers()
    (num_atoms,
     symbols,
     scaled_positions,
     sort_list) = sort_positions_by_symbols(atoms.get_chemical_symbols(),
                                            atoms.get_scaled_positions())
    lines = []
    if is_vasp5:
        lines.append("generated by phonopy")
    else:
        lines.append(" ".join(["%s" % s for s in symbols]))
    lines.append("   1.0")
    for a in atoms.get_cell():
        lines.append("  %21.16f %21.16f %21.16f" % tuple(a))
    lines.append(" ".join(["%s" % s for s in symbols]))
    lines.append(" ".join(["%4d" % n for n in num_atoms]))
    lines.append("Direct")
    lines += _get_vasp_scaled_positions_lines(scaled_positions)

    # VASP compiled on some system, ending by \n is necessary to read POSCAR
    # properly.
    lines.append('')

    return lines

def get_pwmat_structure_lines(atoms, direct=True):
    (num_atoms,
     symbols,
     scaled_positions,
     sort_list) = sort_positions_by_symbols(atoms.get_chemical_symbols(),
                                            atoms.get_scaled_positions())
    atoms_Z = atoms.get_atomic_numbers()
    num_tot_atoms = len(atoms_Z)
    lines = []
    lines.append(str(num_tot_atoms))
    lines.append("Lattice vector")
    for a in atoms.get_cell():
        lines.append("  %21.16f %21.16f %21.16f" % tuple(a))
    lines.append("Position")
    lines += _get_scaled_positions_lines(scaled_positions, atoms_Z)
    lines.append('')

    return lines

def _get_reduced_symbols(symbols):
    reduced_symbols = []
    for s in symbols:
        if not (s in reduced_symbols):
            reduced_symbols.append(s)
    return reduced_symbols

#
# Non-analytical term
#
def get_born_vasprunxml(filename="vasprun.xml",
                        primitive_matrix=None,
                        supercell_matrix=None,
                        is_symmetry=True,
                        symmetrize_tensors=False,
                        symprec=1e-5):
    import io
    borns = []
    epsilon = []
    with io.open(filename, "rb") as f:
        vasprun = VasprunxmlExpat(f)
        if vasprun.parse():
            epsilon = vasprun.get_epsilon()
            borns = vasprun.get_born()
            lattice = vasprun.get_lattice()[-1]
            points = vasprun.get_points()[-1]
            symbols = vasprun.get_symbols()
            ucell = Atoms(symbols=symbols,
                          scaled_positions=points,
                          cell=lattice)
        else:
            return None

    return _get_borns(ucell,
                      borns,
                      epsilon,
                      primitive_matrix=primitive_matrix,
                      supercell_matrix=supercell_matrix,
                      is_symmetry=is_symmetry,
                      symmetrize_tensors=symmetrize_tensors,
                      symprec=symprec)

def get_born_OUTCAR(poscar_filename="POSCAR",
                    outcar_filename=None,
                    primitive_matrix=None,
                    supercell_matrix=None,
                    is_symmetry=True,
                    symmetrize_tensors=False,
                    symprec=1e-5):
    if outcar_filename is None:
        filename = "OUTCAR"
    else:
        filename = outcar_filename

    ucell = read_vasp(poscar_filename)
    borns, epsilon = _read_born_and_epsilon_from_OUTCAR(filename)
    if len(borns) == 0 or len(epsilon) == 0:
        return None
    else:
        return _get_borns(ucell,
                          borns,
                          epsilon,
                          primitive_matrix=primitive_matrix,
                          supercell_matrix=supercell_matrix,
                          is_symmetry=is_symmetry,
                          symmetrize_tensors=symmetrize_tensors,
                          symprec=symprec)

def symmetrize_borns_and_epsilon(borns,
                                 epsilon,
                                 ucell,
                                 symprec=1e-5,
                                 is_symmetry=True):
    lattice = ucell.get_cell()
    positions = ucell.get_scaled_positions()
    u_sym = Symmetry(ucell, is_symmetry=is_symmetry, symprec=symprec)
    rotations = u_sym.get_symmetry_operations()['rotations']
    translations = u_sym.get_symmetry_operations()['translations']
    ptg_ops = get_pointgroup_operations(rotations)
    epsilon_ = symmetrize_2nd_rank_tensor(epsilon, ptg_ops, lattice)

    for i, Z in enumerate(borns):
        site_sym = get_site_symmetry(i,
                                     lattice,
                                     positions,
                                     rotations,
                                     translations,
                                     symprec)
        Z = symmetrize_2nd_rank_tensor(Z, site_sym, lattice)

    borns_ = np.zeros_like(borns)
    for i in range(len(borns)):
        count = 0
        for r, t in zip(rotations, translations):
            count += 1
            diff = np.dot(positions, r.T) + t - positions[i]
            diff -= np.rint(diff)
            dist = np.sqrt(np.sum(np.dot(diff, lattice) ** 2, axis=1))
            j = np.nonzero(dist < symprec)[0][0]
            r_cart = similarity_transformation(lattice.T, r)
            borns_[i] += similarity_transformation(r_cart, borns[j])
        borns_[i] /= count

    return borns_, epsilon_

def symmetrize_2nd_rank_tensor(tensor, symmetry_operations, lattice):
    sym_cart = [similarity_transformation(lattice.T, r)
                for r in symmetry_operations]
    sum_tensor = np.zeros_like(tensor)
    for sym in sym_cart:
        sum_tensor += similarity_transformation(sym, tensor)
    return sum_tensor / len(symmetry_operations)

def _get_borns(ucell,
               borns,
               epsilon,
               primitive_matrix=None,
               supercell_matrix=None,
               is_symmetry=True,
               symmetrize_tensors=False,
               symprec=1e-5):
    """Parse Born effective charges and dielectric constants


     Args:
         ucell (Atoms): Unit cell structure
         borns (np.array): Born effective charges of ucell
         epsilon (np.array): Dielectric constant tensor

     Returns:
         (Born effective charges, dielectric constant)

     Raises:
          AssertionError: Inconsistency of number of atoms or Born effective
              charges.

     Warning:
         Broken symmetry of Born effective charges

     """

    assert len(borns) == ucell.get_number_of_atoms(), \
        "num_atom %d != len(borns) %d" % (ucell.get_number_of_atoms(),
                                          len(borns))

    if symmetrize_tensors:
        borns_, epsilon_ = symmetrize_borns_and_epsilon(borns,
                                                        epsilon,
                                                        ucell,
                                                        symprec=symprec,
                                                        is_symmetry=is_symmetry)

        if (abs(borns - borns_) > 0.1).any():
            lines = ["Born effective charge symmetry is largely broken. "
                     "Largest different among elements: "
                     "%s" % np.amax(abs(borns - borns_))]
            import warnings
            warnings.warn("\n".join(lines))

        borns = borns_
        epsilon = epsilon_

    borns, s_indep_atoms = _extract_independent_borns(
        borns,
        ucell,
        primitive_matrix=primitive_matrix,
        supercell_matrix=supercell_matrix,
        is_symmetry=is_symmetry,
        symprec=symprec)

    return borns, epsilon, s_indep_atoms

def _extract_independent_borns(borns,
                               ucell,
                               primitive_matrix=None,
                               supercell_matrix=None,
                               is_symmetry=True,
                               symprec=1e-5):
    if primitive_matrix is None:
        pmat = np.eye(3)
    else:
        pmat = primitive_matrix
    if supercell_matrix is None:
        smat = np.eye(3, dtype='intc')
    else:
        smat = supercell_matrix

    inv_smat = np.linalg.inv(smat)
    scell = get_supercell(ucell, smat, symprec=symprec)
    pcell = get_primitive(scell, np.dot(inv_smat, pmat), symprec=symprec)
    p2s = np.array(pcell.get_primitive_to_supercell_map(), dtype='intc')
    p_sym = Symmetry(pcell, is_symmetry=is_symmetry, symprec=symprec)
    s_indep_atoms = p2s[p_sym.get_independent_atoms()]
    u2u = scell.get_unitcell_to_unitcell_map()
    u_indep_atoms = [u2u[x] for x in s_indep_atoms]
    reduced_borns = borns[u_indep_atoms].copy()

    return reduced_borns, s_indep_atoms

def _read_born_and_epsilon_from_OUTCAR(filename):
    with open(filename) as outcar:
        borns = []
        epsilon = []

        while True:
            line = outcar.readline()
            if not line:
                break

            if "NIONS" in line:
                num_atom = int(line.split()[11])

            if "MACROSCOPIC STATIC DIELECTRIC TENSOR" in line:
                epsilon = []
                outcar.readline()
                epsilon.append([float(x) for x in outcar.readline().split()])
                epsilon.append([float(x) for x in outcar.readline().split()])
                epsilon.append([float(x) for x in outcar.readline().split()])

            if "BORN" in line:
                outcar.readline()
                line = outcar.readline()
                if "ion" in line:
                    for i in range(num_atom):
                        born = []
                        born.append([float(x)
                                     for x in outcar.readline().split()][1:])
                        born.append([float(x)
                                     for x in outcar.readline().split()][1:])
                        born.append([float(x)
                                     for x in outcar.readline().split()][1:])
                        outcar.readline()
                        borns.append(born)

        borns = np.array(borns, dtype='double')
        epsilon = np.array(epsilon, dtype='double')

    return borns, epsilon

#
# vasprun.xml handling
#
class VasprunWrapper(object):
    """VasprunWrapper class
    This is used to avoid VASP 5.2.8 vasprun.xml defect at PRECFOCK,
    xml parser stops with error.
    """
    def __init__(self, fileptr):
        self._fileptr = fileptr

    def read(self, size=None):
        element = self._fileptr.next()
        if element.find("PRECFOCK") == -1:
            return element
        else:
            return "<i type=\"string\" name=\"PRECFOCK\"></i>"

class Vasprun(object):
    def __init__(self, fileptr, use_expat=False):
        self._fileptr = fileptr
        self._use_expat = use_expat

    def read_forces(self):
        if self._use_expat:
            return self._parse_expat_vasprun_xml()
        else:
            vasprun_etree = self._parse_etree_vasprun_xml(tag='varray')
            return self._get_forces(vasprun_etree)

    def read_force_constants(self):
        vasprun = self._parse_etree_vasprun_xml()
        return self._get_force_constants(vasprun)

    def _get_forces(self, vasprun_etree):
        """
        vasprun_etree = etree.iterparse(fileptr, tag='varray')
        """
        forces = []
        for event, element in vasprun_etree:
            if element.attrib['name'] == 'forces':
                for v in element:
                    forces.append([float(x) for x in v.text.split()])
        return np.array(forces)

    def _get_force_constants(self, vasprun_etree):
        fc_tmp = None
        num_atom = 0
        for event, element in vasprun_etree:
            if num_atom == 0:
                atomtypes = self._get_atomtypes(element)
                if atomtypes:
                    num_atoms, elements, elem_masses = atomtypes[:3]
                    num_atom = np.sum(num_atoms)
                    masses = []
                    for n, m in zip(num_atoms, elem_masses):
                        masses += [m] * n

            # Get Hessian matrix (normalized by masses)
            if element.tag == 'varray':
                if element.attrib['name'] == 'hessian':
                    fc_tmp = []
                    for v in element.findall('./v'):
                        fc_tmp.append([float(x)
                                       for x in v.text.strip().split()])

        if fc_tmp is None:
            return False
        else:
            fc_tmp = np.array(fc_tmp)
            if fc_tmp.shape != (num_atom * 3, num_atom * 3):
                return False
            # num_atom = fc_tmp.shape[0] / 3
            force_constants = np.zeros((num_atom, num_atom, 3, 3),
                                       dtype='double')

            for i in range(num_atom):
                for j in range(num_atom):
                    force_constants[i, j] = fc_tmp[i*3:(i+1)*3, j*3:(j+1)*3]

            # Inverse normalization by atomic weights
            for i in range(num_atom):
                for j in range(num_atom):
                    force_constants[i, j] *= -np.sqrt(masses[i] * masses[j])

            return force_constants, elements

    def _get_atomtypes(self, element):
        atom_types = []
        masses = []
        valences = []
        num_atoms = []

        if element.tag == 'array':
            if 'name' in element.attrib:
                if element.attrib['name'] == 'atomtypes':
                    for rc in element.findall('./set/rc'):
                        atom_info = [x.text for x in rc.findall('./c')]
                        num_atoms.append(int(atom_info[0]))
                        atom_types.append(atom_info[1].strip())
                        masses.append(float(atom_info[2]))
                        valences.append(float(atom_info[3]))
                    return num_atoms, atom_types, masses, valences

        return None

    def _parse_etree_vasprun_xml(self, tag=None):
        if self._is_version528():
            return self._parse_by_etree(VasprunWrapper(self._fileptr), tag=tag)
        else:
            return self._parse_by_etree(self._fileptr, tag=tag)

    def _parse_by_etree(self, fileptr, tag=None):
        try:
            import xml.etree.cElementTree as etree
            for event, elem in etree.iterparse(fileptr):
                if tag is None or elem.tag == tag:
                    yield event, elem
        except ImportError:
            print("Python 2.5 or later is needed.")
            print("For creating FORCE_SETS file with Python 2.4, you can use "
                  "phonopy 1.8.5.1 with python-lxml .")
            sys.exit(1)

    def _parse_expat_vasprun_xml(self):
        if self._is_version528():
            return self._parse_by_expat(VasprunWrapper(self._fileptr))
        else:
            return self._parse_by_expat(self._fileptr)

    def _parse_by_expat(self, fileptr):
        vasprun = VasprunxmlExpat(fileptr)
        vasprun.parse()
        return vasprun.get_forces()[-1]

    def _is_version528(self):
        for line in self._fileptr:
            if '\"version\"' in str(line):
                self._fileptr.seek(0)
                if '5.2.8' in str(line):
                    sys.stdout.write(
                        "\n"
                        "**********************************************\n"
                        "* A special routine was used for VASP 5.2.8. *\n"
                        "**********************************************\n")
                    return True
                else:
                    return False

class VasprunxmlExpat(object):
    def __init__(self, fileptr):
        """Parsing vasprun.xml by Expat

        Args:
           fileptr: binary stream. Considering compatibility between python2.7
               and 3.x, it is prepared as follows:

               import io
               io.open(filename, "rb")

        """

        import xml.parsers.expat

        self._fileptr = fileptr

        self._is_forces = False
        self._is_stress = False
        self._is_positions = False
        self._is_symbols = False
        self._is_basis = False
        self._is_energy = False
        self._is_k_weights = False
        self._is_eigenvalues = False
        self._is_epsilon = False
        self._is_born = False
        self._is_efermi = False

        self._is_v = False
        self._is_i = False
        self._is_rc = False
        self._is_c = False
        self._is_set = False
        self._is_r = False

        self._is_scstep = False
        self._is_structure = False
        self._is_projected = False
        self._is_proj_eig = False

        self._all_forces = []
        self._all_stress = []
        self._all_points = []
        self._all_lattice = []
        self._symbols = []
        self._all_energies = []
        self._born = []
        self._forces = None
        self._stress = None
        self._points = None
        self._lattice = None
        self._energies = None
        self._epsilon = None
        self._born_atom = None
        self._efermi = None
        self._k_weights = None
        self._eigenvalues = None
        self._eig_state = [0, 0]
        self._projectors = None
        self._proj_state = [0, 0, 0]

        self._p = xml.parsers.expat.ParserCreate()
        self._p.buffer_text = True
        self._p.StartElementHandler = self._start_element
        self._p.EndElementHandler = self._end_element
        self._p.CharacterDataHandler = self._char_data

    def parse(self):
        try:
            self._p.ParseFile(self._fileptr)
        except:
            return False
        else:
            return True

    def get_forces(self):
        return np.array(self._all_forces)

    def get_stress(self):
        return np.array(self._all_stress)

    def get_epsilon(self):
        return np.array(self._epsilon)

    def get_efermi(self):
        return self._efermi

    def get_born(self):
        return np.array(self._born)

    def get_points(self):
        return np.array(self._all_points)

    def get_lattice(self):
        return np.array(self._all_lattice)

    def get_symbols(self):
        return self._symbols

    def get_energies(self):
        return np.array(self._all_energies)

    def get_k_weights(self):
        return self._k_weights

    def get_eigenvalues(self):
        return self._eigenvalues

    def get_projectors(self):
        return self._projectors

    def _start_element(self, name, attrs):
        # Used not to collect energies in <scstep>
        if name == 'scstep':
            self._is_scstep = True

        # Used not to collect basis and positions in
        # <structure name="initialpos" >
        # <structure name="finalpos" >
        if name == 'structure':
            if 'name' in attrs.keys():
                self._is_structure = True

        if (self._is_forces or
            self._is_stress or
            self._is_epsilon or
            self._is_born or
            self._is_positions or
            self._is_basis,
            self._is_k_weights):
            if name == 'v':
                self._is_v = True

        if name == 'varray':
            if 'name' in attrs.keys():
                if attrs['name'] == 'forces':
                    self._is_forces = True
                    self._forces = []

                if attrs['name'] == 'stress':
                    self._is_stress = True
                    self._stress = []

                if attrs['name'] == 'weights':
                    self._is_k_weights = True
                    self._k_weights = []

                if attrs['name'] == 'epsilon':
                    self._is_epsilon = True
                    self._epsilon = []

                if not self._is_structure:
                    if attrs['name'] == 'positions':
                        self._is_positions = True
                        self._points = []

                    if attrs['name'] == 'basis':
                        self._is_basis = True
                        self._lattice = []

        if name == 'i':
            if 'name' in attrs.keys():
                if attrs['name'] == 'efermi':
                    self._is_i = True
                    self._is_efermi = True

        if self._is_energy and name == 'i':
            self._is_i = True

        if name == 'energy' and (not self._is_scstep):
            self._is_energy = True
            self._energies = []

        if self._is_symbols and name == 'rc':
            self._is_rc = True

        if self._is_symbols and self._is_rc and name == 'c':
            self._is_c = True

        if self._is_born and name == 'set':
            self._is_set = True
            self._born_atom = []

        if name == 'array':
            if 'name' in attrs.keys():
                if attrs['name'] == 'atoms':
                    self._is_symbols = True

                if attrs['name'] == 'born_charges':
                    self._is_born = True

        if self._is_projected and not self._is_proj_eig:
            if name == 'set':
                if 'comment' in attrs.keys():
                    if 'spin' in attrs['comment']:
                        self._projectors.append([])
                        spin_num = int(attrs['comment'].replace("spin", ''))
                        self._proj_state = [spin_num - 1, -1, -1]
                    if 'kpoint' in attrs['comment']:
                        self._projectors[self._proj_state[0]].append([])
                        k_num = int(attrs['comment'].split()[1])
                        self._proj_state[1:3] = k_num - 1, -1
                    if 'band' in attrs['comment']:
                        s, k = self._proj_state[:2]
                        self._projectors[s][k].append([])
                        b_num = int(attrs['comment'].split()[1])
                        self._proj_state[2] = b_num - 1
            if name == 'r':
                self._is_r = True

        if self._is_eigenvalues:
            if name == 'set':
                if 'comment' in attrs.keys():
                    if 'spin' in attrs['comment']:
                        self._eigenvalues.append([])
                        spin_num = int(attrs['comment'].split()[1])
                        self._eig_state = [spin_num - 1, -1]
                    if 'kpoint' in attrs['comment']:
                        self._eigenvalues[self._eig_state[0]].append([])
                        k_num = int(attrs['comment'].split()[1])
                        self._eig_state[1] = k_num - 1
            if name == 'r':
                self._is_r = True

        if name == 'projected':
            self._is_projected = True
            self._projectors = []

        if name == 'eigenvalues':
            if self._is_projected:
                self._is_proj_eig = True
            else:
                self._is_eigenvalues = True
                self._eigenvalues = []

    def _end_element(self, name):
        if name == 'scstep':
            self._is_scstep = False

        if name == 'structure' and self._is_structure:
            self._is_structure = False

        if name == 'varray':
            if self._is_forces:
                self._is_forces = False
                self._all_forces.append(self._forces)

            if self._is_stress:
                self._is_stress = False
                self._all_stress.append(self._stress)

            if self._is_k_weights:
                self._is_k_weights = False

            if self._is_positions:
                self._is_positions = False
                self._all_points.append(self._points)

            if self._is_basis:
                self._is_basis = False
                self._all_lattice.append(self._lattice)

            if self._is_epsilon:
                self._is_epsilon = False

        if name == 'array':
            if self._is_symbols:
                self._is_symbols = False

            if self._is_born:
                self._is_born = False

        if name == 'energy' and (not self._is_scstep):
            self._is_energy = False
            self._all_energies.append(self._energies)

        if name == 'v':
            self._is_v = False

        if name == 'i':
            self._is_i = False
            if self._is_efermi:
                self._is_efermi = False

        if name == 'rc':
            self._is_rc = False
            if self._is_symbols:
                self._symbols.pop(-1)

        if name == 'c':
            self._is_c = False

        if name == 'r':
            self._is_r = False

        if name == 'projected':
            self._is_projected = False

        if name == 'eigenvalues':
            if self._is_projected:
                self._is_proj_eig = False
            else:
                self._is_eigenvalues = False

        if name == 'set':
            self._is_set = False
            if self._is_born:
                self._born.append(self._born_atom)
                self._born_atom = None

    def _char_data(self, data):
        if self._is_v:
            if self._is_forces:
                self._forces.append(
                    [float(x) for x in data.split()])

            if self._is_stress:
                self._stress.append(
                    [float(x) for x in data.split()])

            if self._is_epsilon:
                self._epsilon.append(
                    [float(x) for x in data.split()])

            if self._is_positions:
                self._points.append(
                    [float(x) for x in data.split()])

            if self._is_basis:
                self._lattice.append(
                    [float(x) for x in data.split()])

            if self._is_k_weights:
                self._k_weights.append(float(data))

            if self._is_born:
                self._born_atom.append(
                    [float(x) for x in data.split()])

        if self._is_i:
            if self._is_energy:
                self._energies.append(float(data.strip()))

            if self._is_efermi:
                self._efermi = float(data.strip())

        if self._is_c:
            if self._is_symbols:
                self._symbols.append(str(data.strip()))

        if self._is_r:
            if self._is_projected and not self._is_proj_eig:
                s, k, b = self._proj_state
                vals = [float(x) for x in data.split()]
                self._projectors[s][k][b].append(vals)
            elif self._is_eigenvalues:
                s, k = self._eig_state
                vals = [float(x) for x in data.split()]
                self._eigenvalues[s][k].append(vals)


#
# XDATCAR
#
def read_XDATCAR(filename="XDATCAR"):
    lattice = None
    symbols = None
    numbers_of_atoms = None
    with open(filename) as f:
        f.readline()
        scale = float(f.readline())
        a = [float(x) for x in f.readline().split()[:3]]
        b = [float(x) for x in f.readline().split()[:3]]
        c = [float(x) for x in f.readline().split()[:3]]
        lattice = np.transpose([a, b, c]) * scale
        symbols = f.readline().split()
        numbers_of_atoms = np.array(
            [int(x) for x in f.readline().split()[:len(symbols)]], dtype='intc')

    if lattice is not None:
        data = np.loadtxt(filename, skiprows=7, comments='D')
        return (data.reshape((-1, numbers_of_atoms.sum(), 3)),
                np.array(lattice, dtype='double', order='C'))
    else:
        return None

#
# OUTCAR handling (obsolete)
#
def read_force_constant_OUTCAR(filename):
    return get_force_constants_OUTCAR(filename)

def get_force_constants_OUTCAR(filename):
    file = open(filename)
    while 1:
        line = file.readline()
        if line == '':
            print("Force constants could not be found.")
            return 0

        if line[:19] == " SECOND DERIVATIVES":
            break

    file.readline()
    num_atom = int(((file.readline().split())[-1].strip())[:-1])

    fc_tmp = []
    for i in range(num_atom * 3):
        fc_tmp.append([float(x) for x in (file.readline().split())[1:]])

    fc_tmp = np.array(fc_tmp)

    force_constants = np.zeros((num_atom, num_atom, 3, 3), dtype=float)
    for i in range(num_atom):
        for j in range(num_atom):
            force_constants[i, j] = -fc_tmp[i*3:(i+1)*3, j*3:(j+1)*3]

    return force_constants
