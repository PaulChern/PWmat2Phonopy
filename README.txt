=============
PWmat2Phonopy
=============

PWmat2Phonopy provides an interface to phonopy, which can help PWmat user to perform phonon calculations. 
You might find it most useful for tasks you already have a relaxed atom.config. Typical usage often looks like this::

    First, you should include PWmat2Phonopy-x.x.x in you PYTHONPATH and PWmat2Phonopy/bin in your PATH.

    Also, you should have phonopy installed in your cluster.

    Then, just type in PWmatRunPhonopy.py in the directory where atom.config, etot.input, and PP are strored.

    The PWmatRunPhonopy.py will call PWmat2Phonopy, a PWmat version of phonopy with an interface to PWmat format and all the functions in phonopy.

    Other than using the PWmatRunPhonopy.py directly, you can acturally use PWmat2Phonopy too. 

    The use of the PWmat2phonopy is exactly the same as phonopy, except that you should include --pwmat in the args when you are using a PWmat calculator.

    If you use --vasp, --wien2k, --abinit, and et. al., PWmat2Phonopy will work exactly the same as the phonopy does.

    So, if you want to learn all the functions and how to use, you can consult phonopy website or user guide.
