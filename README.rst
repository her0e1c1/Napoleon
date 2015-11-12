
==========
 Napoleon
==========

.. contents::

Introduction
============

Napoleon is a card game.

You can play Napoleon at https://napolo.herokuapp.com if you want.

Install on virtual box
======================
you can make a development environment with vagrant.::

    # get image
    # you don't need to run this if you have got the image once
    vagrant box add ubuntu/trusty64
    
    # go to project root. you need to create it if it doesn't exist
    cd /path/to/project_root

    # copy Vagrantfile (just download the file. so you can get it from a web browser)
    curl https://raw.githubusercontent.com/her0e1c1/Napoleon/master/Vagrantfile -O

    # set up virtualbox and install
    vagrant up --provision
    
    # login the server of ubuntu
    vagrant ssh
    # or just use ssh. password is vagrant (if you use windows, try TeraTerm)
    ssh vagrant@192.168.56.11

    # run Napoleon server on ubuntu
    source /vagrant/pyvenv/bin/activate
    python /vagrant/Napoleon/main.py --log_to_stderr

Now you can access a Napoleon server at ``http://192.168.56.11:8001/``

uninstall ::

    vagrant destroy -f
