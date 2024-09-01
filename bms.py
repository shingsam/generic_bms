

import paho.mqtt.client as mqtt
import socket
import time
import yaml
import os
import json
import serial
import io
import json
import atexit
import sys
import constants
import itertools

print("Starting up...")

config = {}
script_version = ""

if os.path.exists('/data/options.json'):
    print("Loading options.json")
    with open(r'/data/options.json') as file:
        config = json.load(file)
        print("Config: " + json.dumps(config))

elif os.path.exists('config.yaml'):
    print("Loading config.yaml")
    with open(r'config.yaml') as file:
        config = yaml.load(file, Loader=yaml.FullLoader)['options']
        
else:
    sys.exit("No config file found")  


scan_interval = config['scan_interval']
connection_type = config['connection_type']
bms_serial = config['bms_serial']
ha_discovery_enabled = config['mqtt_ha_discovery']
code_running = True
bms_connected = False
mqtt_connected = False
print_initial = True
debug_output = config['debug_output']
disc_payload = {}
repub_discovery = 0

bms_version = ''
bms_sn = 'sn1'
pack_sn = ''
packs = 2
cells = 16
temps = 6


print("Connection Type: " + connection_type)

def on_connect(client, userdata, flags, rc):
    print("MQTT connected with result code "+str(rc))
    client.will_set(config['mqtt_base_topic'] + "/availability","offline", qos=0, retain=False)
    global mqtt_connected
    mqtt_connected = True

def on_disconnect(client, userdata, rc):
    print("MQTT disconnected with result code "+str(rc))
    global mqtt_connected
    mqtt_connected = False


client = mqtt.Client("bmspace")
client.on_connect = on_connect
client.on_disconnect = on_disconnect
#client.on_message = on_message

client.username_pw_set(username=config['mqtt_user'], password=config['mqtt_password'])
client.connect(config['mqtt_host'], config['mqtt_port'], 60)
client.loop_start()
time.sleep(2)

def exit_handler():
    print("Script exiting")
    client.publish(config['mqtt_base_topic'] + "/availability","offline")
    return

atexit.register(exit_handler)

def bms_connect(address, port):

    if connection_type == "Serial":

        try:
            print("trying to connect %s" % bms_serial)
            s = serial.Serial(bms_serial,timeout = 1)
            print("BMS serial connected")
            return s, True
        except IOError as msg:
            print("BMS serial error connecting: %s" % msg)
            return False, False    

    else:

        try:
            print("trying to connect " + address + ":" + str(port))
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((address, port))
            print("BMS socket connected")
            return s, True
        except OSError as msg:
            print("BMS socket error connecting: %s" % msg)
            return False, False

def bms_sendData(comms,request=''):

    if connection_type == "Serial":

        try:
            if len(request) > 0:
                comms.write(request)
                time.sleep(0.25)
                return True
        except IOError as e:
            print("BMS serial error: %s" % e)
            # global bms_connected
            return False

    else:

        try:
            if len(request) > 0:
                comms.send(request)
                time.sleep(0.25)
                return True
        except Exception as e:
            print("BMS socket error: %s" % e)
            # global bms_connected
            return False

def bms_get_data(comms):
    try:
        if connection_type == "Serial":
            inc_data = comms.read(4096)
        else:
            temp = bytes()
            
            while len(temp) == 0 or temp[-1] != 13:
                temp = temp + comms.recv(4096)

            temp2 = temp.split(b'\r')
            # Decide which one to take:
            for element in range(0,len(temp2)):
                SOI = hex(ord(temp2[element][0:1]))
                if SOI == '0x7e':
                    inc_data = temp2[element] + b'\r'
                    break

            if (len(temp2) > 2) & (debug_output > 0):
                print("Multiple EOIs detected")
                print("...for incoming data: " + str(temp) + " |Hex: " + str(temp.hex(' ')))
                
        return inc_data
    except Exception as e:
        print("BMS socket receive error: %s" % e)
        # global bms_connected
        return False

def ha_discovery():

    global ha_discovery_enabled
    global packs

    if ha_discovery_enabled:
        
        print("Publishing HA Discovery topic...")

        disc_payload['availability_topic'] = config['mqtt_base_topic'] + "/availability"

        device = {}
        device['manufacturer'] = "BMS Pace"
        device['model'] = "STD1-T4"
        device['identifiers'] = "bmspace_" + bms_sn
        device['name'] = "LIFePO"
        device['sw_version'] = bms_version
        disc_payload['device'] = device

        for p in range (1,packs+1):

            for i in range(0,cells):
                disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Cell " + str(i+1).zfill(config['zero_pad_number_cells']) + " Voltage"
                disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_v_cell_" + str(i+1).zfill(config['zero_pad_number_cells'])
                disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/v_cells/cell_" + str(i+1).zfill(config['zero_pad_number_cells'])
                disc_payload['unit_of_measurement'] = "mV"
                client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            for i in range(0,temps):
                disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Temperature " + str(i+1)
                disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_temp_" + str(i+1)
                disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/temps/temp_" + str(i+1)
                disc_payload['unit_of_measurement'] = "°C"
                client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " MOS_Temp"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_t_mos"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/t_mos"
            disc_payload['unit_of_measurement'] = "°C"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Environmental_Temp"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_t_env"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/t_env"
            disc_payload['unit_of_measurement'] = "°C"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Current"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_i_pack"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/i_pack"
            disc_payload['unit_of_measurement'] = "A"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Voltage"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_v_pack"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/v_pack"
            disc_payload['unit_of_measurement'] = "V"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Remaining Capacity"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_i_remain_cap"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/i_remain_cap"
            disc_payload['unit_of_measurement'] = "mAh"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " State of Health"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_soh"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/soh"
            disc_payload['unit_of_measurement'] = "%"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Cycles"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_cycles"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/cycles"
            disc_payload['unit_of_measurement'] = ""
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Full Capacity"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_i_full_cap"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/i_full_cap"
            disc_payload['unit_of_measurement'] = "mAh"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " State of Charge"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_soc"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/soc"
            disc_payload['unit_of_measurement'] = "%"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " State of Health"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_soh"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/soh"
            disc_payload['unit_of_measurement'] = "%"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)


            disc_payload.pop('unit_of_measurement')

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Warnings"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_warnings"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/warnings"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Balancing"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_balancing"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/balancing"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            # Binary Sensors
            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Current Limit"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_current_limit"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/current_limit"
            disc_payload['payload_on'] = "1"
            disc_payload['payload_off'] = "0"
            client.publish(config['mqtt_ha_discovery_topic']+"/binary_sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Charge FET"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_charge_fet"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/charge_fet"
            disc_payload['payload_on'] = "1"
            disc_payload['payload_off'] = "0"
            client.publish(config['mqtt_ha_discovery_topic']+"/binary_sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Discharge FET"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_discharge_fet"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/discharge_fet"
            disc_payload['payload_on'] = "1"
            disc_payload['payload_off'] = "0"
            client.publish(config['mqtt_ha_discovery_topic']+"/binary_sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Charging"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_charging"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/charging"
            disc_payload['payload_on'] = "1"
            disc_payload['payload_off'] = "0"
            client.publish(config['mqtt_ha_discovery_topic']+"/binary_sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Discharging"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_discharging"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/discharging"
            disc_payload['payload_on'] = "1"
            disc_payload['payload_off'] = "0"
            client.publish(config['mqtt_ha_discovery_topic']+"/binary_sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)


            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Heating"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_heating"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/heating"
            disc_payload['payload_on'] = "1"
            disc_payload['payload_off'] = "0"
            client.publish(config['mqtt_ha_discovery_topic']+"/binary_sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Cell Max Volt Diff"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_cells_max_diff_calc"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/cells_max_diff_calc"
            disc_payload['unit_of_measurement'] = "mV"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            # Pack data
            disc_payload.pop('payload_on')
            disc_payload.pop('payload_off')

            disc_payload['name'] = "Pack Remaining Capacity"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_i_remain_cap"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_remain_cap"
            disc_payload['unit_of_measurement'] = "mAh"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack Full Capacity"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_i_full_cap"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_full_cap"
            disc_payload['unit_of_measurement'] = "mAh"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack State of Charge"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_soc"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_soc"
            disc_payload['unit_of_measurement'] = "%"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack State of Health"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_soh"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_soh"
            disc_payload['unit_of_measurement'] = "%"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

    else:
        print("HA Discovery Disabled")

def chksum_calc(data):

    global debug_output
    chksum = 0

    try:

        for element in range(1, len(data)): #-5):
            chksum += (data[element])
        
        chksum = chksum % 65536
        chksum = '{0:016b}'.format(chksum)
    
        flip_bits = '' 
        for i in chksum:
            if i == '0':
                flip_bits += '1'
            else:
                flip_bits += '0'

        chksum = flip_bits
        chksum = int(chksum,2)+1

        chksum = format(chksum, 'X')

    except Exception as e:
        if debug_output > 0:
            print("Error calculating CHKSUM using data: " + data)
            print("Error details: ", str(e))
        return(False)

    return(chksum)

def cid2_rtn(rtn):

    # RTN Reponse codes, looking for errors
    if rtn == b'00':
        return False, False
    elif rtn == b'01':
        return True, "RTN Error 01: Undefined RTN error"
    elif rtn == b'02':
        return True, "RTN Error 02: CHKSUM error"
    elif rtn == b'03':
        return True, "RTN Error 03: LCHKSUM error"
    elif rtn == b'04':
        return True, "RTN Error 04: CID2 undefined"
    elif rtn == b'05':
        return True, "RTN Error 05: Undefined error"
    elif rtn == b'06':
        return True, "RTN Error 06: Undefined error"
    elif rtn == b'09':
        return True, "RTN Error 09: Operation or write error"
    else:
        return False, False

def bms_callback(adr, cid1, RTN, INFO):
    if len(INFO) < 4:
        return
    if RTN == b'85':
        return
    if (cid1 == b'4A'):
        p = int(adr, 16)
        bms_getAnalogData(INFO, p + 1)

def bms_parse_data(inc_data):

    global debug_output

    #inc_data = b'~25014600D0F40002100DD50DBC0DD70DD70DD40DD70DD20DD50DD30DD60DC10DD40DD50DD70DD30DD5060B760B710B700B7A0B7D0B9D0000DD2326A90226AC011126AC64100DD30DBD0DD40DC60DD50DD40DD50DD50DD60DD60DD40DD20DD30\r'

    try:
        
        SOI = hex(ord(inc_data[0:1]))
        if SOI != '0x7e':
            return(False,"Incorrect starting byte for incoming data")

        if debug_output > 1:
            print("SOI: ", SOI)
            print("VER: ", inc_data[1:3])
            print("ADR: ", inc_data[3:5])
            print("CID1 (Type): ", inc_data[5:7])

        RTN = inc_data[7:9]
        error, info = cid2_rtn(RTN)
        if error:
            print(error)
            raise Exception(error)
        
        LCHKSUM = inc_data[9]

        if debug_output > 1:
            print("RTN: ", RTN)
            print("LENGTH: ", inc_data[9:13])
            print(" - LCHKSUM: ", LCHKSUM)
            print(" - LENID: ", inc_data[10:13])

        LENID = int(inc_data[10:13],16) #amount of bytes, i.e. 2x hex

        calc_LCHKSUM = lchksum_calc(inc_data[10:13])
        if calc_LCHKSUM == False:
            return(False,"Error calculating LCHKSUM for incoming data")

        if LCHKSUM != ord(calc_LCHKSUM):
            if debug_output > 0:
                print("LCHKSUM received: " + str(LCHKSUM) + " does not match calculated: " + str(ord(calc_LCHKSUM)))
            return(False,"LCHKSUM received: " + str(LCHKSUM) + " does not match calculated: " + str(ord(calc_LCHKSUM)))

        if debug_output > 1:
            print(" - LENID (int): ", LENID)

        INFO = inc_data[13:13+LENID]

        if debug_output > 1:
            print("INFO: ", INFO)

        CHKSUM = inc_data[13+LENID:13+LENID+4]

        if debug_output > 1:
            print("CHKSUM: ", CHKSUM)
            #print("EOI: ", hex(inc_data[13+LENID+4]))

        calc_CHKSUM = chksum_calc(inc_data[:len(inc_data)-5])
        CHKSUM_decoded = CHKSUM.decode("ASCII")

        if debug_output > 1:
            print("Calc CHKSUM: ", calc_CHKSUM)
    except Exception as e:
        if debug_output > 0:
            print("Error1 calculating CHKSUM using data: ", inc_data)
        return(False,"Error1 calculating CHKSUM: " + str(e))

    if calc_CHKSUM == False:
        if debug_output > 0:
            print("Error2 calculating CHKSUM using data: ", inc_data)
        return(False,"Error2 calculating CHKSUM")

    if CHKSUM_decoded == calc_CHKSUM:
        bms_callback(inc_data[3:5], inc_data[5:7], RTN, INFO)
        return(True, INFO)
    else:
        if debug_output > 0:
            print("Received and calculated CHKSUM does not match: Received: " + CHKSUM.decode("ASCII") + ", Calculated: " + calc_CHKSUM)
            print("...for incoming data: " + str(inc_data) + " |Hex: " + str(inc_data.hex(' ')))
            print("Length of incoming data as measured: " + str(len(inc_data)))
            print("SOI: ", SOI)
            print("VER: ", inc_data[1:3])
            print("ADR: ", inc_data[3:5])
            print("CID1 (Type): ", inc_data[5:7])
            print("RTN (decode!): ", RTN)
            print("LENGTH: ", inc_data[9:13])
            print(" - LCHKSUM: ", inc_data[9])
            print(" - LENID: ", inc_data[10:13])
            print(" - LENID (int): ", int(inc_data[10:13],16))
            print("INFO: ", INFO)
            print("CHKSUM: ", CHKSUM)
            #print("EOI: ", hex(inc_data[13+LENID+4]))
        return(False,"Checksum error")

def lchksum_calc(lenid):

    chksum = 0

    try:

        # for element in range(1, len(lenid)): #-5):
        #     chksum += (lenid[element])
        
        for element in range(0, len(lenid)):
            chksum += int(chr(lenid[element]),16)

        chksum = chksum % 16
        chksum = '{0:04b}'.format(chksum)

        flip_bits = '' 
        for i in chksum:
            if i == '0':
                flip_bits += '1'
            else:
                flip_bits += '0'

        chksum = flip_bits
        chksum = int(chksum,2)

        chksum += 1

        if chksum > 15:
            chksum = 0

        chksum = format(chksum, 'X')

    except:

        print("Error calculating LCHKSUM using LENID: ", lenid)
        return(False)

    return(chksum)

def bms_request(bms, ver=b"\x32\x35",adr=b"\x30\x31",cid1=b"\x34\x36",cid2=b"\x43\x31",info=b"",LENID=False):

    global bms_connected
    global debug_output
    
    request = b'\x7e'
    request += ver
    request += adr
    request += cid1
    request += cid2

    if not(LENID):
        LENID = len(info)
        #print("Length: ", LENID)
        LENID = bytes(format(LENID, '03X'), "ASCII")

    #print("LENID: ", LENID)

    if LENID == b'000':
        LCHKSUM = '0'
    else:
        LCHKSUM = lchksum_calc(LENID)
        if LCHKSUM == False:
            return(False,"Error calculating LCHKSUM)")
    #print("LCHKSUM: ", LCHKSUM)
    request += bytes(LCHKSUM, "ASCII")
    request += LENID
    request += info
    CHKSUM = bytes(chksum_calc(request), "ASCII")
    if CHKSUM == False:
        return(False,"Error calculating CHKSUM)")
    request += CHKSUM
    request += b'\x0d'

    if debug_output > 2:
        print("-> Outgoing Data: ", request)

    if not bms_sendData(bms,request):
        bms_connected = False
        print("Error, connection to BMS lost")
        return(False,"Error, connection to BMS lost")

    return (True, "")

i_remain_cap = {}
i_full_cap = {}
soc ={}
soh = {}
def bms_getAnalogData(inc_data, p=0):
    global print_initial
    global cells
    global temps
    global packs
    byte_index = 2
#    i_pack = []
#    v_pack = []
    global i_remain_cap
#    i_design_cap = []
#    cycles = []
    global i_full_cap
    global soc
    global soh

    try:
        v_cell = {}
        t_cell = {}

        soc[p] = int(inc_data[byte_index:byte_index+4], 16)/100
        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p) + "/soc",str(soc[p]))
        if print_initial:
            print("Pack " + str(p) + ", SOC: " + str(soc[p]) + " %")

        byte_index += 4

        v_pack = int(inc_data[byte_index:byte_index+4],16)/100
        byte_index += 4
        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p) + "/v_pack", str(v_pack))
        if print_initial:
            print("Pack " + str(p) + ", V Pack: " + str(v_pack) + " V")

        cells = int(inc_data[byte_index:byte_index+2],16)

        if print_initial:
            print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", Total cells: " + str(cells))
        byte_index += 2
            
        cell_min_volt = 0
        cell_max_volt = 0

        for i in range(0,cells):
            v_cell[i] = int(inc_data[byte_index:byte_index+4],16)
            byte_index += 4
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/v_cells/cell_" + str(i+1).zfill(config['zero_pad_number_cells']) ,str(v_cell[i]))
            if print_initial:
                print("Pack " + str(p).zfill(config['zero_pad_number_packs']) +", V Cell" + str(i+1).zfill(config['zero_pad_number_cells']) + ": " + str(v_cell[i]) + " mV")

            #Calculate cell max and min volt
            if i == 0:
                cell_min_volt = v_cell[i]
                cell_max_volt = v_cell[i]
            else:
                if v_cell[i] < cell_min_volt:
                    cell_min_volt = v_cell[i]
                if v_cell[i] > cell_max_volt:
                    cell_max_volt = v_cell[i]

        #Calculate cells max diff volt
        cell_max_diff_volt = cell_max_volt - cell_min_volt
        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/cells_max_diff_calc" ,str(cell_max_diff_volt))
        if print_initial:
            print("Pack " + str(p).zfill(config['zero_pad_number_packs']) +", Cell Max Diff Volt Calc: " + str(cell_max_diff_volt) + " mV")

        t_mos = (int(inc_data[byte_index:byte_index+4],16))/10
        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/t_mos",str(round(t_mos,1)))
        if print_initial:
            print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", T Mos: " + str(t_mos) + " Deg")
        byte_index += 4

        # some temperature 27 degrees
        byte_index += 4

        t_env = (int(inc_data[byte_index:byte_index+4],16))/10
        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/t_env",str(round(t_env,1)))
        if print_initial:
            print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", T Env: " + str(t_env) + " Deg")
        byte_index += 4

        temps = int(inc_data[byte_index:byte_index + 2],16)
        if print_initial:
            print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", Total temperature sensors: " + str(temps))
        byte_index += 2

        for i in range(0,temps): #temps-2
            t_cell[i] = (int(inc_data[byte_index:byte_index + 4],16))/10
            byte_index += 4
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/temps/temp_" + str(i+1) ,str(round(t_cell[i],1)))
            if print_initial:
                print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", Temp" + str(i+1) + ": " + str(round(t_cell[i],1)) + " ℃")

        i_pack = int(inc_data[byte_index:byte_index+4],16)
        byte_index += 4
        if i_pack >= 32768:
            i_pack = -1*(65535 - i_pack)
        i_pack = i_pack/100
        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/i_pack",str(i_pack))
        if print_initial:
            print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", I Pack: " + str(i_pack) + " A")

        byte_index += 4

        soh[p] = int(inc_data[byte_index:byte_index+4],16)
        byte_index += 4
        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/soh",str(soh[p]))
        if print_initial:
            print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", SOH: " + str(soh[p]) + " %")

        byte_index += 2

        i_full_cap[p] = int(inc_data[byte_index:byte_index+4],16)*10
        byte_index += 4
        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/i_full_cap",str(i_full_cap[p]))
        if print_initial:
            print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", I Full Capacity: " + str(i_full_cap[p]) + " mAh")

        i_remain_cap[p] = int(inc_data[byte_index:byte_index+4],16)*10
        byte_index += 4
        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/i_remain_cap",str(i_remain_cap[p]))
        if print_initial:
            print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", I Remaining Capacity: " + str(i_remain_cap[p]) + " mAh")

        cycles = int(inc_data[byte_index:byte_index+4],16)
        byte_index += 4
        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/cycles",str(cycles))
        if print_initial:
            print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", Cycles: " + str(cycles))

        w_status = {"INFO": [], "AS": [], "PS": [], "FS": [], "N/A": []}
        for warn_index in  itertools.chain(range(0, 10), range(31, 33)):
            value = int(inc_data[byte_index + warn_index*2:byte_index + warn_index*2 + 2], 16)
            for x in range(0, 8):
                w_byte = constants.w_byte[warn_index]
                if (value & (1<<x)):
                    w_status[w_byte[x+1]["type"]].append(w_byte[x+1]["msg"])

        info = 0
        if len(w_status["INFO"]) > 0:
            for v in w_status["INFO"]:
                if v == "Charge MOS":
                    info |= (1<<1)
                elif v == "DISCH MOS":
                    info |= (1<<2)
                elif v == "Current limit":
                    info |= (1<<0)
                elif v == "Charging":
                    info |= (1<<3)
                elif v == "Discharging":
                    info |= (1<<4)
                elif v == "Heating":
                    info |= (1<<7)
                else:
                    print("Unknown INFO: ", v)

        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/current_limit",str(info>>0 & 1))
        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/charge_fet",str(info>>1 & 1))
        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/discharge_fet",str(info>>2 & 1))
        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/charging",str(info>>3 & 1))
        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/discharging",str(info>>4 & 1))
        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/heating",str(info>>7 & 1))

        warnings = ""
        if len(w_status["AS"]) > 0:
            warnings += "\nAlarm Status: "
            for v in w_status["AS"]:
                warnings += v + ","
        if len(w_status["PS"]) > 0:
            warnings += "\nProtection Status: "
            for v in w_status["PS"]:
                warnings += v + ","
        if len(w_status["FS"]) > 0:
            warnings += "\nFault Status: "
            for v in w_status["FS"]:
                warnings += v + ","

        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/warnings",warnings)
        if print_initial:
            print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", warnings: " + warnings)

        byte_index += 36
        b = '{0:016b}'.format(int(inc_data[byte_index:byte_index+4], 16))
        client.publish(config['mqtt_base_topic'] + "/pack_" + str(p) + "/balancing", b)
        if print_initial:
            print("Pack " + str(p) + ", balancing: " + b)

        if len(i_remain_cap) == packs:
            client.publish(config['mqtt_base_topic'] + "/pack_remain_cap", str(sum(i_remain_cap.values())))
            if print_initial:
                print("Pack Remaining Capacity: " + str(sum(i_remain_cap.values()))+ " mAh")
        if len(i_full_cap) == packs:
            client.publish(config['mqtt_base_topic'] + "/pack_full_cap",str(sum(i_full_cap.values())))
            if print_initial:
                print("Pack Full Capacity: " + str(sum(i_full_cap.values())) + " mAh")
        if len(soc) == packs:
            client.publish(config['mqtt_base_topic'] + "/pack_soc",str(sum(soc.values())/len(soc)))
            if print_initial:
                print("Pack SOC: " + str(sum(soc.values())/len(soc)) + " %")
        if len(soh) == packs:
            client.publish(config['mqtt_base_topic'] + "/pack_soh",str(sum(soh.values())/len(soh)))
            if print_initial:
                print("Pack SOH: " + str(sum(soh.values())/len(soh)) + " %")

    except Exception as e:
        print("Error parsing BMS analog data: ", str(e))
        return(False,"Error parsing BMS analog data: " + str(e))

    if print_initial:
        print("Script running....")

    return True,True

def bms_ReadBms(bms):
    inc_data = bms_get_data(bms)

    if not inc_data:
        return

    temp2 = inc_data.split(b'\r')
    for element in range(0, len(temp2)):
        inc_data = temp2[element] + b'\r'

        if inc_data == False:
            print("Error retrieving data from BMS")
            return(False,"Error retrieving data from BMS")

        if debug_output > 2:
            print("<- Incoming data: ", inc_data)

        success, INFO = bms_parse_data(inc_data)


print("Connecting to BMS...")
bms,bms_connected = bms_connect(config['bms_ip'],config['bms_port'])

client.publish(config['mqtt_base_topic'] + "/availability","offline")
print_initial = True

addr = 0
while code_running == True:

    if bms_connected == True:
        if mqtt_connected == True:
            a = '{0:02d}'.format(addr).encode() 
            success, inc_data = bms_request(bms, ver=b'22', adr=a, cid1 = b'4A', cid2 = b'42', info = a)

            addr = (addr + 1) % packs
            bms_ReadBms(bms)
            if addr == 0:
                time.sleep(scan_interval)
            else:
                time.sleep(scan_interval/3)

            if print_initial:
                ha_discovery()
                
            client.publish(config['mqtt_base_topic'] + "/availability","online")

            print_initial = False
            

            repub_discovery += 1
            if repub_discovery*scan_interval > 3600:
                repub_discovery = 0
                print_initial = True
        
        else: #MQTT not connected
            client.loop_stop()
            print("MQTT disconnected, trying to reconnect...")
            client.connect(config['mqtt_host'], config['mqtt_port'], 60)
            client.loop_start()
            time.sleep(5)
            print_initial = True
    else: #BMS not connected
        print("BMS disconnected, trying to reconnect...")
        bms,bms_connected = bms_connect(config['bms_ip'],config['bms_port'])
        client.publish(config['mqtt_base_topic'] + "/availability","offline")
        time.sleep(5)
        print_initial = True

client.loop_stop()
