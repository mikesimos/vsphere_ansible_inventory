[![Build Status](https://travis-ci.org/mikesimos/vsphere_ansible_inventory.svg?branch=master)](https://travis-ci.org/mikesimos/vsphere_ansible_inventory)
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
``git clone https://github.com/mikesimos/vsphere_ansible_inventory.git``

###### Configure vsphere_inventory.ini file accordingly. An example configuration may be found in current
vsphere-inventory.ini file.
#


# Usage
Example usage:
`$ ansible all -i vsphere_inventory.py -m ping`

# Requirements
* pyVmomi
* configparser

All package requirements are installed (with pip) during installation.

# Compatibility
* Python >=2.7 or >= 3.3


Author Information
------------------

Michael Angelos Simos

[www.asimos.tk](https://www.asimos.tk)
