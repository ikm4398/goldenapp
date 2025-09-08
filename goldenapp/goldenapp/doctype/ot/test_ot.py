# Copyright (c) 2025, ik and Contributors
# See license.txt

# import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase


# On IntegrationTestCase, the doctype test records and all
# link-field test record depdendencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class UnitTestOT(UnitTestCase):
	"""
	Unit tests for OT.
	Use this class for testing individual functions and methods.
	"""

	pass


class IntegrationTestOT(IntegrationTestCase):
	"""
	Integration tests for OT.
	Use this class for testing interactions between multiple components.
	"""

	pass
