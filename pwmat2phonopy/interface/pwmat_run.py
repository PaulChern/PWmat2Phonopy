#!/usr/bin/env python

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

# Parse PWmat etot_input file
class InputParser(object):
    def __init__(self, filename=None):
        self._confs = {}

        if filename is not None:
            self.read_input(filename) # store data in self._confs

    def read_input(self, filename):
        file = open(filename, 'r')
        is_continue = False
        left = None

        for line in file:
            if line.strip() == '':
                is_continue = False
                continue

            if line.strip()[0] == '#':
                is_continue = False
                continue

            if line.find('=') != -1:
                left, right = [x.strip() for x in line.split('=')]
                right_value = right.split('#')[0]
                self._confs[left.lower()] = right_value.strip()
            else:
                nodes = line.split()[0:2]
                self._confs['nodes'] = '    '.join(nodes)

    def get_configures(self):
        return self._confs

    def set_configures(self, key, elem):
        self._confs[key.lower()] = elem

    def write_input(self, filename='./etot.input'):
        lines = self._get_input_lines()
        with open(filename, 'w') as w:
            w.write("\n".join(lines))

    def _get_input_lines(self):

        confs = self._confs
        lines = []
        lines.append(confs['nodes'])
        for key, elem in confs.items():
            if key != 'nodes':
                lines.append(" = ".join([key, elem]))
        lines.append('')

        return lines

def creat_pbs(ppn, queue, wall_time, job_name='forces'):
    lines = []
    lines.append('#PBS -N '+job_name)
    lines.append('#PBS -l nodes=1:ppn='+str(ppn))
    lines.append('#PBS -q '+queue)
    lines.append('#PBS -e '+job_name)
    lines.append('#PBS -o '+job_name)
    lines.append('#PBS -l walltime='+wall_time)
    lines.append('')
    lines.append('NPROCS=`wc -l < $PBS_NODEFILE`')
    lines.append('')
    lines.append('cd $PBS_O_WORKDIR')
    lines.append('')
    lines.append('mpirun -np ${NPROCS} PWmat')
    lines.append('')

    with open(job_name+'.pbs', 'w') as w:
        w.write("\n".join(lines))
def creat_post_process_script(num_forces):
    force = ''
    for i in range(num_forces):
        force += "./{pre_filename}-{0:0{width}}/OUT.FORCE ".format(i + 1, pre_filename='forces', width=3)
    lines = []
    lines.append('#!/bin/sh')
    lines.append('PWmat2Phonopy --pwmat -f '+force)
    lines.append('PWmat2Phonopy --pwmat -p -s band_dos.conf -c ../atom.config')
    lines.append('')
    with open('plot_phonon.sh', 'w') as w:
        w.write("\n".join(lines))

def creat_phonopy_conf(DIM, BAND, BAND_LABELS, BAND_POINTS, unit, MP, FPITCH, SIGMA):
    if unit == '0': # THz
        FREQUENCY_CONVERSION_FACTOR = '15.633302'
    elif unit == '1': # cm^-1
        FREQUENCY_CONVERSION_FACTOR = '521.47083'
    elif unit == '2': # eV
        FREQUENCY_CONVERSION_FACTOR = '6.46541380e-2'
    elif unit == '3': # meV
        FREQUENCY_CONVERSION_FACTOR = '6.46541380e1'
    else:
        FREQUENCY_CONVERSION_FACTOR = '15.633302'

    lines = []
    lines.append('DIM = '+DIM)
    lines.append('PRIMITIVE_AXIS = 1.0 0.0 0.0  0.0 1.0 0.0  0.0 0.0 1.0')
    lines.append('BAND = '+BAND)
    lines.append('BAND_LABELS = '+BAND_LABELS)
    lines.append('BAND_POINTS = '+BAND_POINTS)
    lines.append('FREQUENCY_CONVERSION_FACTOR = '+FREQUENCY_CONVERSION_FACTOR)
    lines.append('MP = '+MP)
    lines.append('DOS = TRUE')
    lines.append('FPITCH = '+FPITCH)
    lines.append('SIGMA = '+SIGMA)
    lines.append('')

    with open('band_dos.conf', 'w') as w:
        w.write("\n".join(lines))

def creat_pwmat2phonopy_input():
    lines = []
    lines.append('nodes = 1    1                                           # node1 node2 for pwmat parallel configuration')
    lines.append('DIM = 2 2 2                                              # supercell dimension which will be used to make displacements')
    lines.append('PRIMITIVE_AXIS = 1.0 0.0 0.0  0.0 1.0 0.0  0.0 0.0 1.0   # ')
    lines.append('BAND = 0.0 0.0 0.0  0.5 0.0 0.0                          # special q points in Brillioun zone')
    lines.append('BAND_LABELS = \Gamma  X                                  # labels of the special q points')
    lines.append('BAND_POINTS = 101                                        # number of q-point along the high symmetry path')
    lines.append('FREQUENCY_CONVERSION_FACTO = THz                         # unit of the frequency')
    lines.append('DOS = TRUE                                               # switch to the DOS calculation')
    lines.append('MP = 41 41 41                                            # q-mesh for the DOS calculation')
    lines.append('FPITCH = 0.1                                             # frequency interval for DOS calculation')
    lines.append('SIGMA = 0.1                                              # smearing width for DOS calculation')
    lines.append('')

    with open('pwmat2phonopy.in', 'w') as w:
        w.write("\n".join(lines))

# Parse pwmat2phonopy.in
class pwmat2phonopyParser(object):
    def __init__(self, filename=None):
        self._confs = {'nodes':{'val':'1    1                                           ', 'comm':'# node1 node2 for pwmat parallel configuration'},
                       'DIM':{'val':'2 2 2                                              ', 'comm':'# supercell dimension which will be used to make displacements'},
                       'PRIMITIVE_AXIS':{'val':'1.0 0.0 0.0  0.0 1.0 0.0  0.0 0.0 1.0   ', 'comm':'# the primitive cell for building the dynamical matrix'},
                       'BAND':{'val':'0.0 0.0 0.0  0.5 0.0 0.0                          ', 'comm':'# special q points in Brillioun zone'},
                       'BAND_LABELS':{'val':'\Gamma  X                                  ', 'comm':'# labels of the special q points'},
                       'BAND_POINTS':{'val':'101                                        ', 'comm':'# number of q-point along the high symmetry path'},
                       'FREQUENCY_CONVERSION_FACTOR':{'val':'THz                        ', 'comm':'# unit of the frequency'},
                       'DOS':{'val':'TRUE                                               ', 'comm':'# switch to the DOS calculation'},
                       'MP':{'val':'41 41 41                                            ', 'comm':'# q-mesh for the DOS calculation'},
                       'FPITCH':{'val':'0.1                                             ', 'comm':'# frequency interval for DOS calculation'},
                       'SIGMA':{'val':'0.1                                              ', 'comm':'# smearing width for DOS calculation'}
                      }
        self._keywords = ['nodes', 'DIM', 'PRIMITIVE_AXIS', 'BAND', 'BAND_LABELS', 'BAND_POINTS', 'FREQUENCY_CONVERSION_FACTOR', 'DOS', 'MP', 'FPITCH', 'SIGMA']
        if filename is not None:
            self.read_input(filename) # store data in self._confs

    def read_input(self, filename):
        file = open(filename, 'r')
        is_continue = False
        left = None

        for line in file:
            if line.strip() == '':
                is_continue = False
                continue

            if line.strip()[0] == '#':
                is_continue = False
                continue

            if line.find('=') != -1:
                left, right = [x.strip() for x in line.split('=')]
                right_value, comm = right.split('#')
                self._confs[left.lower()] = {'val':right_value, 'comm':comm}

    def get_configures(self):
        return self._confs

    def set_configures(self, key, elem):
        self._confs[key.lower()]['val'] = elem

    def write_input(self, filename='./pwmat2phonopy.in'):
        lines = self._get_input_lines()
        with open(filename, 'w') as w:
            w.write("\n".join(lines))

    def _get_input_lines(self):

        confs = self._confs
        lines = []
        lines.append(confs['nodes'])
        for key in self._keywords:
            lines.append(" = ".join([key, confs[key]['val']])+' '+confs[key]['comm'])
        lines.append('')

        return lines

#    def write_pwmat2phonopy_input():
#        lines = []
#        lines.append('nodes = 1    1                                           # node1 node2 for pwmat parallel configuration')
#        lines.append('DIM = 2 2 2                                              # supercell dimension which will be used to make displacements')
#        lines.append('PRIMITIVE_AXIS = 1.0 0.0 0.0  0.0 1.0 0.0  0.0 0.0 1.0   # the primitive cell for building the dynamical matrix')
#        lines.append('BAND = 0.0 0.0 0.0  0.5 0.0 0.0                          # special q points in Brillioun zone')
#        lines.append('BAND_LABELS = \Gamma  X                                  # labels of the special q points')
#        lines.append('BAND_POINTS = 101                                        # number of q-point along the high symmetry path')
#        lines.append('FREQUENCY_CONVERSION_FACTO = THz                         # unit of the frequency')
#        lines.append('DOS = TRUE                                               # switch to the DOS calculation')
#        lines.append('MP = 41 41 41                                            # q-mesh for the DOS calculation')
#        lines.append('FPITCH = 0.1                                             # frequency interval for DOS calculation')
#        lines.append('SIGMA = 0.1                                              # smearing width for DOS calculation')
#        lines.append('')
#
#        with open('pwmat2phonopy.in', 'w') as w:
#            w.write("\n".join(lines))
