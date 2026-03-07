
import pytest
from zigpy.zcl import foundation
from zhaquirks.tuya import TuyaCommand, TuyaDatapointData, TuyaData, TuyaDPType
from zhaquirks.tuya.mcu import TuyaMCUCluster
import zhaquirks

zhaquirks.setup()

@pytest.mark.asyncio
async def test_hobeian_zg303z_moisture_logic(zigpy_device_from_v2_quirk):
    """Test that ZG-303Z moisture binary sensor follows calculated logic."""
    quirked = zigpy_device_from_v2_quirk("_TZE200_npj9bug3", "TS0601")
    ep1 = quirked.endpoints[1]
    tuya_cluster = ep1.tuya_manufacturer

    def send_dp_update(dp, dp_type, value):
        data = TuyaData()
        data.dp_type = dp_type
        data.payload = value

        cmd = TuyaCommand(
            status=0,
            tsn=1,
            datapoints=[TuyaDatapointData(dp=dp, data=data)]
        )
        tuya_cluster.handle_get_data(cmd)

    # 1. Initial state
    send_dp_update(3, TuyaDPType.VALUE, 15) # 15% moisture
    send_dp_update(110, TuyaDPType.VALUE, 25) # 25% threshold

    # Calculation: 15 < 25 -> Moisture False (Dry)
    assert ep1.tuya_manufacturer.get("moisture") == False

    # 2. Moisture above threshold
    send_dp_update(3, TuyaDPType.VALUE, 30) # 30% moisture
    # Calculation: 30 >= 25 -> Moisture True (Wet)
    assert ep1.tuya_manufacturer.get("moisture") == True

    # 3. Lower threshold below moisture
    send_dp_update(110, TuyaDPType.VALUE, 10) # 10% threshold
    send_dp_update(3, TuyaDPType.VALUE, 15) # 15% moisture
    # Calculation: 15 >= 10 -> Moisture True (Wet)
    assert ep1.tuya_manufacturer.get("moisture") == True

    # 4. Verify DP 106 is ignored
    # Currently 15% >= 10% -> Wet (True)
    # Hardware alarm DP 106 = 1 (Dry)
    send_dp_update(106, TuyaDPType.ENUM, 1)
    # Should still be Wet (True) because DP 106 is ignored
    assert ep1.tuya_manufacturer.get("moisture") == True

    # Change moisture to 5% (below 10% threshold)
    send_dp_update(3, TuyaDPType.VALUE, 5)
    # Calculation: 5 < 10 -> Moisture False (Dry)
    assert ep1.tuya_manufacturer.get("moisture") == False
