# -*- coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2010-2011, GEM Foundation.
#
# OpenQuake is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# only, as published by the Free Software Foundation.
#
# OpenQuake is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License version 3 for more details
# (a copy is included in the LICENSE file that accompanied this code).
#
# You should have received a copy of the GNU Lesser General Public License
# version 3 along with OpenQuake.  If not, see
# <http://www.gnu.org/licenses/lgpl-3.0.txt> for a copy of the LGPLv3 License.


import os
import unittest

from db.alchemy.db_utils import get_uiapi_writer_session
from openquake.output.risk import LossCurveDBWriter, LossMapDBWriter
from openquake.shapes import Site, Curve

from db_tests import helpers

# The data below was captured (and subsequently modified for testing purposes)
# by running
#
#   bin/openquake --config_file=smoketests/classical_psha_simple/config.gem
#
# and putting a breakpoint in openquake/output/risk.py:CurveXMLWriter.write()
RISK_LOSS_CURVE_DATA = [
    (Site(-118.077721, 33.852034),
     (Curve([(3.18e-06, 1.0), (8.81e-06, 1.0), (1.44e-05, 1.0),
             (2.00e-05, 1.0)]),
      {u'assetValue': 5.07, u'assetID': u'a5625',
       u'listDescription': u'Collection of exposure values for ...',
       u'structureCategory': u'RM1L', u'lon': -118.077721,
       u'assetDescription': u'LA building',
       u'vulnerabilityFunctionReference': u'HAZUS_RM1L_LC',
       u'listID': u'LA01', u'assetValueUnit': None, u'lat': 33.852034})),

    (Site(-118.077721, 33.852034),
     (Curve([(7.18e-06, 1.0), (1.91e-05, 1.0), (3.12e-05, 1.0),
             (4.32e-05, 1.0)]),
     {u'assetValue': 5.63, u'assetID': u'a5629',
      u'listDescription': u'Collection of exposure values for ...',
      u'structureCategory': u'URML',
      u'lon': -118.077721, u'assetDescription': u'LA building',
      u'vulnerabilityFunctionReference': u'HAZUS_URML_LC',
      u'listID': u'LA01', u'assetValueUnit': None, u'lat': 33.852034})),

    (Site(-118.077721, 33.852034),
     (Curve([(5.48e-06, 1.0), (1.45e-05, 1.0), (2.36e-05, 1.0),
             (3.27e-05, 1.0)]),
     {u'assetValue': 11.26, u'assetID': u'a5630',
      u'listDescription': u'Collection of exposure values for ...',
      u'structureCategory': u'URML', u'lon': -118.077721,
      u'assetDescription': u'LA building',
      u'vulnerabilityFunctionReference': u'HAZUS_URML_LS',
      u'listID': u'LA01', u'assetValueUnit': None, u'lat': 33.852034})),

    (Site(-118.077721, 33.852034),
     (Curve([(9.77e-06, 1.0), (2.64e-05, 1.0), (4.31e-05, 1.0),
             (5.98e-05, 1.0)]),
     {u'assetValue': 5.5, u'assetID': u'a5636',
      u'listDescription': u'Collection of exposure values for ...',
      u'structureCategory': u'C3L', u'lon': -118.077721,
      u'assetDescription': u'LA building',
      u'vulnerabilityFunctionReference': u'HAZUS_C3L_MC',
      u'listID': u'LA01', u'assetValueUnit': None, u'lat': 33.852034})),
]


class LossCurveDBWriterTestCase(unittest.TestCase, helpers.DbTestMixin):
    """
    Unit tests for the LossCurveDBWriter class, which serializes
    loss curves to the database.
    """
    def tearDown(self):
        if hasattr(self, "job") and self.job:
            self.teardown_job(self.job)
        if hasattr(self, "output") and self.output:
            self.teardown_output(self.output)

    def setUp(self):
        self.job = self.setup_classic_job()
        self.session = get_uiapi_writer_session()
        output_path = self.generate_output_path(self.job)
        self.display_name = os.path.basename(output_path)

        self.writer = LossCurveDBWriter(self.session, output_path, self.job.id)

    def test_insert(self):
        """All the records are inserted correctly."""
        output = self.writer.output

        # Call the function under test.
        data = RISK_LOSS_CURVE_DATA
        self.writer.serialize(data)

        # After calling the function under test we see the expected output.
        self.assertEqual(1, len(self.job.output_set))

        # Make sure the inserted output record has the right data.
        [output] = self.job.output_set
        self.assertTrue(output.db_backed)
        self.assertTrue(output.path is None)
        self.assertEqual(self.display_name, output.display_name)
        self.assertEqual("loss_curve", output.output_type)
        self.assertTrue(self.job is output.oq_job)

        # After calling the function under test we see the expected loss asset
        # data.
        self.assertEqual(4, len(output.lossassetdata_set))

        inserted_data = []

        for lad in output.lossassetdata_set:
            pos = lad.pos.coords(self.session)

            for curve in lad.losscurvedata_set:
                data = (Site(pos[0], pos[1]),
                        (Curve(zip(curve.abscissae, curve.poes)),
                        {u'assetID': lad.asset_id}))

                inserted_data.append(data)

        def normalize(values):
            result = []
            for value in values:
                result.append((value[0],
                               (value[1][0],
                                {'assetID': value[1][1]['assetID']})))

            return sorted(result, key=lambda v: v[1][1]['assetID'])

        self.assertEquals(normalize(RISK_LOSS_CURVE_DATA),
                          normalize(inserted_data))


SITE_A = Site(-117.0, 38.0)
SITE_A_ASSET_ONE = {'assetID': 'a1711'}
SITE_A_ASSET_TWO = {'assetID': 'a1712'}

SITE_B = Site(-118.0, 39.0)
SITE_B_ASSET_ONE = {'assetID': 'a1713'}

LOSS_MAP_METADATA = {
    'nrmlID': 'test_nrml_id',
    'riskResultID': 'test_rr_id',
    'lossMapID': 'test_lm_id',
    'endBranchLabel': 'test_ebl',
    'lossCategory': 'economic_loss',
    'unit': 'EUR'}

DETERMINISTIC_LOSS_MAP_METADATA = LOSS_MAP_METADATA.copy()
DETERMINISTIC_LOSS_MAP_METADATA.update({
    'deterministic': True})

SITE_A_DETERMINISTIC_LOSS_ONE = {'mean_loss': 0, 'stddev_loss': 100}
SITE_A_DETERMINISTIC_LOSS_TWO = {'mean_loss': 5, 'stddev_loss': 2000.0}

SITE_B_DETERMINISTIC_LOSS_ONE = {'mean_loss': 120000.0, 'stddev_loss': 2000.0}

SAMPLE_DETERMINISTIC_LOSS_MAP_DATA = [
    DETERMINISTIC_LOSS_MAP_METADATA,
    (SITE_A, [(SITE_A_DETERMINISTIC_LOSS_ONE, SITE_A_ASSET_ONE),
    (SITE_A_DETERMINISTIC_LOSS_TWO, SITE_A_ASSET_TWO)]),
    (SITE_B, [(SITE_B_DETERMINISTIC_LOSS_ONE, SITE_B_ASSET_ONE)])]

NONDETERMINISTIC_LOSS_MAP_METADATA = LOSS_MAP_METADATA.copy()
NONDETERMINISTIC_LOSS_MAP_METADATA.update({
    'poe': 0.6,
    'deterministic': False})

SITE_A_NONDETERMINISTIC_LOSS_ONE = {'value': 12}
SITE_A_NONDETERMINISTIC_LOSS_TWO = {'value': 66}

SITE_B_NONDETERMINISTIC_LOSS_ONE = {'value': 1000.0}

SAMPLE_NONDETERMINISTIC_LOSS_MAP_DATA = [
    NONDETERMINISTIC_LOSS_MAP_METADATA,
    (SITE_A, [(SITE_A_NONDETERMINISTIC_LOSS_ONE, SITE_A_ASSET_ONE),
    (SITE_A_NONDETERMINISTIC_LOSS_TWO, SITE_A_ASSET_TWO)]),
    (SITE_B, [(SITE_B_NONDETERMINISTIC_LOSS_ONE, SITE_B_ASSET_ONE)])]


class LossMapDBWriterTestCase(unittest.TestCase, helpers.DbTestMixin):
    """
    Unit tests for the LossMapDBWriter class, which serializes
    loss maps to the database.
    """
    def tearDown(self):
        if hasattr(self, "job") and self.job:
            self.teardown_job(self.job)
        if hasattr(self, "output") and self.output:
            self.teardown_output(self.output)

    def setUp(self):
        self.job = self.setup_classic_job()
        self.session = get_uiapi_writer_session()
        output_path = self.generate_output_path(self.job)
        self.display_name = os.path.basename(output_path)

        self.writer = LossMapDBWriter(self.session, output_path, self.job.id)

    def test_serialize_deterministic(self):
        """
        All the records for deterministic loss maps are inserted correctly.
        """

        output = self.writer.output

        # Call the function under test.
        data = SAMPLE_DETERMINISTIC_LOSS_MAP_DATA
        self.writer.serialize(data)

        # Output record
        self.assertEqual(1, len(self.job.output_set))
        [output] = self.job.output_set
        self.assertTrue(output.db_backed)
        self.assertTrue(output.path is None)
        self.assertEqual(self.display_name, output.display_name)
        self.assertEqual("loss_map", output.output_type)
        self.assertTrue(self.job is output.oq_job)

        # LossMap record
        self.assertEqual(1, len(output.lossmap_set))
        [metadata] = output.lossmap_set
        self.assertEqual(DETERMINISTIC_LOSS_MAP_METADATA['deterministic'],
                         metadata.deterministic)
        self.assertEqual(DETERMINISTIC_LOSS_MAP_METADATA['endBranchLabel'],
                         metadata.end_branch_label)
        self.assertEqual(DETERMINISTIC_LOSS_MAP_METADATA['lossCategory'],
                         metadata.category)
        self.assertEqual(DETERMINISTIC_LOSS_MAP_METADATA['unit'],
                         metadata.unit)
        self.assertEqual(None, metadata.poe)

        # LossMapData records
        self.assertEqual(3, len(metadata.lossmapdata_set))
        [data_a, data_b, data_c] = metadata.lossmapdata_set

        self.assertEqual(SITE_A, Site(*data_a.location.coords(self.session)))
        self.assertEqual(SITE_A_ASSET_ONE['assetID'], data_a.asset_ref)
        self.assertEqual(SITE_A_DETERMINISTIC_LOSS_ONE['mean_loss'],
                        data_a.value)
        self.assertEqual(SITE_A_DETERMINISTIC_LOSS_ONE['stddev_loss'],
                         data_a.std_dev)

        self.assertEqual(SITE_A, Site(*data_b.location.coords(self.session)))
        self.assertEqual(SITE_A_ASSET_TWO['assetID'], data_b.asset_ref)
        self.assertEqual(SITE_A_DETERMINISTIC_LOSS_TWO['mean_loss'],
                         data_b.value)
        self.assertEqual(SITE_A_DETERMINISTIC_LOSS_TWO['stddev_loss'],
                         data_b.std_dev)

        self.assertEqual(SITE_B, Site(*data_c.location.coords(self.session)))
        self.assertEqual(SITE_B_ASSET_ONE['assetID'], data_c.asset_ref)
        self.assertEqual(SITE_B_DETERMINISTIC_LOSS_ONE['mean_loss'],
                         data_c.value)
        self.assertEqual(SITE_B_DETERMINISTIC_LOSS_ONE['stddev_loss'],
                         data_c.std_dev)

    def test_serialize_nondeterministic(self):
        """
        All the records for non-deterministic loss maps are inserted correctly.
        """

        output = self.writer.output

        # Call the function under test.
        data = SAMPLE_NONDETERMINISTIC_LOSS_MAP_DATA
        self.writer.serialize(data)

        # Output record
        self.assertEqual(1, len(self.job.output_set))
        [output] = self.job.output_set
        self.assertTrue(output.db_backed)
        self.assertTrue(output.path is None)
        self.assertEqual(self.display_name, output.display_name)
        self.assertEqual("loss_map", output.output_type)
        self.assertTrue(self.job is output.oq_job)

        # LossMap record
        self.assertEqual(1, len(output.lossmap_set))
        [metadata] = output.lossmap_set
        self.assertEqual(NONDETERMINISTIC_LOSS_MAP_METADATA['deterministic'],
                         metadata.deterministic)
        self.assertEqual(NONDETERMINISTIC_LOSS_MAP_METADATA['endBranchLabel'],
                         metadata.end_branch_label)
        self.assertEqual(NONDETERMINISTIC_LOSS_MAP_METADATA['lossCategory'],
                         metadata.category)
        self.assertEqual(NONDETERMINISTIC_LOSS_MAP_METADATA['unit'],
                         metadata.unit)
        self.assertEqual(NONDETERMINISTIC_LOSS_MAP_METADATA['poe'],
                         metadata.poe)

        # LossMapData records
        self.assertEqual(3, len(metadata.lossmapdata_set))
        [data_a, data_b, data_c] = metadata.lossmapdata_set

        self.assertEqual(SITE_A, Site(*data_a.location.coords(self.session)))
        self.assertEqual(SITE_A_ASSET_ONE['assetID'], data_a.asset_ref)
        self.assertEqual(SITE_A_NONDETERMINISTIC_LOSS_ONE['value'],
                         data_a.value)

        self.assertEqual(SITE_A, Site(*data_b.location.coords(self.session)))
        self.assertEqual(SITE_A_ASSET_TWO['assetID'], data_b.asset_ref)
        self.assertEqual(SITE_A_NONDETERMINISTIC_LOSS_TWO['value'],
                         data_b.value)

        self.assertEqual(SITE_B, Site(*data_c.location.coords(self.session)))
        self.assertEqual(SITE_B_ASSET_ONE['assetID'], data_c.asset_ref)
        self.assertEqual(SITE_B_NONDETERMINISTIC_LOSS_ONE['value'],
                         data_c.value)