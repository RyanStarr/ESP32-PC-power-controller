import time
from influxdb_client import InfluxDBClient
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from datetime import datetime
import os

# Load .env file
load_dotenv()

# InfluxDB details
INFLUXDB_URL = os.getenv("INFLUXDB_URL")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

# MQTT details
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC")

# Voltage settings
VOLTAGE_OFF_THRESHOLD = float(os.getenv("VOLTAGE_OFF_THRESHOLD"))
VOLTAGE_ON_THRESHOLD = float(os.getenv("VOLTAGE_ON_THRESHOLD"))

#Query influxDB for the latest battery voltage
def get_battery_voltage():
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -30d)
          |> filter(fn: (r) => r._measurement == "charge_controller" and r._field == "battery_voltage")
          |> last()
        '''
        result = client.query_api().query(org=INFLUXDB_ORG, query=query)
        client.close()
        
        if result and result[0].records:
            return result[0].records[0].get_value()
    except Exception as e:
        print(f"Error querying InfluxDB: {e}")
    return None

#Send MQTT command to control PC
def control_pc(voltage, mqtt_client):
    try:
        print(f"Battery voltage: {voltage}")
        if voltage < VOLTAGE_OFF_THRESHOLD:
            mqtt_client.publish(MQTT_TOPIC, "turn_off")
            print("PC turned off due to low battery voltage.")
        elif voltage > VOLTAGE_ON_THRESHOLD:
            mqtt_client.publish(MQTT_TOPIC, "turn_on")
            print("PC turned on due to sufficient battery voltage.")
    except Exception as e:
        print(f"Error controlling PC: {e}")

#Check MQTT connection
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print(f"Failed to connect, return code {rc}")

#Send command via MQTT
def on_publish(client, userdata, mid, properties=None, reasonCode=None):
    print(f"Message published: {mid}")

#Connect to MQTT and begin battery voltage check
def main():
    try:
        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        mqtt_client.on_connect = on_connect
        mqtt_client.on_publish = on_publish
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()

        last_successful_time = time.time()

        while True:
            voltage = get_battery_voltage()
            current_time = time.time()
            if voltage is not None:
                control_pc(voltage, mqtt_client)
                last_successful_time = current_time
            else:
                print("Failed to retrieve battery voltage.")
                print(f"Last successful time {datetime.fromtimestamp(last_successful_time).strftime('%Y-%m-%d %H:%M:%S')}")
                # If no data is received from InfluxDB for 1 hour then turn off the PC
                if current_time - last_successful_time > 3600:
                    mqtt_client.publish(MQTT_TOPIC, "turn_off")
                    print("PC turned off due to no data received from InfluxDB within an hour.")
            time.sleep(300)  # Check every 5 minutes
            
    except Exception as e:
        print(f"Error in main loop: {e}")

if __name__ == "__main__":
    main()