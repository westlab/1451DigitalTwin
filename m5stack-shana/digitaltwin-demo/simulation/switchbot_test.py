import time
from python_host import SwitchBot  # This is assuming you're using the python-host package

# This function should attempt to find your SwitchBot device by Bluetooth MAC address
def find_switchbot_device():
    # Replace with your SwitchBot's Bluetooth MAC address
    # You can find the MAC address by scanning for nearby Bluetooth devices
    target_device_address = "34:B7:DA:D4:C6:2E"  # Replace with the actual address
    return target_device_address

def main():
    # Step 1: Find the SwitchBot device by its Bluetooth MAC address
    device_address = find_switchbot_device()
    
    if not device_address:
        print("No SwitchBot device found!")
        return
    
    print(f"Connecting to SwitchBot device at {device_address}...")
    
    try:
        # Step 2: Create a SwitchBot object and connect
        bot = SwitchBot(device_address)

        # Step 3: Check if the device is alive and wake it up if necessary
        if not bot.is_alive():
            print("SwitchBot is asleep. Waking up...")
            bot.wake_up()  # Wake up the device

        # Step 4: Send a command (like pressing a button)
        print("Sending command to SwitchBot...")
        bot.press_button()  # Example command - replace with the actual method if different

        time.sleep(2)  # Optional delay to wait for SwitchBot to process the command
        
        print("Command sent successfully to the SwitchBot!")

    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Step 5: Clean up by disconnecting from the SwitchBot
        if bot.is_connected():
            bot.disconnect()

if __name__ == "__main__":
    main()
