#!/bin/sh
PWmat2Phonopy --pwmat -f ./forces-001/OUT.FORCE ./forces-002/OUT.FORCE ./forces-003/OUT.FORCE 
PWmat2Phonopy --pwmat -p -s band_dos.conf -c ../atom.config
