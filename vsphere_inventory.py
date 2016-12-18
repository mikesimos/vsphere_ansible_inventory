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
try:
    from json import dumps, dump, load
except ImportError:
    from simplejson import dumps, dump, load
from argparse import ArgumentParser
try:
    # python 2
    from ConfigParser import SafeConfigParser as ConfigParser
except ImportError:
    # python 3
    from configparser import ConfigParser
import os
import errno
from sys import exit
from time import time


class VSphere:

    def __init__(self, vcenter_hostname=None, vsphere_username='', vshpere_password='',
                 vsphere_port=443, nosslcheck=False):
        """
        Initialize a session with vSphere vCenter API.
        :param str vcenter_hostname: The FQDN of vSphere vCenter
        :param str vsphere_username: A vSphere vCenter (read only) user
        :param str vshpere_password: vSphere vCenter user password
        :param int vsphere_port: vSphere Web Client port
        :param bool nosslcheck: Ignore certificate verification
        """
        try:
            self.inventory = []

            if nosslcheck:
                vcenter_api_connection = connect.SmartConnectNoSSL
            else:
                vcenter_api_connection = connect.SmartConnect

            self.__session__ = vcenter_api_connection(host=vcenter_hostname,
                                                      user=vsphere_username,
                                                      pwd=vshpere_password,
                                                      port=vsphere_port)

            atexit.register(connect.Disconnect, self.__session__)

        except Exception as error:
            print("[Error] Could not connect to vSphere: {}".format(error))
            exit(1)

    def list_inventory(self, filters):
        """
        :param dict filters:A dictionary of pyVmomi virtual machine attribute key-value filters.
        List vSphere vCenter API virtual machines. Listing function supports filtering and grouping.
        :return: An Ansible pluggable dynamic inventory, as a Python json serializable dictionary.
        """
        try:
            content = self.__session__.RetrieveContent()
            vms_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True).view
            for vm in vms_view:
                self.append_vm_info(vm)
            self.filter_inventory(**filters)
            output = self.grouped_inventory()
            output.update({"_meta": {"hostvars": {}}})
            return output
        except vmodl.MethodFault as error:
            print("[Error] : " + error.msg)
            exit(1)

    def append_vm_info(self, virtual_machine):
        """
        Append information of a particular virtual machine object
        :param object virtual_machine: vim.VirtualMachine view object
        :return: None
        """

        net = []
        summary = virtual_machine.summary
        # select first active network
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
        """
        Apply filtering on inventory by kwargs
        :param kwargs: filter parameter arguments
        :return: None
        """
        for d in reversed(self.inventory):
            for name, value in kwargs.items():
                if type(value) == list:
                    if d[name] not in value and d in self.inventory:
                        self.inventory.remove(d)
                else:
                    if str(d[name]) != value and d in self.inventory:
                        self.inventory.remove(d)

    def grouped_inventory(self, group='net', field='name'):
        """
        Group inventory in group input argument groups, providing a list output of specified field.
        :param group: Group by attribute name.
        :param field: Listing field name.
        :return: An Ansible pluggable dynamic inventory, as a Python json serializable dictionary.
        """
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

    def list_and_save(self, filters, cache_path):
        """
        :param  dict filters: A dictionary of pyVmomi virtual machine attribute key-value filters.
        :param  str cache_path: Path of inventory list data cache.
        :return: Ansible pluggable dynamic inventory, as a Python json serializable dictionary.
        """
        data = self.list_inventory(filters)
        with open(cache_path, 'w') as fp:
            dump(data, fp)
        return data

    def cached_inventory(self, filters, cache_path=None, cache_ttl=3600, refresh=False, ):
        """
        Wrapper method implementing caching functionality over list_inventory.
        :param dict filters: A dictionary of pyVmomi virtual machine attribute key-value filters.
        :param str cache_path: A path for caching inventory list data. Quite a necessity for large environments.
        :param int cache_ttl: Integer Inventory list data cache Time To Live in seconds. (cache Expiration period)
        :param boolean refresh: Setting this True, triggers a cache refresh. Fresh data is fetched.
        :return: An Ansible pluggable dynamic inventory, as a Python json serializable dictionary.
        """
        if refresh:
            return self.list_and_save(filters, cache_path)
        else:
            if os.path.isfile(cache_path) and time() - os.stat(cache_path).st_mtime < cache_ttl:
                try:
                    with open(cache_path) as f:
                        data = load(f)
                        return data
                except (ValueError, IOError):
                    return self.list_and_save(filters, cache_path)
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
                return self.list_and_save(filters, cache_path)


def parse_config():
    """ Parse available configuration.
    Default configuration file: vsphere-inventory.ini
    Configuration file path may be overridden,
    by defining an environment variable: VSPHERE_INVENTORY_INI_PATH
    :return:(filters, cache_path, cache_ttl, vsphere_host, vsphere_user, vsphere_pass, vsphere_port, vsphere_cert_check)
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
    vsphere_port = config.getint('GENERIC', 'vsphere_port', fallback='')
    vsphere_cert_check = config.getboolean('GENERIC', 'vsphere_cert_check', fallback=True)
    filters = {}
    for name, value in config.items("INVENTORY_FILTERS"):
        if ',' in value:
            filters.update({name: [v.strip() for v in value.split(',')]} )
        else:
            filters.update({name: value})
    return filters, cache_path, cache_ttl, vsphere_host, vsphere_user, vsphere_pass, vsphere_port, vsphere_cert_check


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
    parser.add_argument('-s', '--hostname', help='vSphere vCenter FQDN')
    parser.add_argument('-u', '--username', help='vSphere username')
    parser.add_argument('-p', '--password', help='vSphere password')
    parser.add_argument('-P', '--port', help='vSphere Port')
    parser.add_argument('-c', '--no_cert_check', help='Dont check vSphere certificate', action='store_true')
    parser.add_argument('-g', '--guest', help='Print a single guest')
    parser.add_argument('-x', '--host', help='Print a single guest')
    parser.add_argument('-r', '--reload-cache', help='Reload cache', action='store_true')
    parser.add_argument('-l', '--list', help='List all VMs', action='store_true')

    return parser.parse_args()


def main():

    # - Get command line args and config args.
    args = get_args()
    (filters, cache_path, cache_ttl, vcenter_host, vsphere_user, vsphere_pass, vsphere_port, no_cert_check) \
        = parse_config()

    # - Override settings with arg parameters if defined
    if not args.password:
        if not vsphere_pass:
            import getpass
            vsphere_pass = getpass.getpass()
        setattr(args, 'password', vsphere_pass)
    if not args.username:
        setattr(args, 'username', vsphere_user)
    if not args.hostname:
        setattr(args, 'hostname', vcenter_host)
    if not args.port:
        setattr(args, 'port', vsphere_port)
    if not args.no_cert_check:
        setattr(args, 'no_cert_check', no_cert_check)
    if not args.no_cert_check:
        setattr(args, 'no_cert_check', no_cert_check)

    # - Perform requested operations (list, host/guest, reload cache)
    if args.host or args.guest:
        print ('{}')
        exit(0)
    elif args.list or args.reload_cache:
        v = VSphere(args.hostname, args.username, args.password, vsphere_port=443, nosslcheck=args.no_cert_check)
        data = v.cached_inventory(filters, cache_path=cache_path, cache_ttl=cache_ttl, refresh=args.reload_cache)
        print ("{}".format(dumps(data)))
        exit(0)

if __name__ == "__main__":
    main()
