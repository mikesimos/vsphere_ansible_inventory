#!/usr/bin/env python

#   This file is part of vSphere Ansible Inventory.
#
#   vSphere Ansible Inventory is free software: you can redistribute it and/or
#   modify it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or (at your
#   option) any later version.
#
#   vSphere Ansible Inventory is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU General Public License for more details.
#   You should have received a copy of the GNU General Public License
#   along with vSphere Ansible Inventory. If not, see:
#   <http://www.gnu.org/licenses/>.
#
# Authors:
# version 0.1 Michael-Angelos Simos

"""
Python script for listing VMware vSphere Virtual Machines for Ansible Inventory
"""

import atexit
from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim
from json import dumps, dump, load
from argparse import ArgumentParser
from configparser import ConfigParser
import os
from sys import exit
from time import time


class VSphere:

    def __init__(self, vsphere_hostname=None, vsphere_username='', vsphere_password='', vsphere_port=443):
        """
        :param str vsphere_hostname: The FQDN of vSphere
        :param str vsphere_username: A vSphere (read only) user
        :param str vsphere_password: vSphere user password
        """
        try:
            self.inventory = []
            self.__session__ = connect.SmartConnectNoSSL(host=vsphere_hostname,
                                                         user=vsphere_username,
                                                         pwd=vsphere_password,
                                                         port=vsphere_port)

            atexit.register(connect.Disconnect, self.__session__)

        except Exception as error:
            print("[Error] Could not connect to vSphere: {}".format(error))
            exit(1)

    def list_inventory(self):
        try:
            content = self.__session__.RetrieveContent()
            vms_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True).view
            for vm in vms_view:
                self.append_vm_info(vm)
            # TODO: ini configurable filters
            self.filter_inventory(guest_id=['centos64Guest', 'centosGuest'], template=False)
            output = self.grouped_inventory()
            output.update({"_meta": {"hostvars": {}}})
            return output
        except vmodl.MethodFault as error:
            print("[Error] : " + error.msg)
            exit(1)

    def append_vm_info(self, virtual_machine):
        """
        Append information for a particular virtual machine object
        """

        # select active networks
        net = []
        summary = virtual_machine.summary

        for dev in virtual_machine.config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualEthernetCard):
                if dev.connectable.connected:
                    net.append(dev.backing.deviceName)

        name = getattr(virtual_machine.guest, 'hostName', virtual_machine.name)
        guest_id = getattr(summary.guest, 'guestId', getattr(summary.config, 'guestId', None))
        guest_full_name = getattr(summary.guest, 'guestFullName', summary.config.guestFullName)
        ip_address = getattr(summary.guest, 'ipAddress', None)
        if name:
            self.inventory.append({"name": name,
                                   "guest_id": guest_id,
                                   "guest_full_name": guest_full_name,
                                   "net": net,
                                   "state": summary.runtime.powerState,
                                   "instance_uuid": summary.config.instanceUuid,
                                   "template": summary.config.template,
                                   "ip_address": ip_address
                                   })

    def filter_inventory(self, **kwargs):
        for d in reversed(self.inventory):
            for name, value in kwargs.items():
                if type(value) == list:
                    if d[name] not in value and d in self.inventory:
                        self.inventory.remove(d)
                else:
                    if d[name] != value and d in self.inventory:
                        self.inventory.remove(d)

    def grouped_inventory(self, group='net', field='name'):
        data = {}
        for d in self.inventory:
            if d[field]:
                if type(d[group]) == list:
                    for g in d[group]:
                        if g in data:
                            data[g].append(d[field])
                        else:
                            data[g] = [d[field]]
                else:
                    if d[group] in data:
                        data[d[group]].append(d[field])
                    else:
                        data[d[group]] = [d[field]]
        return data

    def list_and_save(self, cache_path):
        """
        :param  str cache_path: A path for caching inventory list data.
        :return:
        """
        data = self.list_inventory()
        with open(cache_path, 'w') as fp:
            dump(data, fp)
        return data

    def cached_inventory(self, cache_path=None, cache_ttl=3600, refresh=False):
        """
        Wrapper method implementing caching functionality over list_inventory.
        :param str cache_path: A path for caching inventory list data. Quite a necessity for large environments.
        :param int cache_ttl: Integer Inventory list data cache Time To Live in seconds. (cache Expiration period)
        :param boolean refresh: Setting this True, triggers a cache refresh. Fresh data is fetched.
        :return:
        Returns an Ansible pluggable dynamic inventory, as a Python json serializable dictionary.
        """
        if refresh:
            return self.list_and_save(cache_path)
        else:
            if os.path.isfile(cache_path) and time() - os.stat(cache_path).st_mtime < cache_ttl:
                try:
                    with open(cache_path) as f:
                        data = load(f)
                        return data
                except (ValueError, IOError):
                    return self.list_and_save(cache_path)
            else:
                if not os.path.exists(os.path.dirname(cache_path)):
                    try:
                        if cache_path:
                            os.makedirs(os.path.dirname(cache_path))
                        else:
                            raise OSError("[Error] cache_path not defined: {}".format(cache_path))
                    # handle race condition
                    except OSError as exc:
                        if exc.errno == errno.EACCES:
                            print("{}".format(str(exc)))
                            exit(1)
                        elif exc.errno != errno.EEXIST:
                            raise
                return self.list_and_save(cache_path)


def parse_config():
    """ Parse available configuration.
    Default configuration file: vsphere-inventory.ini
    Configuration file path may be overridden,
    by defining an environment variable: VSPHERE_INVENTORY_INI_PATH
    :return: (cache_path, cache_ttl, vsphere_host, vsphere_user, vsphere_pass)
    """
    config = ConfigParser()
    vsphere_default_ini_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'vsphere-inventory.ini')
    vsphere_ini_path = os.path.expanduser(
        os.path.expandvars(os.environ.get('VSPHERE_INVENTORY_INI_PATH', vsphere_default_ini_path)))
    config.read(vsphere_ini_path)
    cache_path = config.get('GENERIC', 'cache_path', fallback='/tmp/ansible-vsphere-inventory-cache.tmp')
    cache_ttl = config.getint('GENERIC', 'cache_ttl', fallback=7200)
    vsphere_host = config.get('GENERIC', 'vsphere_host', fallback='')
    vsphere_user = config.get('GENERIC', 'vsphere_user', fallback='')
    vsphere_pass = config.get('GENERIC', 'vsphere_pass', fallback='')

    return cache_path, cache_ttl, vsphere_host, vsphere_user, vsphere_pass


def get_args():
    """
    Return Command Line Arguments.
    :return: ArgumentParser instance
    """
    parser = ArgumentParser(description="vSphere Ansible Inventory.",
                            epilog="Example:\n"
                                   "./vsphere_inventory.py -l\n"
                                   "./vsphere_inventory.py -s <vSphere.hostname>"
                                   "-u <vSphere_username> -p <vSphere_password> -l\n")
    parser.add_argument('-s', '--hostname', help='vSphere FQDN')
    parser.add_argument('-u', '--username', help='vSphere username')
    parser.add_argument('-p', '--password', help='vSphere password')
    parser.add_argument('-g', '--guest', help='Print a single guest')
    parser.add_argument('-x', '--host', help='Print a single guest')
    parser.add_argument('-r', '--reload-cache', help='Reload cache', action='store_true')
    parser.add_argument('-l', '--list', help='List all VMs', action='store_true')
    return parser.parse_args()


def main():

    # - Get command line args and config args.
    args = get_args()
    (cache_path, cache_ttl, vsphere_host, vsphere_user, vsphere_pass) = parse_config()

    # - Override settings with arg parameters if defined
    if not args.password:
        if not vsphere_pass:
            import getpass
            vsphere_pass = getpass.getpass()
        setattr(args, 'password', vsphere_pass)
    if not args.username:
        setattr(args, 'username', vsphere_user)
    if not args.hostname:
        setattr(args, 'hostname', vsphere_host)

    # - Perform requested operations (list, host/guest)
    if args.host or args.guest:
        print ('{}')
        exit(0)
    elif args.list or args.reload_cache:
        v = VSphere(args.hostname, args.username, args.password)
        data = v.cached_inventory(cache_path=cache_path, cache_ttl=cache_ttl, refresh=args.reload_cache)
        print ("{}".format(dumps(data)))
        exit(0)

if __name__ == "__main__":
    main()
