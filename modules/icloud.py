import os
import sys
import click

from dotenv import load_dotenv
from pyicloud import PyiCloudService
from datetime import datetime

class iCloudService:
    def __init__(self, email=None, password=None):
        self.email = email
        self.password = password
        self.api = None
        self.authenticated = False

    def authenticate(self):
        """Einmalige Authentifizierung durchführen"""
        if not self.api:
            self.api = PyiCloudService(self.email, self.password)

            # Zwei-Faktor-Authentifizierung
            if self.api.requires_2fa:
                self._handle_2fa()
            elif self.api.requires_2sa:
                self._handle_2sa()

            self.authenticated = True
            print("Authentifizierung abgeschlossen")
        else:
            print("Bereits authentifiziert")

    def _handle_2fa(self):
        code = input("Enter the code you received on one of your approved devices: ")
        result = self.api.validate_2fa_code(code)
        print(f"Code validation result: {result}")

        if not result:
            print("Failed to verify security code")
            sys.exit(1)

        if not self.api.is_trusted_session:
            print("Session is not trusted. Requesting trust...")
            result = self.api.trust_session()
            print(f"Session trust result {result}")
            if not result:
                print("Failed to request trust. You will likely be prompted for the code again in the coming weeks")

    def _handle_2sa(self):
        devices = self.api.trusted_devices
        for i, device in enumerate(devices):
            print(f"  {i}: {device.get('deviceName', 'SMS to %s' % device.get('phoneNumber'))}")

        device = click.prompt('Which device would you like to use?', default=0)
        device = devices[device]
        if not self.api.send_verification_code(device):
            print("Failed to send verification code")
            sys.exit(1)

        code = click.prompt('Please enter validation code')
        if not self.api.validate_verification_code(device, code):
            print("Failed to verify verification code")
            sys.exit(1)

    def get_iphone_location(self):
        """Get the current location of the iPhone."""
        return self.api.iphone.location()

    def ring_device(self, device_id):
        """Play a sound on the iPhone to help locate it."""
        self.api.devices[device_id].play_sound()

    def get_devices(self):
        """Get the status of all icloud devices.
        Returns a list of dictionaries containing device information."""
        
        devices_info = []
        for device in self.api.devices:
            device_data = {
                'id': device['id'],
                'name': device['name'],
                'content': device.content,
                'data': device.data,
                'message_url': device.message_url,
                'sound_url': device.sound_url,
                'location': device.location(),
                'status': device.status(),
            }
            devices_info.append(device_data)
        
        return devices_info

    def convert_to_datetime(self, date_list):
        return datetime(date_list[1], date_list[2], date_list[3], date_list[4], date_list[5], date_list[6] // 1000)


    def get_calendar_events_in_range(self, range):
        print('range',range)
        print(self.api.devices)

        # print("Contacts")
        # for c in self.api.contacts.all():
        #     print(c.get("firstName"), c.get("phones"))

        # print("File Storage")
        # print(self.api.drive.dir())
        
        start = datetime.fromisoformat(range.start)
        end = datetime.fromisoformat(range.end)
        print(start)
        print(end)
        """Get a list of calendar events."""
        events = self.api.calendar.events(start, end)
        event_details = []

        for event in events:
            event_details.append(event)
        return event_details


# Beispiel der Nutzung
if __name__ == "__main__":
    iphone_service = IphoneService()

    # Standort des iPhones abrufen
    print("######## LOCATION ########")
    location = iphone_service.get_iphone_location()
    print(location)

    # Status des iPhones abrufen
    print("######## STATUS ########")
    status = iphone_service.get_iphone_status()
    print(status)

    # Kalenderereignisse abrufen
    print("######## EVENTS ########")
    events = iphone_service.get_calendar_events()
    for event in events:
        print(event)
    
    # Klingeln lassen
    # iphone_service.play_iphone_sound()
