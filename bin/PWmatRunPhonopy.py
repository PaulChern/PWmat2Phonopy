#!/usr/bin/env python
import os
import subprocess

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
    pwmat2phonopy = pwmat_run.pwmat2phonopyParser(etotinput=EtotInput)
    confs_scf = EtotInput.get_configures()
    print('current workding directory is: '+dir0)
    print('phonon will be calculate in: '+dir0+'/phonon')
    if os.path.exists(dir0+'/pwmat2phonopy.in'):
        raw_input('\nPlease type enter to edit the \033[93m pwmat2phonopy.in \033[0m file\n')
        subprocess.call(["vim","./pwmat2phonopy.in"])
    else:
        pwmat2phonopy.write_input()
        raw_input('\nPlease type enter to edit the \033[93m pwmat2phonopy.in \033[0m file\n')
        subprocess.call(["vim","./pwmat2phonopy.in"])
    pwmat2phonopy.read_input(filename='pwmat2phonopy.in')

#########################
# produce displacements #
#########################
    DIM = pwmat2phonopy.get_configures('dim')['val'].strip()
    print(subprocess.Popen('PWmat2Phonopy --pwmat -d --dim="'+DIM+'" -c atom.config', shell=True, stdout=subprocess.PIPE).stdout.read())

#######################
# initiallize phonopy #
#######################
    os.chdir(dir0+'/phonon')

# prepre nodes
    nodes = pwmat2phonopy.get_configures('nodes')['val']
    EtotInput.set_configures('nodes', nodes.strip())

# prepare new k-points for supercell
    mp_n123 = pwmat2phonopy.get_configures('mp_n123')['val']
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
        EtotInput.set_configures('job', 'scf')
        EtotInput.write_input('./'+force+'/etot.input')
    os.chdir(dir0+'/phonon')

# prepare postprocess script
    pwmat_run.creat_post_process_script(num_forces=num_forces)

    pwmat2phonopy.creat_phonopy_conf()

    subprocess.Popen('chmod +x '+'plot_phonon.sh', shell=True)

# submit the jobs
    node1 = int(nodes.split()[0])
    node2 = int(nodes.split()[1])
    ppn = node1*node2
    queue = 'test'
    wall_time = pwmat2phonopy.get_configures('wall_time')['val'].strip()
    for i in range(num_forces):
        force = "{pre_filename}-{0:0{width}}".format(i + 1, pre_filename='forces', width=3)
        os.chdir(dir0+'/phonon/'+force)
        pwmat_run.creat_pbs(ppn=ppn, queue=queue, wall_time=wall_time, job_name=force)
        subprocess.Popen('chmod +x '+force+'.pbs', shell=True)
        subprocess.Popen('qsub '+force+'.pbs', shell=True)
    os.chdir(dir0+'/phonon')

    print("\033[93m\n Please run ./plot_phonon.sh to get the plot and data, when the forces calculations are finished! \n\033[0m")
