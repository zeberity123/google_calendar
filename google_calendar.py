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
    """Fetches events from all Google Calendars and sorts them by end time."""
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
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    future = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + 'Z'  # Fetch events for the next 30 days

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
        return []

    # Sort events by end time.
    events_sorted = sorted(
        all_events,
        key=lambda event: event['end'].get('dateTime', event['end'].get('date'))
    )

    return events_sorted

def create_ui(events):
    """Creates the GUI to display events with urgency-colored bars."""
    root = tk.Tk()
    # root.geometry("350x900")
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

    current_date = datetime.datetime.now().date()

    # Populate the scrollable frame with events
    for event in events:
        summary = event.get('summary', 'No Title')
        start_str = event['start'].get('dateTime', event['start'].get('date'))
        end_str = event['end'].get('dateTime', event['end'].get('date'))
        calendar_name = event.get('calendarSummary', 'Unknown Calendar')

        # Parse start and end dates
        try:
            start_datetime = parser.isoparse(start_str)
            end_datetime = parser.isoparse(end_str)
        except ValueError:
            print(f"Error parsing start or end time for event: {summary}")
            continue  # Skip this event if parsing fails

        start_date = start_datetime.date()
        end_date = end_datetime.date()

        # Calculate total_days and passed_days
        total_days = (end_date - start_date).days + 1
        if total_days <= 0:
            total_days = 1  # Avoid division by zero or negative durations

        passed_days = (current_date - start_date).days + 1

        # Handle cases where event hasn't started or already ended
        if current_date < start_date:
            passed_days = 0
        elif current_date > end_date:
            passed_days = total_days

        # Calculate urgency (remaining days)
        remaining_days = (end_date - current_date).days + 1
        if remaining_days < 0:
            remaining_days = 0
        if remaining_days > total_days:
            remaining_days = total_days

        # Calculate urgency ratio
        urgency_ratio = remaining_days / total_days

        # Clamp urgency_ratio between 0 and 1
        urgency_ratio = max(0, min(urgency_ratio, 1))

        # Determine color intensity based on urgency
        red_intensity = int(round((1 - urgency_ratio) * 255))
        green_intensity = int(round(urgency_ratio * 255))

        # Clamp color intensities between 0 and 255
        red_intensity = max(0, min(red_intensity, 255))
        green_intensity = max(0, min(green_intensity, 255))

        color_hex = f'#{red_intensity:02x}{green_intensity:02x}00'  # Format color as hex

        # Create a frame for the event with colored bar
        event_frame = ttk.Frame(scrollable_frame, borderwidth=1, relief="solid")
        event_frame.pack(fill=tk.X, padx=10, pady=5)

        # Create the colored bar
        color_bar = tk.Frame(event_frame, bg=color_hex, height=20)
        color_bar.pack(fill=tk.X)

        # Display end date in bold
        end_date_str = end_date.strftime('%A, %B %d, %Y')
        end_date_label = ttk.Label(event_frame, text=end_date_str, font=("Helvetica", 14, "bold"))
        end_date_label.pack(anchor='w', padx=10, pady=(5, 0))

        # Display summary and progress
        progress_text = f"{summary} ({passed_days}/{total_days})"
        progress_label = ttk.Label(event_frame, text=progress_text, font=("Helvetica", 12))
        progress_label.pack(anchor='w', padx=10, pady=(0, 5))

    root.mainloop()

def main():
    events = get_events()
    if not events:
        print('No upcoming events found.')
        return
    create_ui(events)

if __name__ == '__main__':
    main()
