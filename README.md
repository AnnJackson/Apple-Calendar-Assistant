# Apple-Calendar-Assistant

A local Flask-based adapter that exposes your Apple Calendar (via EventKit) as a RESTful API, enabling ChatGPT Custom GPTs to list, create, update, delete, summarize, and search events—complete with recurring-event support and location handling.

Features
	•	List Events: GET /listEvents?start=ISO&end=ISO returns all events (including recurrences) in a UTC range.
	•	Create Event: POST /createEvent with JSON {title, start, end, location?} to add a new event.
	•	Update Event: POST /updateEvent with JSON {id, title?, start?, end?, location?, instanceStart?} to modify an event or a specific recurrence.
	•	Delete Event: DELETE /deleteEvent?id=EVENT_ID removes an event by ID.
	•	Summarize Events: GET /summarizeEvents?start=ISO&end=ISO returns a plain-text list of events.
	•	Next Event: GET /nextEvent?keyword=WORD finds the next occurrence matching a keyword.
	•	Search by Location: GET /searchByLocation?location=PLACE filters events by location.

Prerequisites
	•	macOS 12+ (for EventKit & PyObjC)
	•	Python 3.9+
	•	Access to an Apple Calendar and the Calendar app
	•	Ngrok account and installed CLI (v3) for public tunneling

Setup
	1.	Clone the repo

git clone https://github.com/yourusername/CalendarGPT.git
cd CalendarGPT


	2.	Create a virtual environment

python3 -m venv .venv
source .venv/bin/activate


	3.	Install dependencies

pip install -r requirements.txt


	4.	Start the adapter

python adapter.py


	5.	Expose via ngrok

ngrok http 5001


	6.	Update OpenAPI spec & Plugin manifest
	•	Edit openapi.yaml → set servers.url to your ngrok HTTPS URL
	•	Edit ai-plugin.json → set api.url and logo_url to match
	7.	Register your Custom GPT
	•	In ChatGPT, go to GPTs → Create GPT, import the openapi.yaml, add Actions.

File Structure

CalendarGPT/
├── adapter.py        # Flask server & EventKit integration
├── openapi.yaml      # OpenAPI 3.1 spec for endpoints
├── ai-plugin.json    # ChatGPT plugin manifest
├── requirements.txt  # Python dependencies
└── README.md         # This file

Usage Examples

List today’s events:

curl "http://localhost:5001/listEvents?start=2025-05-18T00:00:00Z&end=2025-05-19T00:00:00Z"

Create an event:

curl -X POST http://localhost:5001/createEvent \
  -H "Content-Type: application/json" \
  -d '{"title":"Doctor Visit","start":"2025-05-20T14:00:00Z","end":"2025-05-20T15:00:00Z","location":"Clinic"}'

Update a recurrence:

curl -X POST http://localhost:5001/updateEvent \
  -H "Content-Type: application/json" \
  -d '{"id":"<MASTER_ID>:<INSTANCE_ID>","location":"Starbucks on 5th Ave","instanceStart":"2025-05-19T19:00:00Z"}'

Search by location:

curl "http://localhost:5001/searchByLocation?location=Cafe"

License 
