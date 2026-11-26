"""Tests for Tuya Sensor quirks."""

from unittest import mock

import pytest
import zigpy.profiles.zha
import zigpy.types
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Basic, PowerConfiguration
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

from tests.common import wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya import TuyaCommand, TuyaData, TuyaDatapointData, TuyaLocalCluster
from zhaquirks.tuya.mcu import TuyaMCUCluster

# Temp DP 1, Humidity DP 2, Battery DP 3
TUYA_TEMP01_HUM02_BAT03 = b"\x09\xe0\x02\x0b\x33\x01\x02\x00\x04\x00\x00\x00\xfd\x02\x02\x00\x04\x00\x00\x00\x47\x03\x02\x00\x04\x00\x00\x00\x01"
# Temp DP 1, Humidity DP 2, Battery DP 4
TUYA_TEMP01_HUM02_BAT04 = b"\x09\xe0\x02\x0b\x33\x01\x02\x00\x04\x00\x00\x00\xfd\x02\x02\x00\x04\x00\x00\x00\x47\x04\x02\x00\x04\x00\x00\x00\x01"
TUYA_USP = b"\x09\xe0\x02\x0b\x33\x01\x02\x00\x04\x00\x00\x00\xfd\x02\x02\x00\x04\x00\x00\x00\x47\xff\x02\x00\x04\x00\x00\x00\x64"

ZCL_TUYA_VERSION_RSP = b"\x09\x06\x11\x01\x6d\x82"

zhaquirks.setup()


@pytest.mark.parametrize(
    "model,manuf,rh_scale,temp_scale,test_neg",
    [
        ("_TZE200_bjawzodf", "TS0601", 10, 10, True),
        ("_TZE200_zl1kmjqx", "TS0601", 10, 10, True),
        ("_TZE200_a8sdabtg", "TS0601", 100, 10, False),  # Variant without screen, round
        ("_TZE200_qoy0ekbd", "TS0601", 100, 10, False),
        ("_TZE200_znbl8dj5", "TS0601", 100, 10, False),
        ("_TZE200_qyflbnbj", "TS0601", 100, 10, True),
        ("_TZE200_zppcgbdj", "TS0601", 100, 10, False),
        ("_TZE200_s1xgth2u", "TS0601", 100, 10, False),
        ("_TZE284_qyflbnbj", "TS0601", 100, 10, True),
        ("_TZE204_s139roas", "TS0601", 100, 10, False),
        ("_TZE200_bq5c8xfe", "TS0601", 100, 10, True),
        ("_TZE200_vs0skpuc", "TS0601", 100, 10, True),
        ("_TZE200_44af8vyi", "TS0601", 100, 10, True),
        ("_TZE200_lve3dvpy", "TS0601", 100, 10, False),  # TH01Z - Temp & humid w/ clock
        ("_TZE200_c7emyjom", "TS0601", 100, 10, False),
        ("_TZE200_locansqn", "TS0601", 100, 10, False),
        ("_TZE200_qrztc3ev", "TS0601", 100, 10, False),
        ("_TZE200_snloy4rw", "TS0601", 100, 10, False),
        ("_TZE200_eanjj2pa", "TS0601", 100, 10, False),
        ("_TZE200_ydrdfkim", "TS0601", 100, 10, False),
        ("_TZE284_locansqn", "TS0601", 100, 10, False),
        ("_TZE200_vvmbj46n", "TS0601", 100, 10, False),
        ("_TZE284_9ern5sfh", "TS0601", 10, 10, True),
    ],
)
async def test_handle_get_data(
    zigpy_device_from_v2_quirk, model, manuf, rh_scale, temp_scale, test_neg
):
    """Test handle_get_data for multiple attributes - normal battery."""

    quirked = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked.endpoints[1]

    assert ep.basic is not None
    assert isinstance(ep.basic, Basic)

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    message = b"\x09\xe0\x02\x0b\x33\x01\x02\x00\x04\x00\x00\x00\xfd\x02\x02\x00\x04\x00\x00\x00\x47\x04\x02\x00\x04\x00\x00\x00\x64"
    hdr, data = ep.tuya_manufacturer.deserialize(message)

    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert (
        ep.temperature.get("measured_value")
        == data.data.datapoints[0].data.payload * temp_scale
    )

    assert (
        ep.humidity.get("measured_value")
        == data.data.datapoints[1].data.payload * rh_scale
    )

    assert (
        ep.power.get("battery_percentage_remaining")
        == data.data.datapoints[2].data.payload * 2
    )

    hdr, data = ep.tuya_manufacturer.deserialize(TUYA_USP)

    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.UNSUPPORTED_ATTRIBUTE

    if test_neg:
        message = b"\tH\x01\x00\xd8\x01\x02\x00\x04\x00\x00\xff\xe0"  # -3.1 deg c
        hdr, data = ep.tuya_manufacturer.deserialize(message)

        status = ep.tuya_manufacturer.handle_get_data(data.data)
        assert status == foundation.Status.SUCCESS

        assert ep.temperature.get("measured_value") == -310


@pytest.mark.parametrize(
    "model,manuf,rh_scale,temp_scale,state_rpt",
    [
        ("_TZE200_yjjdcqsq", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE204_yjjdcqsq", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE200_9yapgbuv", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE204_9yapgbuv", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE284_9yapgbuv", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE200_utkemkbs", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE204_utkemkbs", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE204_ksz749x8", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE200_upagmta9", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE204_upagmta9", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE200_cirvgep4", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE204_cirvgep4", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE204_jygvp6fk", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE284_upagmta9", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE204_1wnh8bqp", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE284_1wnh8bqp", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
    ],
)
async def test_handle_get_data_enum_batt(
    zigpy_device_from_v2_quirk, model, manuf, rh_scale, temp_scale, state_rpt
):
    """Test handle_get_data for multiple attributes - enum battery."""

    quirked = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked.endpoints[1]

    assert ep.basic is not None
    assert isinstance(ep.basic, Basic)

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    hdr, data = ep.tuya_manufacturer.deserialize(state_rpt)

    status = ep.tuya_manufacturer.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    assert (
        ep.temperature.get("measured_value")
        == data.data.datapoints[0].data.payload * temp_scale
    )

    assert (
        ep.humidity.get("measured_value")
        == data.data.datapoints[1].data.payload * rh_scale
    )

    assert ep.power.get("battery_percentage_remaining") == 100

    hdr, data = ep.tuya_manufacturer.deserialize(TUYA_USP)

    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.UNSUPPORTED_ATTRIBUTE


def test_valid_attributes(zigpy_device_from_v2_quirk):
    """Test that valid attributes on virtual clusters are populated by Tuya datapoints mappings."""
    quirked = zigpy_device_from_v2_quirk("_TZE200_bjawzodf", "TS0601")
    ep = quirked.endpoints[1]

    temperature_attr_id = TemperatureMeasurement.AttributeDefs.measured_value.id
    humidity_attr_id = RelativeHumidity.AttributeDefs.measured_value.id
    power_attr_id = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id

    temperature_cluster = ep.temperature
    humidity_cluster = ep.humidity
    power_config_cluster = ep.power

    assert isinstance(temperature_cluster, TuyaLocalCluster)
    assert isinstance(humidity_cluster, TuyaLocalCluster)
    assert isinstance(power_config_cluster, TuyaLocalCluster)

    # check that the virtual clusters have expected valid attributes
    assert {temperature_attr_id} == temperature_cluster._VALID_ATTRIBUTES
    assert {humidity_attr_id} == humidity_cluster._VALID_ATTRIBUTES
    assert {power_attr_id} == power_config_cluster._VALID_ATTRIBUTES


def _hobeian_soil_sensor(zigpy_device_from_v2_quirk):
    """Create the ZG-303Z soil sensor with the clusters of the real device."""
    return zigpy_device_from_v2_quirk(
        "_TZE200_npj9bug3",
        "TS0601",
        cluster_ids={
            1: dict.fromkeys(
                (
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    TuyaMCUCluster.cluster_id,
                ),
                ClusterType.Server,
            )
        },
    )


def _datapoint(dp: int, value: int) -> TuyaCommand:
    return TuyaCommand(
        status=0, tsn=1, datapoints=[TuyaDatapointData(dp, TuyaData(value))]
    )


async def test_zg303z_air_humidity_is_not_overwritten_by_soil_moisture(
    zigpy_device_from_v2_quirk,
):
    """The device reports soil moisture in its own 0x0405 cluster on endpoint 1.

    Air humidity (DP 109) must therefore live on another endpoint.
    """
    quirked = _hobeian_soil_sensor(zigpy_device_from_v2_quirk)

    assert RelativeHumidity.cluster_id not in quirked.endpoints[1].in_clusters

    quirked.endpoints[1].tuya_manufacturer.handle_get_data(_datapoint(109, 53))
    quirked.endpoints[1].tuya_manufacturer.handle_get_data(_datapoint(3, 70))

    assert quirked.endpoints[2].humidity.get("measured_value") == 5300
    assert quirked.endpoints[1].soil_moisture.get("measured_value") == 7000


async def test_zg303z_resends_write_the_sleeping_device_missed(
    zigpy_device_from_v2_quirk,
):
    """A write is kept and sent again after the device has been heard."""
    quirked = _hobeian_soil_sensor(zigpy_device_from_v2_quirk)
    cluster = quirked.endpoints[1].tuya_manufacturer

    with (
        mock.patch.object(cluster, "command", new=mock.AsyncMock()) as command,
        mock.patch("zhaquirks.tuya.tuya_sensor.time.monotonic", return_value=1000),
    ):
        await cluster.write_attributes({"alarm_soil_moisture_min": 0})
        await wait_for_zigpy_tasks()
        assert command.await_count == 1

        # The device reports something else, and still has the old value
        cluster.handle_get_data(_datapoint(5, 250))
        cluster.handle_get_data(_datapoint(110, 20))
        await wait_for_zigpy_tasks()
        assert command.await_count == 2
        sent = command.await_args.args[1].datapoints[0]
        assert (sent.dp, sent.data.payload) == (110, 0)

        # The old value does not replace the one that was written
        assert cluster.get("alarm_soil_moisture_min") == 0

        # The device confirms the write: nothing is sent again
        cluster.handle_set_data_response(_datapoint(110, 0))
        cluster.handle_get_data(_datapoint(5, 251))
        await wait_for_zigpy_tasks()
        assert command.await_count == 2
        assert cluster.get("alarm_soil_moisture_min") == 0


async def test_zg303z_resend_is_limited(zigpy_device_from_v2_quirk):
    """A write the device never confirms is dropped after a few attempts."""
    quirked = _hobeian_soil_sensor(zigpy_device_from_v2_quirk)
    cluster = quirked.endpoints[1].tuya_manufacturer

    with (
        mock.patch.object(cluster, "command", new=mock.AsyncMock()) as command,
        mock.patch("zhaquirks.tuya.tuya_sensor.time.monotonic") as monotonic,
    ):
        await cluster.write_attributes({"alarm_soil_moisture_min": 5})
        await wait_for_zigpy_tasks()

        for wake in range(1, 30):
            monotonic.return_value = wake * 60
            cluster.handle_get_data(_datapoint(5, 250))
            await wait_for_zigpy_tasks()

    assert command.await_count == cluster.MAX_ATTEMPTS


async def test_zg303z_resends_write_after_any_frame_from_the_device(
    zigpy_device_from_v2_quirk,
):
    """The device does not always report datapoints, any frame shows it is awake."""
    quirked = _hobeian_soil_sensor(zigpy_device_from_v2_quirk)
    cluster = quirked.endpoints[1].tuya_manufacturer

    with (
        mock.patch.object(cluster, "command", new=mock.AsyncMock()) as command,
        mock.patch("zhaquirks.tuya.tuya_sensor.time.monotonic", return_value=1000),
    ):
        await cluster.write_attributes({"alarm_soil_moisture_min": 0})
        await wait_for_zigpy_tasks()
        assert command.await_count == 1

        # temperature report on the standard cluster
        quirked.packet_received(
            zigpy.types.ZigbeePacket(
                profile_id=zigpy.profiles.zha.PROFILE_ID,
                cluster_id=TemperatureMeasurement.cluster_id,
                src_ep=1,
                dst_ep=1,
                data=zigpy.types.SerializableBytes(b"\x18\x8c\x0a\x00\x00\x29\x22\x0b"),
                dst=zigpy.types.AddrModeAddress(
                    addr_mode=zigpy.types.AddrMode.NWK, address=quirked.nwk
                ),
            )
        )
        await wait_for_zigpy_tasks()

    assert command.await_count == 2
