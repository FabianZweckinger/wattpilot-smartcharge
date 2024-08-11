import time
import requests
import wattpilot

# Config:
amis_reader_address = "http://xxx.xxx.xxx.xxx/rest"  # Amis reader for outgoing grid power
charge_distance_to_0 = 1000  # distance until outgoing grid power reaches 0 Watts in Watts
checktime = 5  # repeated check time in seconds
grid_voltage = 230  # grid voltage in Volts

print("Smartcharge started...")


def set_charge_level(charge_with_3_phase, charge_amps, wattpilot_connection):
    wattpilot_connection.set_psm(charge_with_3_phase)
    wattpilot_connection.set_power(charge_amps)

    if charge_with_3_phase:
        print("Set charge level to: 3 phase at " + str(charge_amps))
    else:
        print("Set charge level to: 1 phase at " + str(charge_amps))

wattpilot_default_mode_enabled = False
smartmeter_outgoing_power = 0  # should be negativ if power goes to the grid
current_charge_power = 0  # current charge power of the wallbox

while True:
    # Get grid power (AMIS Reader)
    try:
        api_response = requests.get(amis_reader_address)
        amis = api_response.json()
        smartmeter_outgoing_power = -amis['saldo']
    except:
        print("Error reading amis reader")
        smartmeter_outgoing_power = 0
    smartmeter_outgoing_power = smartmeter_outgoing_power - charge_distance_to_0


    # Get wallbox current charge power and mode:
    wattpilot_connection = wattpilot.Wattpilot("xxx.xxx.xxx.xxx", "xxxxxxxxxxxxx")
    wattpilot_connection.connect()
    c = 0
    while not wattpilot_connection.connected and c < 10:
        time.sleep(1)
        c = c + 1
    wattpilot_default_mode_enabled = wattpilot_connection.mode == "Default"

    if wattpilot_default_mode_enabled:
        try:
            current_charge_power = int(wattpilot_connection.power * 1000)
        except TypeError:
            current_charge_power = 0

        # Power Level switch:
        found_power_level = False

        # Check if 3 phase is sufficient (Wattage level from 11040W -> 4140W at 230V)
        for amperage in reversed(range(8, 16)):
            charge_power = amperage * grid_voltage * 3
            if smartmeter_outgoing_power > charge_power - current_charge_power:
                set_charge_level(True, amperage, wattpilot_connection)
                found_power_level = True
                break

        if not found_power_level:
            # Check if 3 phase is sufficient (Wattage level from 3680W -> 1380W at 230V)
            for amperage in reversed(range(8, 16)):
                charge_power = amperage * grid_voltage
                if smartmeter_outgoing_power > charge_power - current_charge_power:
                    set_charge_level(False, amperage, wattpilot_connection)
                    found_power_level = True
                    break

        if not found_power_level and current_charge_power != 0:
            set_charge_level(False, 0, wattpilot_connection)
        elif current_charge_power == 0:
            print("Charge level remains at 0")

    wattpilot_connection.disconnect()
    time.sleep(checktime)
