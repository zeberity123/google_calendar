from __future__ import print_function
import datetime
import os.path
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from dateutil import parser  # Import the dateutil parser

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_events():
    """Fetches events from all Google Calendars and groups them by date."""
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If credentials are not available or are invalid, prompt the user to log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Run local server for authentication.
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for future use.
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    # Build the service object for the Google Calendar API.
    service = build('calendar', 'v3', credentials=creds)

    # Define the time range (from now to a future date).
    now = datetime.datetime.now().isoformat() + 'Z'  # 'Z' indicates UTC time
    future = (datetime.datetime.now() + datetime.timedelta(days=7)).isoformat() + 'Z'

    # Get the list of calendars
    calendars_result = service.calendarList().list().execute()
    calendars = calendars_result.get('items', [])

    all_events = []

    # Loop through all calendars
    for calendar in calendars:
        calendar_id = calendar['id']
        # Fetch events from this calendar
        events_result = service.events().list(calendarId=calendar_id, timeMin=now,
                                              timeMax=future, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])
        for event in events:
            # Add calendar name to event data
            event['calendarSummary'] = calendar.get('summary', 'No Calendar Name')
            all_events.append(event)

    # Check if any events are found.
    if not all_events:
        return {}

    # Sort events by start time.
    events_sorted = sorted(
        all_events,
        key=lambda event: event['start'].get('dateTime', event['start'].get('date'))
    )

    # Group events by date
    events_by_date = {}
    for event in events_sorted:
        # Get the event's start date
        start_str = event['start'].get('dateTime', event['start'].get('date'))
        # Parse the datetime string correctly
        try:
            start_datetime = parser.isoparse(start_str)
        except ValueError:
            print(f"Error parsing date: {start_str}")
            continue  # Skip this event if parsing fails

        start_date = start_datetime.date()

        # Convert date to string for grouping
        date_str = start_date.strftime('%A, %B %d, %Y')
        if date_str not in events_by_date:
            events_by_date[date_str] = []
        events_by_date[date_str].append(event)

    return events_by_date

def create_ui(events_by_date):
    """Creates the GUI to display events day by day."""
    root = tk.Tk()
    root.title("Google Calendar Events")

    # Create a scrollable frame
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=1)

    canvas = tk.Canvas(main_frame)
    scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Populate the scrollable frame with events
    for date_str, events in events_by_date.items():
        # Create a label for the date
        date_label = ttk.Label(scrollable_frame, text=date_str, font=("Helvetica", 16, "bold"))
        date_label.pack(anchor='w', pady=(10, 0))

        # List events under the date
        for event in events:
            summary = event.get('summary', 'No Title')
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            calendar_name = event.get('calendarSummary', 'Unknown Calendar')

            # Parse start and end times
            try:
                start_datetime = parser.isoparse(start)
                end_datetime = parser.isoparse(end)
            except ValueError:
                print(f"Error parsing start or end time for event: {summary}")
                continue  # Skip this event if parsing fails

            if 'dateTime' in event['start']:
                start_time = start_datetime.strftime('%I:%M %p')
                end_time = end_datetime.strftime('%I:%M %p')
            else:
                start_time = 'All Day'
                end_time = ''

            event_text = f"{start_time} - {end_time} | {summary} ({calendar_name})"
            event_label = ttk.Label(scrollable_frame, text=event_text, font=("Helvetica", 12))
            event_label.pack(anchor='w', padx=20)

    root.mainloop()

def main():
    events_by_date = get_events()
    if not events_by_date:
        print('No upcoming events found.')
        return
    create_ui(events_by_date)

if __name__ == '__main__':
    main()
