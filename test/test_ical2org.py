import datetime
from freezegun import freeze_time
import pytz
import sys
import unittest

try:
    import ical2org
except ImportError as e:
    print('Import error:', str(e), file=sys.stderr)
    sys.exit(1)

class TestIcal2Org(unittest.TestCase):
    def setUp(self):
        self.ics_string_tpl = """\
BEGIN:VCALENDAR
PRODID:-//Google Inc//Google Calendar 70.9054//EN
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Personal
X-WR-TIMEZONE:America/Los_Angeles
BEGIN:VTIMEZONE
TZID:America/Los_Angeles
X-LIC-LOCATION:America/Los_Angeles
BEGIN:DAYLIGHT
TZOFFSETFROM:-0800
TZOFFSETTO:-0700
TZNAME:PDT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:-0700
TZOFFSETTO:-0800
TZNAME:PST
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE
BEGIN:VTIMEZONE
TZID:America/Chicago
X-LIC-LOCATION:America/Chicago
BEGIN:DAYLIGHT
TZOFFSETFROM:-0600
TZOFFSETTO:-0500
TZNAME:CDT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:-0500
TZOFFSETTO:-0600
TZNAME:CST
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE
BEGIN:VEVENT
{event}
END:VEVENT
END:VCALENDAR
"""

    @freeze_time("2016-10-22 19:00:00")
    def test_zero_duration_event(self):
        """When the start and end times are the same, the "DTEND" line is not
        included.
        """
        ics_string = self.ics_string_tpl.format(event = """\
DTSTART:20161022T230000Z
DTSTAMP:20160904T144133Z
CREATED:20160903T055100Z
DESCRIPTION:
LAST-MODIFIED:20160903T055101Z
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Event 1
""")

        org_lines = ical2org.convert_ical(ics_string)

        self.assertEqual(org_lines[2].strip(),
                         "<2016-10-22 Sat 16:00>")

    @freeze_time("2016-10-22 19:00:00")
    def test_default_timezone(self):
        """The event time will use the default timezone from the calendar when
        not specified.

        """
        ics_string = self.ics_string_tpl.format(event = """\
DTSTART:20161022T190000Z
DTEND:20161022T200000Z
DTSTAMP:20160904T144133Z
CREATED:20160903T055100Z
DESCRIPTION:
LAST-MODIFIED:20160903T055101Z
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Event 1
""")

        org_lines = ical2org.convert_ical(ics_string)

        self.assertEqual(org_lines[2].strip(),
                         "<2016-10-22 Sat 12:00>--<2016-10-22 Sat 13:00>")

    @freeze_time("2016-10-22 19:00:00")
    def test_specified_timezone(self):
        """The event time will use a specified timezone.
        """
        ics_string = self.ics_string_tpl.format(
            event = """\
DTSTART;TZID=Europe/Paris:20161022T230000Z
DTEND;TZID=Europe/Paris:20161023T020000Z
DTSTAMP:20160904T144133Z
CREATED:20160903T055100Z
DESCRIPTION:
LAST-MODIFIED:20160903T055101Z
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Event 1
""")

        org_lines = ical2org.convert_ical(ics_string)

        self.assertEqual(org_lines[2].strip(),
                         "<2016-10-22 Sat 14:00>--<2016-10-22 Sat 17:00>")

    @freeze_time("2016-11-17 19:00:00")
    def test_weekly_duration_event_with_bydays(self):
        """When specific days are set for weekly recurring events, only events
        for the specified days will be generated.
        """
        ics_string = self.ics_string_tpl.format(event = """
DTSTART;TZID=America/Los_Angeles:20161117T100000
DTEND;TZID=America/Los_Angeles:20161117T101500
RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR
CREATED:20161019T223911Z
LAST-MODIFIED:20161117T181500Z
DESCRIPTION:
SEQUENCE:1
STATUS:CONFIRMED
SUMMARY:Event 1
""")

        org_lines = ical2org.convert_ical(ics_string)

        # This is gross, but I'm taking the easy path instead of doing
        # a bunch of date math.
        self.assertEqual(org_lines[2].strip(),
                         '<2016-11-17 Thu 10:00>--<2016-11-17 Thu 10:15>')
        self.assertEqual(org_lines[7].strip(),
                         '<2016-11-18 Fri 10:00>--<2016-11-18 Fri 10:15>')
        self.assertEqual(org_lines[12].strip(),
                         '<2016-11-21 Mon 10:00>--<2016-11-21 Mon 10:15>')
        self.assertEqual(org_lines[17].strip(),
                         '<2016-11-22 Tue 10:00>--<2016-11-22 Tue 10:15>')
        self.assertEqual(org_lines[22].strip(),
                         '<2016-11-23 Wed 10:00>--<2016-11-23 Wed 10:15>')
        self.assertEqual(org_lines[27].strip(),
                         '<2016-11-24 Thu 10:00>--<2016-11-24 Thu 10:15>')
        self.assertEqual(org_lines[32].strip(),
                         '<2016-11-25 Fri 10:00>--<2016-11-25 Fri 10:15>')
        self.assertEqual(org_lines[37].strip(),
                         '<2016-11-28 Mon 10:00>--<2016-11-28 Mon 10:15>')
        self.assertEqual(org_lines[42].strip(),
                         '<2016-11-29 Tue 10:00>--<2016-11-29 Tue 10:15>')


    @freeze_time("2018-10-07 00:00:00")
    def test_single_zulu_event(self):
        """A single event with Z dates will show up at the correct time in the
        calendar.
        """
        ics_string = self.ics_string_tpl.format(event = """\
DTSTART:20181008T020000Z
DTEND:20181008T022000Z
DTSTAMP:20181008T121345Z
UID:c4s3ep9j68pjcb9k75j3ib9k6tim6bb1ckr32b9n60pj2p1l6ormcd32c4@google.com
CREATED:20181007T155551Z
DESCRIPTION:
LAST-MODIFIED:20181007T155551Z
LOCATION:
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:SpaceX launch
TRANSP:OPAQUE
BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:This is an event reminder
TRIGGER:-P0DT0H5M0S
END:VALARM
""")
        org_lines = ical2org.convert_ical(ics_string)

        self.assertEqual(org_lines[2].strip(),
                         "<2018-10-07 Sun 19:00>--<2018-10-07 Sun 19:20>")

    @freeze_time("2018-10-07 00:00:00")
    def test_timzone_offset(self):
        """This event shows up an hour later than it is.
        """
        ics_string = self.ics_string_tpl.format(event = """\
CREATED:20171109T045108Z
UID:B91CC1E3-34AA-4ACC-A45F-D54A4FEE92C3
DTEND:20181009T034700Z
TRANSP:TRANSPARENT
X-APPLE-TRAVEL-ADVISORY-BEHAVIOR:AUTOMATIC
SUMMARY:⚫ New Moon
DTSTART:20181009T034700Z
DTSTAMP:20141228T213726Z
CATEGORIES:Moon,New Moon
SEQUENCE:0
URL;VALUE=URI:http://en.wikipedia.org/wiki/Moon_phases
""")
        org_lines = ical2org.convert_ical(ics_string)

        self.assertEqual(org_lines[2].strip(), "<2018-10-08 Mon 20:47>")

    @freeze_time("2020-04-29 00:00:00")
    def test_rrule_start_day(self):
        """The RRULE can specify a different day than when it starts.
        """
        ics_string = self.ics_string_tpl.format(event = """\
DTSTART;TZID=America/Los_Angeles:20200430T140000
DTEND;TZID=America/Los_Angeles:20200430T150000
RRULE:FREQ=WEEKLY;WKST=SU;COUNT=5;BYDAY=TH
DTSTAMP:20200502T021356Z
UID:195pd5fgk89kf3ace89qekbbn6@google.com
CREATED:20200430T034521Z
DESCRIPTION:
LAST-MODIFIED:20200430T210550Z
LOCATION:
SEQUENCE:1
STATUS:CONFIRMED
SUMMARY:Cloud Computing Cost Estimation Presentation Series
TRANSP:OPAQUE
""")

        org_lines = ical2org.convert_ical(ics_string)

        self.assertEqual(org_lines[2].strip(), "<2020-04-30 Thu 14:00>--<2020-04-30 Thu 15:00>")
        self.assertEqual(org_lines[7].strip(), "<2020-05-07 Thu 14:00>--<2020-05-07 Thu 15:00>")
        self.assertEqual(org_lines[12].strip(), "<2020-05-14 Thu 14:00>--<2020-05-14 Thu 15:00>")
        self.assertEqual(org_lines[17].strip(), "<2020-05-21 Thu 14:00>--<2020-05-21 Thu 15:00>")
        self.assertEqual(org_lines[22].strip(), "<2020-05-28 Thu 14:00>--<2020-05-28 Thu 15:00>")


    @freeze_time("2020-05-12 00:00:00")
    def test_rrule_2week_interval(self):
        """The RRULE can specify two week intervals.
        """
        ics_string = self.ics_string_tpl.format(event = """\
DTSTART;TZID=America/New_York:20200513T130000
DTEND;TZID=America/New_York:20200513T140000
RRULE:FREQ=WEEKLY;WKST=SU;UNTIL=20201008T035959Z;INTERVAL=2;BYDAY=WE
DTSTAMP:20200502T062047Z
UID:3v0tb4ra2fnk8cusgif78bu23n@google.com
CREATED:20200430T225453Z
DESCRIPTION:<a href="https://stsci.webex.com/stsci/j.php?MTID=m937a574e2f26
 f852e40f8b1df261d553">https://stsci.webex.com/stsci/j.php?MTID=m937a574e2f2
 6f852e40f8b1df261d553</a><br>Meeting number (access code): 909 070 777<br>M
 eeting password: sdUC3tkFA28 <br>Join by phone<br>Tap to call in from a mob
 ile device (attendees only)<br><br>+1-510-210-8882 USA toll<br><br>http://b
 it.ly/NAVO-Python-WG-Notes
LAST-MODIFIED:20200430T225705Z
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:NASANavo Python WG
TRANSP:TRANSPARENT
""")

        org_lines = ical2org.convert_ical(ics_string)

        self.assertEqual(org_lines[2].strip(), "<2020-05-13 Wed 10:00>--<2020-05-13 Wed 11:00>")
        self.assertEqual(org_lines[8].strip(), "<2020-05-27 Wed 10:00>--<2020-05-27 Wed 11:00>")
        self.assertEqual(org_lines[14].strip(), "<2020-06-10 Wed 10:00>--<2020-06-10 Wed 11:00>")
        self.assertEqual(org_lines[20].strip(), "<2020-06-24 Wed 10:00>--<2020-06-24 Wed 11:00>")
        self.assertEqual(org_lines[26].strip(), "<2020-07-08 Wed 10:00>--<2020-07-08 Wed 11:00>")
        self.assertEqual(org_lines[32].strip(), "<2020-07-22 Wed 10:00>--<2020-07-22 Wed 11:00>")
        self.assertEqual(org_lines[38].strip(), "<2020-08-05 Wed 10:00>--<2020-08-05 Wed 11:00>")

    @freeze_time("2018-10-07 00:00:00")
    def test_http_location_insertion(self):
        """If location has a URL (http.*) then format it for org-mode.
        """
        ics_string = self.ics_string_tpl.format(event = """\
DTSTART:20181008T020000Z
DTEND:20181008T022000Z
DTSTAMP:20181008T121345Z
UID:c4s3ep9j68pjcb9k75j3ib9k6tim6bb1ckr32b9n60pj2p1l6ormcd32c4@google.com
CREATED:20181007T155551Z
DESCRIPTION:
LAST-MODIFIED:20181007T155551Z
LOCATION:https://stsci.webex.com/stsci/j.php?MTID=m937a574e2f26f852e40f8b1d
 f261d553
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:SpaceX launch
TRANSP:OPAQUE
BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:This is an event reminder
TRIGGER:-P0DT0H5M0S
END:VALARM
""")
        org_lines = ical2org.convert_ical(ics_string)

        self.assertEqual(org_lines[4].strip(),
                         "- [[https://stsci.webex.com/stsci/j.php?MTID=m937a574e2f26f852e40f8b1df261d553]]")

    @freeze_time("2018-10-07 00:00:00")
    def test_non_http_location_insertion(self):
        """If location has a URL (http.*) then format it for org-mode.
        """
        ics_string = self.ics_string_tpl.format(event = """\
DTSTART:20181008T020000Z
DTEND:20181008T022000Z
DTSTAMP:20181008T121345Z
UID:c4s3ep9j68pjcb9k75j3ib9k6tim6bb1ckr32b9n60pj2p1l6ormcd32c4@google.com
CREATED:20181007T155551Z
DESCRIPTION:
LAST-MODIFIED:20181007T155551Z
LOCATION:1700 Stadium Way\, Los Angeles\, CA 90017
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:SpaceX launch
TRANSP:OPAQUE
BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:This is an event reminder
TRIGGER:-P0DT0H5M0S
END:VALARM
""")
        org_lines = ical2org.convert_ical(ics_string)

        self.assertEqual(org_lines[4].strip(), "- 1700 Stadium Way, Los Angeles, CA 90017")
