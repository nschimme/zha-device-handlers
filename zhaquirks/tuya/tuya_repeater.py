"""Tuya Zigbee repeater."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Groups, OnOff, Scenes
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZ3000_wn65ixz9", "TS0001")
    .tuya_enchantment()
    .removes(OnOff.cluster_id)
    .removes(Metering.cluster_id)
    .removes(ElectricalMeasurement.cluster_id)
    .removes(Groups.cluster_id)
    .removes(Scenes.cluster_id)
    .removes(0xE001)
    .removes(0xFC11)
    .replaces_endpoint(1, device_type=zha.DeviceType.RANGE_EXTENDER)
    .add_to_registry()
)
