# with the command bellow, start virtual box and run the shell for setup
# vagrant up --provision

$script = <<SCRIPT_LINES__
# root
apt-get update
apt-get install -y redis-server git python3-setuptools postgresql python-psycopg2 postgresql-server-dev-all python3-dev python-virtualenv

# vagrant
sudo -u vagrant sh <<SCRIPT_VAGRANT
redis-server &

# On windows, you can't put a pyvenv directory on /vagrant, because there is something wrong with
# a synchronized directory between windows and ubuntu
[ -d ~/pyvenv ] && rm -fr ~/pyvenv
virtualenv -p python3.4 ~/pyvenv
# Suddenly this doesn't work on ubuntu
# pyvenv-3.4 --without-pip ~/pyvenv
# . ~/pyvenv/bin/activate && curl https://bootstrap.pypa.io/get-pip.py | ~/pyvenv/bin/python

cd /vagrant
[ -d Napoleon ] && rm -fr Napoleon
git clone https://github.com/her0e1c1/Napoleon.git

cd Napoleon
# even if you are in python environment, you are deactevated on vagrant
. ~/pyvenv/bin/activate && python setup.py install
. ~/pyvenv/bin/activate && python manage.py migrate

SCRIPT_VAGRANT

SCRIPT_LINES__

Vagrant.configure(2) do |config|
  config.vm.box = "ubuntu/trusty64"

  # mac bridge
  # config.vm.network "public_network", bridge: "en0: Wi-Fi (AirPort)"

  config.vm.network :private_network, ip:"192.168.56.11"

  config.vm.provider "virtualbox" do |v|
    v.customize ["modifyvm", :id, "--ostype", "Ubuntu_64"]
    v.gui = true
  end

  config.vm.provision "shell", inline: $script
end
