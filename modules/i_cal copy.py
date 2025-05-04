import caldav
import json
import os

from datetime import datetime, timedelta

class ICalendarClient:
    def __init__(self):
        """
        Initialisiert den CalDAV-Client mit den iCloud-Zugangsdaten.
        """
        self.username = os.getenv("APPLE_MAIL")
        self.password = os.getenv("SPECIFIC_APPLE_PW")
        self.client = caldav.DAVClient('https://caldav.icloud.com', username=self.username, password=self.password)
        self.principal = self.client.principal()
        self.calendars = self.principal.calendars()
    
    def get_events(self, start_time, end_time):
        events_list = []

        for calendar in self.calendars:
            events = calendar.date_search(start=start_time, end=end_time)

            i = 0 
            for event in events:
                print(i)
                i = i + 1
                
                print()
                print('######## vevent ########')
                print(dir(event.instance.vevent))
                
                print()
                print('######## normal_attributes ########')
                print(event.instance.vevent.normal_attributes)
                
                print()
                print('######## name ########')
                print(event.instance.vevent.name)
                
                print()
                print('######## behavior ########')
                print(dir(event.instance.vevent.behavior))

                print()
                print('######## description ########')
                print(event.instance.vevent.behavior.description)
                
                print()
                print('######## parentBehavior ########')
                print(event.instance.vevent.parentBehavior)

                print()
                print('######## lines ########')
                print(event.instance.vevent.lines())
                for child in event.instance.vevent.lines():
                    print(child)

                print()
                print('######## components ########')
                print(event.instance.vevent.components())
                for child in event.instance.vevent.components():
                    print(child)

                print()
                print('######## CONTENTS ########')
                # for key in dir(event.instance.vevent):
                #     print(key, "->", getattr(event.instance.vevent.contents, key))
                print('######## KEYS ########')
                for key, value in event.instance.vevent.contents.items():
                    print(f"{key}: {value}")

                event_data = {
                    "calendar": calendar.name,
                    "title": event.instance.vevent.summary,
                    "description": getattr(event.instance.vevent, 'description', None),
                    "start": str(event.instance.vevent.dtstart.value),
                    "end": str(event.instance.vevent.dtend.value),
                    "location": getattr(event.instance.vevent, 'location', None),
                    "alarm": [alarm.trigger.value for alarm in getattr(event.instance.vevent, 'valarm', [])],
                    "created": str(event.instance.vevent.created.value) if hasattr(event.instance.vevent, 'created') else None,
                    "last_modified": str(event.instance.vevent.last_modified.value) if hasattr(event.instance.vevent, 'last_modified') else None,
                    "status": getattr(event.instance.vevent, 'status', None),
                    "attendees": [str(att) for att in getattr(event.instance.vevent, 'attendee', [])],
                    "categories": getattr(event.instance.vevent, 'categories', None),
                    "recurrence_rule": getattr(event.instance.vevent, 'rrule', None),
                    "excluded_dates": [str(date.value) for date in getattr(event.instance.vevent, 'exdate', [])],       
                }
                events_list.append(event_data)
        
        return events_list


    def get_day_events(self):
        """
        Ruft alle heutigen Events aus den iCloud-Kalendern ab und gibt sie als JSON zurück.
        """
        start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)

        return self.get_events(start_time, end_time)

    def get_week_events(self):
        """
        Ruft alle aktuellen und kommenden Events bis zum Ende der Woche aus den iCloud-Kalendern ab und gibt sie als JSON zurück.
        """
        today = datetime.now()
        start_time = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=(6 - today.weekday()))

        return self.get_events(start_time, end_time)

    def get_month_events(self):
        """
        Ruft alle aktuellen und kommenden Events im laufenden Monat aus den iCloud-Kalendern ab
        und gibt sie als JSON zurück. Vergangene Events werden ignoriert.
        """
        today = datetime.now()
        # Setze den ersten Tag des Monats
        start_time = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Berechne das Ende des Monats
        next_month = today.replace(day=28) + timedelta(days=4)  # Geh zum nächsten Monat
        end_time = next_month.replace(day=1) - timedelta(seconds=1)
        
        return self.get_events(start_time, end_time)

    def get_events_in_range(self, start_date: str, end_date: str):
        """
        Ruft alle Events zwischen dem angegebenen Start- und Enddatum aus den iCloud-Kalendern ab
        und gibt sie als JSON zurück. Vergangene Events werden ignoriert.
        """
        print(f"Getting events between {start_date} and {end_date}")
        # Konvertiere die übergebenen Strings in datetime-Objekte
        try:
            start_time = start_date
            end_time = end_date
        except ValueError as e:
            raise ValueError(f"Invalid date format: {e}")
        
        return self.get_events(start_time, end_time)