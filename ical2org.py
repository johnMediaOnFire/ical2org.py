#!/usr/bin/env python

from math import floor
from datetime import date, datetime, timedelta, tzinfo
import icalendar as ical
import os
from pytz import timezone, utc
import sys

# Default attendee: for checkout status of the participant.
DEFAULT_ATTENDEE = "jwpalmieri@gmail.com"

# Default local timezone. This needs to follow what timezone emacs is
# in. Or you can pull it from a file.
LOCAL_TZ = timezone("America/Los_Angeles")
TIMEZONE_FILE = "~/tmp/calendar/timezone"

# Window length in days (left & right from current time). Has to be positive.
WINDOW = 90

# leave empty if you don't want to attach any tag to recurring events
RECUR_TAG = "" #":RECURRING::"

# Do not change anything below

def orgDatetime(dt):
    '''Given a datetime in his own timezone, return YYYY-MM-DD DayofWeek HH:MM in local timezone'''
    return dt.astimezone(LOCAL_TZ).strftime("<%Y-%m-%d %a %H:%M>")

def orgDate(dt):
    '''Given a date in his own timezone, return YYYY-MM-DD DayofWeek in local timezone'''
    return dt.astimezone(LOCAL_TZ).strftime("<%Y-%m-%d %a>")

def get_datetime(dt):
    '''Given a datetime, return it. If argument is date, convert it to a local datetime'''
    if isinstance(dt, datetime):
        return dt
    elif isinstance(dt, date):
        return datetime(year = dt.year, month = dt.month, day = dt.day, tzinfo = LOCAL_TZ)
    else:
        # The given ical date may have a timezone. If not, use the
        # default for the calendar.
        if "TZID" in dt.params:
            tz = timezine(dt.params["TZID"])
        else:
            tz = LOCAL_TZ

        aux_dt = datetime(year = dt.year, month = dt.month, day = dt.day, tzinfo = tz)
        return aux_dt

def add_delta_dst(dt, delta):
    '''Add a timedelta to a datetime, adjusting DST when appropriate'''
    # convert datetime to naive, add delta and convert again to his own timezone
    naive_dt = dt.replace(tzinfo = None)
    return dt.tzinfo.localize(naive_dt + delta)

def advance_just_before(start_dt, timeframe_start, delta_days):
    '''Advance an start_dt datetime to the first date just before
    timeframe_start. Use delta_days for advancing the event. Precond:
    start_dt < timeframe_start'''
    delta = timedelta(days = delta_days)
    delta_ord = floor( (timeframe_start.toordinal() - start_dt.toordinal() - 1) / delta_days )
    return (add_delta_dst(start_dt, timedelta(days = delta_days * int(delta_ord))), int(delta_ord))


def generate_event_iterator(comp, timeframe_start, timeframe_end):
    ''' Given an VEVENT object return an iterator with the proper delta (days, weeks, etc)'''
    # Note: timeframe_start and timeframe_end are in UTC
    if comp.name != 'VEVENT': return []
    if 'RRULE' in comp:
        if comp['RRULE']['FREQ'][0] == 'WEEKLY':
            return EventRecurDaysIter(7, comp, timeframe_start, timeframe_end)
        elif comp['RRULE']['FREQ'][0] == 'DAILY':
            return EventRecurDaysIter(1, comp, timeframe_start, timeframe_end)
        elif comp['RRULE']['FREQ'][0] == 'MONTHLY':
            return list()
        elif comp['RRULE']['FREQ'][0] == 'YEARLY':
            return EventRecurYearlyIter(comp, timeframe_start, timeframe_end)
    else:
        return EventSingleIter(comp, timeframe_start, timeframe_end)

class EventSingleIter:
    '''Iterator for non-recurring single events.'''
    def __init__(self, comp, timeframe_start, timeframe_end):
        self.ev_start = get_datetime(comp['DTSTART'].dt)

        # Events with the same begin/end time same do not include
        # "DTEND".
        if "DTEND" not in comp:
            self.ev_end = self.ev_start
        else:
            self.ev_end = get_datetime(comp['DTEND'].dt)

        self.duration = self.ev_end - self.ev_start
        self.result = ()
        if (self.ev_start < timeframe_end and self.ev_end > timeframe_start):
            self.result = ( self.ev_start, self.ev_end, 0)

    def __iter__(self):
        return self

    # Iterate just once
    def __next__(self):
        if self.result:
            aux = self.result
            self.result = ()
        else:
            raise StopIteration
        return aux

class EventRecurDaysIter:
    '''Iterator for daily-based recurring events (daily, weekly).'''
    def __init__(self, days, comp, timeframe_start, timeframe_end):
        self.ev_start = get_datetime(comp['DTSTART'].dt)

        self.ev_end = get_datetime(comp['DTEND'].dt)
        self.duration = self.ev_end - self.ev_start
        self.is_count = False
        self.day_list = list()

        if 'BYDAY' in comp['RRULE']:
            day_num = self.set_day_num(comp['RRULE'])
            self.day_list = [ day_num[day_name] for day_name in comp['RRULE']['BYDAY'] ]
            delta_days = 1
        elif comp['RRULE']['FREQ'][0] == 'WEEKLY':
            self.day_list = [0, 1, 2, 3, 4, 5, 6]
            delta_days = 7
        else:
            self.day_list = [self.ev_start.weekday()]
            delta_days = 1

        if 'COUNT' in comp['RRULE']:
            self.is_count = True
            self.count = comp['RRULE']['COUNT'][0]
        if 'INTERVAL' in comp['RRULE']:
            delta_days *= comp['RRULE']['INTERVAL'][0]
        self.delta = timedelta(delta_days)
        if 'UNTIL' in comp['RRULE']:
            if self.is_count:
                raise "UNTIL and COUNT MUST NOT occur in the same 'recur'"
            self.until_utc = get_datetime(comp['RRULE']['UNTIL'][0]).astimezone(utc)
        else :
            self.until_utc = timeframe_end
        if self.until_utc < timeframe_start:
            self.current = self.until_utc + self.delta # Default value for no iteration
            return
        self.until_utc = min(self.until_utc, timeframe_end)
        if self.ev_start < timeframe_start:
            # advance to timeframe start
            (self.current, counts) = advance_just_before(self.ev_start, timeframe_start, delta_days)
            if self.is_count:
                self.count -= counts
                if self.count < 1: return
            while self.current < timeframe_start:
                self.current = add_delta_dst(self.current, self.delta)
        else:
            self.current = self.ev_start

    def __iter__(self):
        return self

    def next_until(self):
        if self.current > self.until_utc:
            raise StopIteration
        event_aux = self.current
        self.current = add_delta_dst(self.current, self.delta)
        while self.current.weekday() not in self.day_list:
            self.current = add_delta_dst(self.current, self.delta)
        return (event_aux, event_aux.tzinfo.normalize(event_aux + self.duration), 1)

    def next_count(self):
        if self.count < 1:
            raise StopIteration
        self.count -= 1
        event_aux = self.current
        self.current = add_delta_dst(self.current, self.delta)
        while self.current.weekday() not in self.day_list:
            self.current = add_delta_dst(self.current, self.delta)
        return (event_aux, event_aux.tzinfo.normalize(event_aux + self.duration), 1)

    def __next__(self):
        if self.is_count: return self.next_count()
        return self.next_until()

    def set_day_num(self, rrule):
        """The week may start on a different day for each RRULE, so number the
        days accordingly.

        Arguments:
        - rrule -- RRULE line.

        Returns:
        - day_num -- dict of day tags to day number.
        """
        # comp['RRULE']['WKST']
        day_tags = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']

        wkst_s = 'MO' #rrule.get('WKST', ['MO'])[0]
        n = 0
        for i, tag in enumerate(day_tags):
            if tag == wkst_s:
                n = i
                break

        day_num = dict()
        for i in range(7):
            day_num[day_tags[n]] = i
            n = (n + 1) % 7

        return day_num


class EventRecurMonthlyIter:
    pass

class EventRecurYearlyIter:
    def __init__(self, comp, timeframe_start, timeframe_end):
        self.ev_start = get_datetime(comp['DTSTART'].dt)
        self.ev_end = get_datetime(comp['DTEND'].dt)
        self.start = timeframe_start
        self.end = timeframe_end
        self.is_until = False
        if 'UNTIL' in comp['RRULE']:
            self.is_until = True
            self.end = min(self.end, get_datetime(comp['RRULE']['UNTIL'][0]).astimezone(utc))
        if self.end < self.start:
            # Default values for no iteration
            self.i = 0
            self.n = 0
            return
        if 'BYMONTH' in comp['RRULE']:
            self.bymonth = comp['RRULE']['BYMONTH'][0]
        else:
            self.bymonth = self.ev_start.month
        if 'BYMONTHDAY' in comp['RRULE']:
            self.bymonthday = comp['RRULE']['BYMONTHDAY'][0]
        else:
            self.bymonthday = self.ev_start.day
        self.duration = self.ev_end - self.ev_start
        self.years = range(self.start.year, self.end.year + 1)
        if 'COUNT' in comp['RRULE']:
            if self.is_until:
                raise "UNTIL and COUNT MUST NOT occur in the same 'recur'"
            self.years = range(self.ev_start.year, self.end.year + 1)
            del self.years[comp['RRULE']['COUNT'][0]:]
        self.i = 0
        self.n = len(self.years)

    def __iter__(self):
        return self

    def __next__(self):
        if self.i >= self.n: raise StopIteration
        event_aux = self.ev_start.replace(year = self.years[self.i])
        event_aux = event_aux.replace(month = self.bymonth)
        event_aux = event_aux.replace(day = self.bymonthday)
        self.i = self.i + 1;
        if event_aux > self.end: raise StopIteration
        if event_aux < self.start: return self.__next__()
        return (event_aux, event_aux.tzinfo.normalize(event_aux + self.duration), 1)

def convert_ical(ics):
    """Convert icalendar export to org-mode.

    Arguments:
    - ics -- the slup'd ics file.

    Returns:
    - org -- org-mode text.

    """
    # Set the default timezone based on a file.
    if os.path.exists(TIMEZONE_FILE):
        with open(TIMEZONE_FILE, "r") as f:
            tz = f.read().strip()
            global LOCAL_TZ
            LOCAL_TZ = timezone(tz)

    try:
        cal = ical.Calendar.from_ical(ics)
    except Exception as e:
        print("ERROR parsing ical file", file=sys.stderr)
        raise(e)

    org_lines = list()

    now = datetime.now(utc)
    start = now - timedelta( days = WINDOW)
    end = now + timedelta( days = WINDOW)

    # Set default attendee
    attendee = "mailto:" + DEFAULT_ATTENDEE
    for comp in cal.walk():
        if isinstance(comp, ical.Calendar):
            if "X-WR-CALNAME" in comp:
                calendar_name = comp["X-WR-CALNAME"]
                if "@" in calendar_name:
                    attendee = "mailto:" + calendar_name
                    # print("Changed attendee to {}".format(attendee), file=sys.stderr)

        # Check the attendee list -- if the attendee has declined
        # the event then mark it so.
        is_attending = True
        if "ATTENDEE" in comp:
            for event_attendee in comp["ATTENDEE"]:
                if event_attendee == attendee and \
                   event_attendee.params['partstat'] == "DECLINED":
                    is_attending = False
                    break

        event_iter = generate_event_iterator(comp, start, end)
        for comp_start, comp_end, rec_event in event_iter:
            SUMMARY = ""
            if "SUMMARY" in comp:
                SUMMARY = comp['SUMMARY'].to_ical().decode("UTF-8")
                SUMMARY = SUMMARY.replace('\\,', ',')
            if not len(SUMMARY):
                SUMMARY = "(No title)"
            if not is_attending:
                SUMMARY = "Declined: {}".format(SUMMARY)
            org_lines.append("* {}".format(SUMMARY))
            if rec_event and len(RECUR_TAG):
                org_lines.append("{}\n".format(RECUR_TAG))
            org_lines.append("\n")
            if isinstance(comp["DTSTART"].dt, datetime):
                ev_start = orgDatetime(comp_start)
                ev_end = orgDatetime(comp_end)
                if ev_start != ev_end:
                    org_lines.append("{}--{}\n".format(ev_start, ev_end))
                else:
                    org_lines.append("{}\n".format(ev_start))
            else:  # all day event
                org_lines.append("{}--{}\n".format(orgDate(comp_start), orgDate(comp_end - timedelta(days=1))))

            org_lines.append("\n")

            if 'DESCRIPTION' in comp:
                description = '\n'.join(comp['DESCRIPTION'].to_ical().decode("UTF-8").split('\\n'))
                description = description.replace('\\,', ',')
                if len(description) > 0:
                    org_lines.append("- {}\n".format(description))
            if 'LOCATION' in comp:
                location = '\n'.join(comp['LOCATION'].to_ical().decode("UTF-8").split('\\n'))
                location = location.replace('\\,', ',')
                if location.startswith('http'):
                    org_lines.append("- [[{}]]\n".format(location))
                elif len(location) > 0:
                    org_lines.append("- {}\n".format(location))

            org_lines.append("\n")

    return org_lines

if __name__ == "__main__":
    if len(sys.argv) < 2:
        fh = sys.stdin
    else:
        fh = open(sys.argv[1],'rb')

    if len(sys.argv) > 2:
        fh_w = open(sys.argv[2],'wb')
    else:
        fh_w = sys.stdout

    org_lines = convert_ical(fh.read())

    fh_w.write(''.join(org_lines))

    exit(0)
