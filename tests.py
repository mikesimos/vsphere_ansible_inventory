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

import unittest


class VSphereAnsibleTestCase(unittest.TestCase):

    def test_list_inventory(self):
        from vsphere_inventory import VSphere
        self.assertTrue(getattr(VSphere, 'list_inventory'))
        self.assertTrue(callable(getattr(VSphere, 'list_inventory')))

    def test_append_vm_info(self):
        from vsphere_inventory import VSphere
        self.assertTrue(hasattr(VSphere, 'append_vm_info'))
        self.assertTrue(callable(getattr(VSphere, 'append_vm_info')))

    def test_filter_inventory(self):
        from vsphere_inventory import VSphere
        self.assertTrue(hasattr(VSphere, 'filter_inventory'))
        self.assertTrue(callable(getattr(VSphere, 'filter_inventory')))

    def test_grouped_inventory(self):
        from vsphere_inventory import VSphere
        self.assertTrue(hasattr(VSphere, 'grouped_inventory'))
        self.assertTrue(callable(getattr(VSphere, 'grouped_inventory')))

    def test_list_and_save(self):
        from vsphere_inventory import VSphere
        self.assertTrue(hasattr(VSphere, 'list_and_save'))
        self.assertTrue(callable(getattr(VSphere, 'list_and_save')))

    def test_cached_inventory(self):
        from vsphere_inventory import VSphere
        self.assertTrue(hasattr(VSphere, 'cached_inventory'))
        self.assertTrue(callable(getattr(VSphere, 'cached_inventory')))


if __name__ == '__main__':
    unittest.main()
