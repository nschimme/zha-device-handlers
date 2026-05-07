"""Tests for Tuya TS0001 breaker quirk."""

import pytest
from zigpy.quirks.v2 import CustomDeviceV2
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

import zhaquirks
from zhaquirks.tuya import (
    ExternalSwitchType,
    PowerOnState,
    SwitchBackLight,
    TuyaZBExternalSwitchTypeCluster,
    TuyaZBOnOffAttributeCluster,
    BaseEnchantedDevice,
)

zhaquirks.setup()


async def test_tz3000_ywlexjqc_breaker(zigpy_device_from_v2_quirk):
    """Test the quirk for _TZ3000_ywlexjqc TS0001."""

    quirked = zigpy_device_from_v2_quirk("_TZ3000_ywlexjqc", "TS0001")

    assert isinstance(quirked, CustomDeviceV2)
    assert isinstance(quirked, BaseEnchantedDevice)
    assert quirked.tuya_spell_read_attributes is True

    ep = quirked.endpoints[1]

    # Check clusters
    assert isinstance(ep.on_off, TuyaZBOnOffAttributeCluster)
    assert ep.on_off.cluster_id == OnOff.cluster_id

    # Check that metering clusters are removed
    assert not hasattr(ep, "smartenergy_metering")
    assert Metering.cluster_id not in ep.in_clusters

    assert not hasattr(ep, "electrical_measurement")
    assert ElectricalMeasurement.cluster_id not in ep.in_clusters

    assert isinstance(ep.tuya_external_switch_type, TuyaZBExternalSwitchTypeCluster)

    # Check for 0xFC11 cluster
    assert 0xFC11 in ep.in_clusters

    # Check entities metadata
    exposes = quirked.exposes_metadata

    # Power-on behavior
    entities = exposes[(1, OnOff.cluster_id, 0)]  # 0 is ClusterType.Server
    entity = next(e for e in entities if e.attribute_name == "power_on_state")
    assert entity.enum == PowerOnState

    # External switch type
    entities_ext = exposes[(1, TuyaZBExternalSwitchTypeCluster.cluster_id, 0)]
    entity = next(e for e in entities_ext if e.attribute_name == "external_switch_type")
    assert entity.enum == ExternalSwitchType

    # Verify Backlight mode and Child lock are NOT present
    assert not any(e.attribute_name == "backlight_mode" for e in entities)
    assert not any(e.attribute_name == "child_lock" for e in entities)
