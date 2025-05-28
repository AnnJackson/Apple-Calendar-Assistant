from flask import Flask, request, jsonify
from EventKit import EKEventStore, EKEvent
from datetime import datetime, timedelta, timezone
import time
# For macOS-native timezone and date handling
import time as _time_module
from Foundation import NSTimeZone, NSDate

app = Flask(__name__)
import logging
logging.basicConfig(level=logging.INFO)

@app.route("/")
def index():
    return "Calendar adapter is running"

def get_store_and_calendar():
    store = EKEventStore.alloc().init()
    store.requestAccessToEntityType_completion_(0, lambda granted, err: None)
    time.sleep(1)
    calendars = store.calendarsForEntityType_(0)
    cal = next((c for c in calendars if c.title() == "YOUR CALENDAR"), None)
    if not cal:
        raise RuntimeError("Calendar not found")
    return store, cal

@app.route("/listEvents")
def list_events():
    app.logger.info(f"listEvents called with args: {request.args}")
    start_str = request.args["start"]
    end_str = request.args["end"]
    # Parse ISO strings into Python datetime, then convert to UTC timestamp
    dt_start_py = datetime.fromisoformat(start_str)
    dt_end_py = datetime.fromisoformat(end_str)
    ts_start = dt_start_py.replace(tzinfo=timezone.utc).timestamp()
    ts_end = dt_end_py.replace(tzinfo=timezone.utc).timestamp()
    # Create NSDate objects for predicate
    ns_start = NSDate.dateWithTimeIntervalSince1970_(ts_start)
    ns_end = NSDate.dateWithTimeIntervalSince1970_(ts_end)
    store, cal = get_store_and_calendar()
    predicate = store.predicateForEventsWithStartDate_endDate_calendars_(ns_start, ns_end, [cal])
    events = store.eventsMatchingPredicate_(predicate)
    result = []
    for e in events:
        # Convert EKDate to UTC datetime
        ts = e.startDate().timeIntervalSince1970()
        dt = datetime.fromtimestamp(ts, timezone.utc)
        te = e.endDate().timeIntervalSince1970()
        dt_end = datetime.fromtimestamp(te, timezone.utc)
        result.append({
            "id": e.eventIdentifier(),
            "title": e.title(),
            "location": e.location() or "",
            "start": dt.isoformat().replace("+00:00", "Z"),
            "end": dt_end.isoformat().replace("+00:00", "Z")
        })
    return jsonify(result)

@app.route("/createEvent", methods=["POST"])
def create_event():
    app.logger.info(f"createEvent called with data: {request.json}")
    data = request.get_json()
    title = data.get("title")
    start_str = data.get("start")
    end_str = data.get("end")
    if not (title and start_str and end_str):
        return jsonify({"error": "Missing required fields: title, start, end"}), 400

    # Parse dates
    start = datetime.fromisoformat(start_str)
    end = datetime.fromisoformat(end_str)
    # Ensure timezone-aware UTC
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    # Get store and calendar
    store, cal = get_store_and_calendar()

    # Create new event using EKEvent
    new_event = EKEvent.eventWithEventStore_(store)
    new_event.setCalendar_(cal)
    new_event.setTitle_(title)
    new_event.setStartDate_(start)
    new_event.setEndDate_(end)
    # Set location if provided
    location = data.get("location")
    if location:
        new_event.setLocation_(location)
    # Save the event
    success, error = store.saveEvent_span_error_(new_event, 0, None)
    if not success:
        app.logger.error(f"Error creating event: {error}")
        return jsonify({"error": str(error)}), 500

    return jsonify({
        "id": new_event.eventIdentifier(),
        "title": new_event.title(),
        "start": new_event.startDate().description(),
        "end": new_event.endDate().description()
    }), 201


@app.route("/deleteEvent", methods=["DELETE"])
def delete_event():
    app.logger.info(f"deleteEvent called with args: {request.args}")
    event_id = request.args.get("id")
    if not event_id:
        return jsonify({"error": "Missing required parameter: id"}), 400
    store, cal = get_store_and_calendar()
    event = store.eventWithIdentifier_(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    success, error = store.removeEvent_span_error_(event, 0, None)
    if not success:
        app.logger.error(f"Error deleting event: {error}")
        return jsonify({"error": str(error)}), 500
    return jsonify({"deletedId": event_id}), 200

@app.route("/updateEvent", methods=["POST"])
def update_event():
    # Supports updating a specific occurrence via instanceStart
    app.logger.info(f"updateEvent called with data: {request.json}")
    data = request.get_json()
    # Initialize store and calendar for updates
    store, cal = get_store_and_calendar()
    instance_start_str = data.get("instanceStart")
    event_id = data.get("id")
    if not event_id:
        return jsonify({"error": "Missing required field: id"}), 400
    if instance_start_str:
        # Normalize ISO 'Z' suffix to '+00:00' for fromisoformat
        instance_start_str = instance_start_str.replace("Z", "+00:00")
        # Parse the requested occurrence start as UTC
        inst_dt = datetime.fromisoformat(instance_start_str)
        if inst_dt.tzinfo is None:
            inst_dt = inst_dt.replace(tzinfo=timezone.utc)
        # Convert to timestamp and create NSDate objects for predicate window
        inst_ts = inst_dt.timestamp()
        ns_start = NSDate.dateWithTimeIntervalSince1970_(inst_ts - 60)  # 1 minute before
        ns_end   = NSDate.dateWithTimeIntervalSince1970_(inst_ts + 60)  # 1 minute after
        # Fetch events in that narrow window
        predicate = store.predicateForEventsWithStartDate_endDate_calendars_(ns_start, ns_end, [cal])
        candidates = store.eventsMatchingPredicate_(predicate)
        # Identify the occurrence by matching the start time closely
        occurrence = None
        for e in candidates:
            # Compare each candidate's start date to the requested instance timestamp
            candidate_ts = e.startDate().timeIntervalSince1970()
            if abs(candidate_ts - inst_ts) < 2:  # within 2 seconds
                occurrence = e
                break
        if not occurrence:
            return jsonify({"error": "Occurrence not found"}), 404
        event = occurrence
    else:
        event = store.eventWithIdentifier_(event_id)
        if not event:
            return jsonify({"error": "Event not found"}), 404
    # Update fields if provided
    if "title" in data:
        event.setTitle_(data["title"])
    if "start" in data:
        dt = datetime.fromisoformat(data["start"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        event.setStartDate_(dt)
    if "end" in data:
        dt = datetime.fromisoformat(data["end"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        event.setEndDate_(dt)
    if "location" in data:
        event.setLocation_(data["location"])
    # Save changes
    success, error = store.saveEvent_span_error_(event, 0, None)
    if not success:
        app.logger.error(f"Error updating event: {error}")
        return jsonify({"error": str(error)}), 500
    return jsonify({
        "id": event.eventIdentifier(),
        "title": event.title(),
        "start": event.startDate().description(),
        "end": event.endDate().description()
    }), 200

@app.route("/summarizeEvents")
def summarize_events():
    app.logger.info(f"summarizeEvents called with args: {request.args}")
    start_str = request.args.get("start")
    end_str = request.args.get("end")
    if not (start_str and end_str):
        return jsonify({"error": "Missing required parameters: start, end"}), 400

    # Parse dates
    start = datetime.fromisoformat(start_str)
    end = datetime.fromisoformat(end_str)

    # Fetch events
    store, cal = get_store_and_calendar()
    predicate = store.predicateForEventsWithStartDate_endDate_calendars_(start, end, [cal])
    events = store.eventsMatchingPredicate_(predicate)

    # Build plain text list of events
    raw = ""
    for e in events:
        ts = e.startDate().timeIntervalSince1970()
        dt = datetime.fromtimestamp(ts, timezone.utc)
        raw += f"- {dt.isoformat().replace('+00:00','Z')}: {e.title()}\n"

    return jsonify({
        "summary": raw or "No events in this range."
    })


@app.route("/nextEvent")
def next_event():
    app.logger.info(f"nextEvent called with args: {request.args}")
    keyword = request.args.get("keyword", "").lower()
    if not keyword:
        return jsonify({"error": "Missing required parameter: keyword"}), 400

    # Use macOS-native NSDate and timezone for compatibility
    tz_obj = NSTimeZone.timeZoneWithName_("America/Phoenix")
    now_date = NSDate.date()
    one_year_date = NSDate.dateWithTimeIntervalSinceNow_(365 * 24 * 3600)

    # Fetch events in that window
    store, cal = get_store_and_calendar()
    predicate = store.predicateForEventsWithStartDate_endDate_calendars_(now_date, one_year_date, [cal])
    events = store.eventsMatchingPredicate_(predicate)

    # Filter by keyword in title
    matches = [e for e in events if keyword in e.title().lower()]
    if not matches:
        return jsonify({"message": f"No upcoming events found matching '{keyword}'"}), 404

    # Find the soonest occurrence
    next_e = min(matches, key=lambda e: e.startDate().timeIntervalSince1970())

    # Convert timestamps to UTC ISO strings
    ts_start = next_e.startDate().timeIntervalSince1970()
    ts_end = next_e.endDate().timeIntervalSince1970()
    dt_start = datetime.fromtimestamp(ts_start, timezone.utc).isoformat().replace("+00:00","Z")
    dt_end   = datetime.fromtimestamp(ts_end, timezone.utc).isoformat().replace("+00:00","Z")

    return jsonify({
        "id": next_e.eventIdentifier(),
        "title": next_e.title(),
        "start": dt_start,
        "end": dt_end
    }), 200


@app.route("/searchByLocation")
def search_by_location():
    app.logger.info(f"searchByLocation called with args: {request.args}")
    loc_kw = request.args.get("location", "").lower()
    if not loc_kw:
        return jsonify({"error": "Missing required parameter: location"}), 400

    # Define search window (now to one year ahead)
    tz_obj = NSTimeZone.timeZoneWithName_("America/Phoenix")
    now_date = NSDate.date()
    one_year_date = NSDate.dateWithTimeIntervalSinceNow_(365 * 24 * 3600)

    store, cal = get_store_and_calendar()
    predicate = store.predicateForEventsWithStartDate_endDate_calendars_(now_date, one_year_date, [cal])
    events = store.eventsMatchingPredicate_(predicate)

    # Filter by location substring
    matches = [e for e in events if e.location() and loc_kw in e.location().lower()]
    output = []
    for e in matches:
        ts_start = e.startDate().timeIntervalSince1970()
        ts_end = e.endDate().timeIntervalSince1970()
        output.append({
            "id": e.eventIdentifier(),
            "title": e.title(),
            "location": e.location() or "",
            "start": datetime.fromtimestamp(ts_start, timezone.utc).isoformat().replace("+00:00","Z"),
            "end": datetime.fromtimestamp(ts_end, timezone.utc).isoformat().replace("+00:00","Z")
        })
    return jsonify(output)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
