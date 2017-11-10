#!/usr/bin/env python

import sys
import os
import subprocess

try:
    import numpy as np
except ImportError:
    print("\033[93m\n ##?| numpy module may be not available ##\n\033[0m")

try:
    from pwmat2phonopy.interface import pwmat_run
except ImportError:
    print("\033[93m\n ##?| interface to pwmat package may be not available ##\n\033[0m")

__author__  = "Paul Chern"
__email__   = "peng.chen.iphy@gmail.com"
__licence__ = "GPL"
__date__    = "Nov. 2017"

if __name__ == "__main__":
    pwmat_run.print_phononpy()
############################
# initiallize calculations #
############################
    dir0 = os.getcwd()

    EtotInput = pwmat_run.InputParser(filename='etot.input')
    confs_scf = EtotInput.get_configures()
#########################
# produce displacements #
#########################
    DIM = raw_input('>> input supercell: "nx ny nz" (type enter to use default: "2 2 2") <<\n')
    if DIM == '':
        DIM = "2 2 2"
        print("2 2 2")
    print(subprocess.Popen('PWmat2Phonopy --pwmat -d --dim="'+DIM+'" -c atom.config', shell=True, stdout=subprocess.PIPE).stdout.read())

#######################
# initiallize phonopy #
#######################
    os.chdir(dir0+'/phonon')

# prepre nodes
    nodes = raw_input('>> input node1 and node2 for supercell calculations: "node1 node2" (type enter to use default value the same as scf) <<\n')
    if nodes != '':
        EtotInput.set_configures('nodes', nodes)
    else:
        nodes = EtotInput.get_configures()['nodes']
        print(nodes)

# prepare new k-points for supercell
    mp_n123 = raw_input('>> input new mp_n123 for the supercell: 10 10 10 0 0 0 (type enter to use default value the same as unitcell scf) <<\n')
    if mp_n123 == '': 
        print(EtotInput.get_configures()['mp_n123'])
        print("\033[93m\n WARNING: the same k-points as unitcell are used, the calculation for supercell will be heavy! \n\033[0m")
    else:
        EtotInput.set_configures('mp_n123', mp_n123.strip())
# prepare input files in the forces directory
    forces_dir = subprocess.Popen('ls -d forces*/ | cut -d "/" -f 1', shell=True, stdout=subprocess.PIPE).stdout.read()
    forces_dir = forces_dir.split()
    num_forces = len(forces_dir)
    for i in range(num_forces):
        force = "{pre_filename}-{0:0{width}}".format(i + 1, pre_filename='forces', width=3)
        for tag in confs_scf.keys():
            if 'in.psp' in tag:
                subprocess.Popen('cp ../'+confs_scf[tag]+' ./'+force, shell=True)
        EtotInput.write_input('./'+force+'/etot.input')
    os.chdir(dir0+'/phonon')

# prepare postprocess script
    pwmat_run.creat_post_process_script(num_forces=num_forces)

    BAND = raw_input('>> input special Q point in the Brillioun zone: "Q1_x Q1_y Q1_z  Q2_x Q2_y Q2_z  Q3_x Q3_y Q3_z ......" \n (type enter to use default "0.0 0.0 0.0  0.5 0.0 0.0")<<\n\033[93m\n You can change it by modifying band_dos.conf after the forces are submitted to the cluster \n\033[0m')
    if BAND == '':
        BAND = "0.0 0.0 0.0  0.5 0.0 0.0"
        print(BAND)
    BAND_LABELS = raw_input('>> input special Q point symbol: "Q1  Q2  Q3 ......" \n (type enter to use default "\Gamma  X")<<\n\033[93m\n You can change it by modifying band_dos.conf after the forces are submitted to the cluster \n\033[0m')
    if BAND_LABELS == '':
        BAND_LABELS = "\Gamma  X"
        print(BAND_LABELS)
    BAND_POINTS = raw_input('>> input number of q points along the k path: "Num" (type enter to use default "101")<<\n\033[93m\n You can change it by modifying band_dos.conf after the forces are submitted to the cluster \n\033[0m')
    if BAND_POINTS == '':
        BAND_POINTS = '101'
        print(BAND_POINTS)
    unit = raw_input('>> Choose unit THz:1, cm^-1:2, eV:3, and meV:4, your choosen is : "number" (type enter to use default "1")<<\n\033[93m\n You can change it by modifying band_dos.conf after the forces are submitted to the cluster \n\033[0m')
    if unit == '':
        unit = '1'
        print(unit)
    MP = raw_input('>> input q-mesh for the DOS calculation: "num_q1 num_q2 num_q3" (type enter to use default "41 41 41")<<\n\033[93m\n You can change it by modifying band_dos.conf after the forces are submitted to the cluster \n\033[0m')
    if MP == '':
        MP = "41 41 41"
        print(MP)
    FPITCH = '0.1'
    SIGMA = raw_input('>> input smearing width for the DOS calculation: "float_number" (type enter to use default "0.05")<<\n\033[93m\n You can change it by modifying band_dos.conf after the forces are submitted to the cluster \n\033[0m')
    if SIGMA == '':
        SIGMA = '0.05'
        print(SIGMA)

    pwmat_run.creat_phonopy_conf(DIM=DIM, 
                                 BAND=BAND, 
                                 BAND_LABELS=BAND_LABELS, 
                                 BAND_POINTS=BAND_POINTS, 
                                 unit=unit, 
                                 MP=MP, 
                                 FPITCH=FPITCH, 
                                 SIGMA=SIGMA)

    subprocess.Popen('chmod +x '+'plot_phonon.sh', shell=True)

# submit the jobs
    node1 = int(nodes.split()[0])
    node2 = int(nodes.split()[1])
    ppn = node1*node2
    queue = 'test'
    wall_time = raw_input('>> input wall time: "hours:minutes:seconds" (type enter to use default "1000:00:00")<<\n')
    if wall_time == '':
        wall_time = "1000:00:00"
        print(wall_time)
    for i in range(num_forces):
        force = "{pre_filename}-{0:0{width}}".format(i + 1, pre_filename='forces', width=3)
        os.chdir(dir0+'/phonon/'+force)
        pwmat_run.creat_pbs(ppn=ppn, queue=queue, wall_time=wall_time, job_name=force)
        subprocess.Popen('chmod +x '+force+'.pbs', shell=True)
        subprocess.Popen('qsub '+force+'.pbs', shell=True)
    os.chdir(dir0+'/phonon')

    print("\033[93m\n Please run ./plot_phonon.sh to get the plot and data, when the forces calculations are finished! \n\033[0m")
