# Apple-Calendar-Assistant

A local Flask-based adapter that exposes your Apple Calendar (via EventKit) as a RESTful API, enabling ChatGPT Custom GPTs to list, create, update, delete, summarize, and search events — complete with recurring-event support and location handling.

## Features

- **List Events**  
  `GET /listEvents?start=ISO&end=ISO`  
  Returns all events (including recurrences) in a UTC range.

- **Create Event**  
  `POST /createEvent`  
  Provide JSON `{title, start, end, location?}` to add a new event.

- **Update Event**  
  `POST /updateEvent`  
  Provide JSON `{id, title?, start?, end?, location?, instanceStart?}` to modify an event or a specific recurrence.

- **Delete Event**  
  `DELETE /deleteEvent?id=EVENT_ID`  
  Removes an event by ID.

- **Summarize Events**  
  `GET /summarizeEvents?start=ISO&end=ISO`  
  Returns a plain-text list of events.

- **Next Event**  
  `GET /nextEvent?keyword=WORD`  
  Finds the next occurrence matching a keyword.

- **Search by Location**  
  `GET /searchByLocation?location=PLACE`  
  Filters events by location.

---

## Prerequisites

- macOS 12+ (for EventKit & PyObjC)
- Python 3.9+
- Access to an Apple Calendar and the Calendar app
- Ngrok account and installed CLI (v3) for public tunneling

---
## File Structure

Apple-Calendar-Assistant/

├── adapter.py        # Flask server & EventKit integration

├── openapi.yaml      # OpenAPI 3.1 spec for endpoints

├── requirements.txt  # Python dependencies

└── README.md         # This file

---
## License

CC BY-NC 4.0 International (Creative Commons Attribution-NonCommerical)
