
from zigpy.zcl.clusters.measurement import RelativeHumidity, SoilMoisture, TemperatureMeasurement, PressureMeasurement, IlluminanceMeasurement

clusters = [RelativeHumidity, SoilMoisture, TemperatureMeasurement, PressureMeasurement, IlluminanceMeasurement]
for c in clusters:
    print(f"Cluster: {c.__name__}, ID: {c.cluster_id:#04x}, ep_attribute: {c.ep_attribute}")
