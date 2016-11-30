# Description
vSphere Ansible Inventory is a fast and robust script for listing VMWare vCenter virtual machines in Ansible dynamic 
inventory format. This script is one of the fastest of its kind, yet features configurable caching, proving quite useful
 in large scale environments.
Its flexibly configurable via it's configuration file (vsphere_inventory.ini).

# Installation

###### install prerequisites:
``
pip install -r requirements.txt
``

###### Clone vsphere_ansible_inventory at your IT Automation server:
``git clone https://github.com/mikeSimos/vsphere_ansible_inventory.git``

###### Configure vsphere_inventory.ini file accordingly.
#


# Usage
Example usage:
``
$ ansible all -i vsphere_inventory.py -m ping

# Requirements
* Python >=2.6 or >= 3.3
* pyVmomi
* configparser for simultaneously python 2 and 3 compatibility

All package requirements are installed (with pip) during installation.