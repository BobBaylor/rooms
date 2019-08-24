#! /usr/bin/env python
"""
based on this quickstart:
from  https://developers.google.com/google-apps/calendar/quickstart/python
I had to use easy_tools to install instead of pip
    easy_install --upgrade google-api-python-client
And don't forget to put client_secret.json in ~/.credentials
"""
import datetime
import os


USE_STR = """
 --Show room usage in Lone Clone Ski Cabin--
 Usage:
  rooms  [--counts] [--debug] [--guests] [--member=<M>] [--nights] [--offline] [--raw] [--shift=<S>] [--whosup] [--year=<Y>]
  rooms  -h | --help
  rooms  -v | --version
 Options:
  -h --help               Show this screen.
  -c --counts             show how many times each member has used each room
  -d --debug              show stuff
  -g --guests             show nights with guests
  -m --member <M>         show nights with guests for one member (or multiple comma sep - no spaces)
  -n --nights             show who slept where, each night
  -o --offline            don't get the live calendar. Use a test data set
  -r --raw                show the raw calendar events
  -s --shift <S>          move 'today' by integer number of days
  -v --version            show the version
  -w --whosup             show who's up in the next week
  -y --year <Y>           year season starts [default: 2018]
    """

try:
    import httplib2
    from googleapiclient import discovery
    from oauth2client import client
    from oauth2client import tools
    from oauth2client.file import Storage
    import docopt
except ImportError:
    IMP_ERR_STR = '**  Failed import! Type "workon rooms" and try again, Bob  **'
    print('\n%s\n'%('*'*len(IMP_ERR_STR)), IMP_ERR_STR, '\n%s\n'%('*'*len(IMP_ERR_STR)))


# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'

ROOMS = ('in-law', 'master', 'middle', 'bunk', 'loft',)    # assignable rooms in the cabin

""" gPeak is a list of days-of-the-week or dates that guest fee is higher than not.
    The dates are specific to the Julian calendar of each season.
    The year index is the season *start* year.
"""
DAYS_PEAK = {
    '2016': ['Fri', 'Sat']+['12/%2d'%x for x in range(18, 32)]+['01/01', '01/02', '02/19',], #pylint: disable=C0326
    '2017': ['Fri', 'Sat']+['12/%2d'%x for x in range(17, 32)]+['01/01',          '02/18',], #pylint: disable=C0326
    '2018': ['Fri', 'Sat']+['12/%2d'%x for x in range(16, 32)]+['01/01',          '02/17',], #pylint: disable=C0326
    '2019': ['Fri', 'Sat']+['12/%2d'%x for x in range(15, 32)]+['01/01',          '02/16',], #pylint: disable=C0326
    }

GUEST_FEE_MID = 30
GUEST_FEE_PEAK = 35

def get_credentials(opts):
    """Gets valid user credentials from storage.
    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.
    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir, 'calendar-python-quickstart.json')
    if opts['--debug']:
        print('** using credentials at '+credential_path)
    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        # if flags:
        credentials = tools.run_flow(flow, store) #, flags)
        # else: # Needed only for compatibility with Python 2.6
        # credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def get_events(cred, **kwargs):
    """  Wraps the service.events() call
    """
    http = cred.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)      # throws Warning and ImportError
    # print(f'service.events={dir(service.events)}')
    """ #pylint: disable=E1101  pylint thinks there is no events()... but there is
    """        #pylint: disable=W0105
    cal_events = service.events().list(**kwargs).execute() #pylint: disable=E1101
    return cal_events.get('items', [])


def get_events_raw(credentials, opts):
    """  Grab the entire calendar for the season from Dec 1 to May 1
        ctor the dicts with night, leave, summary, description keys.
        nightShort is added later by more_dates()
    """
    day0 = datetime.datetime(int(opts['--year']), 12, 1).isoformat()+'Z'
    day1 = datetime.datetime(int(opts['--year']) + 1, 5, 1).isoformat()+'Z'
    events = get_events(
        credentials,
        timeMin=day0,
        timeMax=day1,
        singleEvents=True,
        orderBy='startTime',
        calendarId="primary")
    return events


def events_to_raw_dates(events, opts):        #pylint: disable=W0613
    """ make a new list: dates_raw
        that has only the fields I care about: night, leave, member, and room
    """
    dates_raw = []
    for event in events:
        day_dict = {}
        day_dict['night'] = event['start'].get('dateTime', event['start'].get('date'))[:10]
        day_dict['leave'] = event['end'].get('dateTime', event['end'].get('date'))[:10]
        # summary is the member name, description has room assignment
        for k in (('summary', 'member',), ('description', 'where', ),):
            try:
                day_dict[k[1]] = event[k[0]].strip()
            except KeyError:
                day_dict[k[1]] = ''
        dates_raw += [day_dict]
    # dates_raw[] is a list of
    # {'night':'2016-12-15', 'summary':'Logan', 'where':'master', 'leave':'2016-12-16',}
    return dates_raw


def expand_multi_nights(dates_raw):
    """ expand multi-night stays into individual nights
    """
    dates_multi_night = []
    for one_date in dates_raw:             # add day of week
        one_date['date'] = datetime.datetime.strptime(one_date['night'], '%Y-%m-%d')
        nights = (datetime.datetime.strptime(one_date['leave'], '%Y-%m-%d').date()
                  - one_date['date'].date()).days - 1
        for i in range(nights):
            new_date = one_date.copy()
            new_date['date'] = datetime.datetime.strptime(one_date['night'], '%Y-%m-%d') \
                + datetime.timedelta(days=i+1)
            dates_multi_night += [new_date]
    dates_raw += dates_multi_night


def add_day_of_week(dates_raw):
    """ Use 'date of "2016-12-23" to make night_abrev of "Fri 12/23" """
    for one_date in dates_raw:

        one_date['night_abrev'] = one_date['date'].strftime('%a %m/%d')
    dates_raw = dates_raw.sort(key=lambda x: x['date'])


def fix_spelling(dates_raw, opts):      #pylint: disable=W0613
    """  Common data entry errors: fix the dict and flag it for me to fix the google calendar
    """
    for date in dates_raw:
        for field, wrong, right in [
                ('where', 'inlaw', 'in-law',), ('member', 'Sarah', 'Sara',),
            ]:
            if wrong in date[field]:
                print('** spellcheck:', date)
                date[field] = date[field].replace(wrong, right)    #  in-law, not inlaw, e.g.
        if 'Glen ' in date['member']: # special treatment for missing n in Glenn
            print('** spellcheck:', date)
            date['member'] = date['summary'].replace('Glen', 'Glenn')    #  two n in Glenn
    return dates_raw


def select_dates(dates_raw, opts, day0=None, day1=None):
    """ return a subset of the events from today+day0 to today+day1
        None in day0 means begining of current ski season
        None in day1 means end of current ski season
    """
    dt_today = datetime.datetime.utcnow()
    if opts['--shift']:
        dt_today += datetime.timedelta(days=int(opts['--shift']))
    season_start = datetime.datetime(int(opts['--year']), 12, 1)  # season starts Dec 1
    season_end = datetime.datetime(1+int(opts['--year']), 5, 1)   # season ends May 1
    date0 = season_start if day0 is None else dt_today + datetime.timedelta(days=day0)
    date1 = season_end if day1 is None else dt_today + datetime.timedelta(days=day1)
    # print 'select',date0.strftime('%a %m/%d'), date1.strftime('%a %m/%d')
    return [e for e in dates_raw if bool(date0 <= e['date'] <= date1)]


def show_raw(dates_raw, bdict=False):
    """  Debugging aid
         bdict=False is formated for humans. True is formatted to copy into code
    """
    if bdict:
        print('** dates_raw')
        print('{'+ '},\n{'.join([', '.join(
            ["'%s':'%s'"%(n, e[n]) for n in ('night_abrev', 'member', 'where', 'leave')]
            ) for e in dates_raw]) +'}')
    else:
        print('')
        print('%10s %20s %-30s'%('', '', 'Raw Calendar',)+' '.join(['%10s'%r for r in ROOMS]))
        for date in dates_raw:
            print('%10s %-20s %-30s'%(date['night_abrev'],
                                      date['member'],
                                      date['where'].strip()) +
                  ' '.join(['%10s'%date[room] for room in ROOMS]))


def put_members_in_rooms(dates_raw, opts):  #pylint: disable=W0613
    """ add ['middle']='Logan', ['bunk']='' etc
        so that all dates have all rooms as keys, w/ or w/o a member
    """
    for date in dates_raw:
        for room in ROOMS:
            if room in date['where'].lower():
                date[room] = gevent_to_member_name(date)   # just the first name
            else:
                date[room] = ''


def show_guest_fees(dates_raw, opts):
    """ Calculate guest fees based on the cabin rules
        (Fri, Sat, and holiday  nights are "Peak" rates)
        note: Special rule for Jon and Dina's daughter Sam who doesn't pay guest fee
        but does take a room.
    """
    # m = '' if not opts['--member'] else opts['--member']
    # print '\n%10s %20s %-20s'
    #           %('%s-%2d'%(opts['--year'], int(opts['--year'])-1999),'Guests Calendar', m)
    print('\n%10s %20s '%('%s-%2d'%(opts['--year'], int(opts['--year'])-1999), 'Guests Calendar'))
    guest_fee_owed, guest_fee_accum, guest_nights_accum = 0, 0, 0
    deadbeats = {}
    for event in dates_raw:
        if '+' in event['member'] and 'Z+1' not in event['member']:
            # guests but not Z+1 (Sam). Enter "Z +1" to indicate not Sam (chargable)
            guest_fee = GUEST_FEE_PEAK if any([x in event['night_abrev'] \
                for x in DAYS_PEAK[opts['--year']]]) else GUEST_FEE_MID
            guest_count = int(event['member'].split('+')[1][0])
            guest_fee *= guest_count
            guest_fee_accum += guest_fee
            guest_nights_accum += guest_count
            if '$' in event['member']:
                payment = ''
            else:
                payment = 'OWES FOR'
                guest_fee_owed += guest_fee
                member_name = event['member'].split('+')[0]
                if member_name in deadbeats:
                    deadbeats[member_name] += [(event['night_abrev'], guest_fee)]
                else:
                    deadbeats[member_name] = [(event['night_abrev'], guest_fee)]
                   
            # if not any([c in e['member'] for c in ('Erin','Jon','Bob ',)]):
            print('%-8s %10s %4d %-20s %-20s'%
                  ( payment, 
                    event['night_abrev'], 
                    guest_fee, 
                    event['member'], 
                    event['where']))
    print('Total %d guest-nights and $%d in fees'%(guest_nights_accum, guest_fee_accum))
    if deadbeats:
        print('\nMembers owing guest fees:')
        for one_beat in deadbeats:
            beat_total = sum([x[1] for x in deadbeats[one_beat]])
            beat_dates = [x[0].split()[1] for x in deadbeats[one_beat]]
            print(f'{one_beat} owes ${beat_total} for %s'%", ".join(beat_dates))



def show_whos_up(dates_raw, opts):
    """ This output gets pasted into my periodic emails
        who room: day date, date, date [, room: date, date]
        I generate a dict, keyed on the member, with values of a list:
        [order#, member, (rooms,day),(rooms,day),...)]
        I repeat the rooms for each day because it can change during a stay.
    """
    print("Here's who I've heard from:")
    dates_raw = select_dates(dates_raw, opts, -2, 7)

    members_dict = {}
    p_ord = 0
    for event in dates_raw:
        member = event['member']
        try:
            members_dict[member] += [(event['where'], event['night_abrev']),]
        except KeyError:
            members_dict[member] = [p_ord, member, (event['where'], event['night_abrev']),]
            p_ord += 1

    # members_dict['Bob'] = [0, 'Bob', ('middle','Mon 12/24'), ('middle','Tue 12/25'), ]
    # sort by the begining night of stay (the p_ord value, above)
    for member_ass in sorted(list(members_dict.items()), key=lambda k_v: k_v[1][0]):
        # member_ass =  ('Bob', [0, 'Bob', ('middle','Mon 12/24'), ('middle','Tue 12/25'), ])
        day_tup = member_ass[1][2:]    #  [('middle','Mon 12/24'), ('middle','Tue 12/25'),]
        room = day_tup[0][0]     # save the room so we only print it when it changes
        print('%20s %7s: %s,'%(member_ass[0], day_tup[0][0], day_tup[0][1]), end=' ')
        for a_day in day_tup[1:]:
            if a_day[0] == room:
                print(a_day[1].split()[1]+',', end=' ')
            else:
                print('%7s: %s,'%(a_day[0], a_day[1].split()[1]), end=' ')
                room = a_day[0] # save the room again
        print('')


def show_missing_rooms(dates_raw, opts):
    """ Flag the data entry error condition: all members in the cabin on a given night
        must be in a room.
        Otherwise, the count will be wrong and the priority system breaks down.
    """
    dates_raw = select_dates(dates_raw, opts, None, 0)
    missing_rooms_str = []
    for date in dates_raw:
        if not date['where']:        # catch members in cabin but not assigned to any room
            missing_rooms_str += \
                ['** On %s, where did %s sleep?'%(date['night_abrev'], date['member'])]
    if missing_rooms_str:
        print('%10s %20s %-20s'%('', "Missing rooms", ''))
        print('\n'.join(missing_rooms_str))


def show_nights(dates_past, opts):      #pylint: disable=W0613
    """ colapse the raw calendar to show each night on one line
        date,      inlaw, master, middle,  bunk,  loft
                   who,   who,    who,     who,   who
    """
    dates_combo = [dates_past[0].copy()]
    for date in dates_past[1:]:
        if dates_combo[-1]['night_abrev'] not in date['night_abrev']:        # new date
            dates_combo += [date.copy()]
        else:
            for room in ROOMS:
                sep = ',' if date[room] and dates_combo[-1][room] else ''
                dates_combo[-1][room] = dates_combo[-1][room]+sep+date[room]
    # dates_combo[] is {'night':'2016-12-15', 'member':'Logan', 'where':'master',
    #       'master':'Logan', 'in-law':'Bob', 'middle':'Mark', ...}
    print('\n%10s '%('Nights')+' '.join(['%16s'%room for room in ROOMS]))
    for date in dates_combo:
        print('%10s '%(date['night_abrev'])+' '.join(['%16s'%date[room] for room in ROOMS]))


def count_members_in_rooms(dates_raw, opts):    #pylint: disable=W0613
    """ Construct the memberCount dict { 'Bob': {'inlaw': count, 'master' count, ...}...}
        for season up to today.
    """
    member_counts = {}
    # init the member_counts with the first name {rooms}
    for event in dates_raw:
        member_counts[gevent_to_member_name(event)] = {room:0 for room in ROOMS+('total',)}
    # add ['middle']='Logan' or blank for all rooms
    for event in dates_raw:
        # print '*****',gevent_to_member_name(event),
        #       '+++', event['member'], '====', event['where'], '*****'
        member_counts[gevent_to_member_name(event)]['total'] = \
            member_counts[gevent_to_member_name(event)]['total']+1
        for room in ROOMS:
            if room in event['where'].lower():
                try:
                    member_counts[event[room]][room] = member_counts[event[room]][room]+1
                except KeyError as why:
                    msg = getattr(why, 'message', repr(why))
                    print(f"FAILED room={room}\nevent={event}\n{msg}\n")
                    print(f"member_counts={member_counts}\n")

    return member_counts


def show_room_counts(member_counts):
    """     Room priority is based on which member has used the room the least.
        display:
            date, who, where    inlaw, master, middle,  bunk,  loft
            total who,          count,  count,  count, count, count
    """
    # show how many times each member has slept in each room
    print('\n%4s%10s'%('', 'Counts')+' '.join(['%8s'%room for room in ROOMS]))
    for member in member_counts:
        print('%4d%10s'%(member_counts[member]['total'], member)+
              ' '.join(['%8s'%('%d'%member_counts[member][room]
                               if member_counts[member][room]
                               else '') for room in ROOMS]))


def gevent_to_member_name(event):
    """ Each calendar event has only one member name as the first word in the summary.
        extract the member name ignoring whatever else is in the summary.
        Should be run *after* fix_spelling()
    """
    member = event['member'].split()[0].replace(',', '')
    return member


def main(opts):
    """ the program
    """

    # ignore line-to-long
    #pylint: disable=C0301
    if opts['--offline']:
        dates_raw = [
            {'leave': '2018-12-02', 'member': 'Bob', 'where': 'master', 'night': '2018-12-01'},
            {'leave': '2018-12-02', 'member': 'James, Jean', 'where': 'in-law', 'night': '2018-12-01'},
            {'leave': '2018-12-02', 'member': 'Peter', 'where': 'middle', 'night': '2018-12-01'},
            {'leave': '2018-12-06', 'member': 'James, Jean', 'where': 'in-law', 'night': '2018-12-02'},
            {'leave': '2018-12-03', 'member': 'Peter', 'where': 'middle', 'night': '2018-12-02'},
            {'leave': '2018-12-09', 'member': 'Bob', 'where': 'master', 'night': '2018-12-08'},
            {'leave': '2018-12-14', 'member': 'Jon', 'where': 'loft', 'night': '2018-12-10'},
            {'leave': '2018-12-24', 'member': 'James, Jean', 'where': 'in-law', 'night': '2018-12-14'},
            {'leave': '2018-12-23', 'member': 'Dina', 'where': 'master', 'night': '2018-12-20'},
            {'leave': '2018-12-30', 'member': 'Jon, Sam, Z', 'where': 'bunk', 'night': '2018-12-20'},
            {'leave': '2018-12-26', 'member': 'Bob +1', 'where': 'middle', 'night': '2018-12-22'},
            {'leave': '2018-12-28', 'member': 'Erin +1', 'where': 'master', 'night': '2018-12-23'},
            {'leave': '2018-12-26', 'member': 'Dina', 'where': 'in-law', 'night': '2018-12-23'},
            {'leave': '2018-12-28', 'member': 'Peter', 'where': 'in-law', 'night': '2018-12-25'},
            {'leave': '2018-12-30', 'member': 'Dina', 'where': 'middle', 'night': '2018-12-26'},
            {'leave': '2019-01-12', 'member': 'James, Jean', 'where': 'middle', 'night': '2019-01-09'},
            {'leave': '2019-01-13', 'member': 'Bob +1', 'where': 'master', 'night': '2019-01-12'},
            {'leave': '2019-01-13', 'member': 'James, Jean +2', 'where': 'middle, bunk', 'night': '2019-01-12'},
            {'leave': '2019-01-17', 'member': 'Jon', 'where': 'in-law', 'night': '2019-01-13'},
            {'leave': '2019-01-16', 'member': 'Jean, James +1', 'where': 'middle, bunk', 'night': '2019-01-13'},
            {'leave': '2019-01-18', 'member': 'Peter', 'where': 'master', 'night': '2019-01-15'},
            {'leave': '2019-01-21', 'member': 'Jon +1 +Z', 'where': 'bunk', 'night': '2019-01-18'},
            {'leave': '2019-01-21', 'member': 'Dina', 'where': 'in-law', 'night': '2019-01-18'},
            {'leave': '2019-01-22', 'member': 'Glenn', 'where': 'master', 'night': '2019-01-18'},
            {'leave': '2019-01-20', 'member': 'Erin', 'where': 'loft', 'night': '2019-01-18'},
            {'leave': '2019-01-20', 'member': 'Bob +1', 'where': 'middle', 'night': '2019-01-19'},
            {'leave': '2019-01-25', 'member': 'James', 'where': 'in-law', 'night': '2019-01-21'},
            {'leave': '2019-01-27', 'member': 'Mark +1', 'where': 'middle, loft', 'night': '2019-01-25'},
            {'leave': '2019-01-27', 'member': 'Glenn', 'where': 'in-law', 'night': '2019-01-25'},
            {'leave': '2019-02-01', 'member': 'James', 'where': 'bunk', 'night': '2019-01-25'},
            {'leave': '2019-01-27', 'member': 'Bob', 'where': 'master', 'night': '2019-01-26'},
            {'leave': '2019-02-01', 'member': 'Jon', 'where': 'in-law', 'night': '2019-01-27'},
            {'leave': '2019-02-06', 'member': 'Mark', 'where': 'master', 'night': '2019-02-04'},
            {'leave': '2019-02-08', 'member': 'Jon', 'where': 'in-law', 'night': '2019-02-05'},
            {'leave': '2019-02-10', 'member': 'Mark', 'where': '', 'night': '2019-02-08'},
            {'leave': '2019-02-10', 'member': 'Bob', 'where': '', 'night': '2019-02-09'},
            ]
    else:
        credentials = get_credentials(opts)
        events_raw = get_events_raw(credentials, opts)
        # print('events', ',\n'.join([repr(x) for x in events_raw]))
        # translate 'start' and 'end' to 'night' and 'leave'
        # translate 'summary' and 'description' to 'member' and 'where'
        dates_raw = events_to_raw_dates(events_raw, opts)
        # print ',\n'.join([repr(x) for x in dates_raw])
    #pylint: enable=C0301

    # dates_raw is a list of dicts. The dates_raw dicts need a few more fields...
    expand_multi_nights(dates_raw)  # add more date dicts to fill in between night and leaving
    add_day_of_week(dates_raw)      # add 'night_abrev' field to the date dicts

    dates_raw = fix_spelling(dates_raw, opts)  # catch data entry errors

    if opts['--debug']:
        show_raw(dates_raw, True)

    put_members_in_rooms(dates_raw, opts)  # to each date, add entries for each room

    # done filling the dicts... time to start printing!
    # dates_raw has whole season ----------------------
    dates_past = select_dates(dates_raw, opts, None, 0)
    # dates_raw[] is now a list of  {'night':'2016-12-15', 'member':'Peter',
    #           'where':'master', 'master':'Peter', 'in-law':'', 'midle':'', ...}
    # dates_past[] has only the dates to the present
    show_missing_rooms(dates_past, opts)    # always show any members I failed to assign to a room

    if opts['--whosup']:
        show_whos_up(dates_raw, opts)

    if opts['--raw']:
        show_raw(dates_raw, False)

    if opts['--guests']:
        show_guest_fees(dates_past, opts)

    if opts['--member']:
        for one_member in opts['--member'].split(','):
            dates_past_member = [x for x in dates_past if one_member in x['member'].split()]
            show_guest_fees(dates_past_member, opts)

    if opts['--nights']:
        show_nights(dates_past, opts)

    if opts['--counts']:
        member_counts = count_members_in_rooms(dates_past, opts)
        # member_counts{} = {'Bob':{'in-law':1, 'master':0, 'middle':0,
        #           'bunk':1,  'loft':0}, 'Mark:{'master':1,...},...}
        show_room_counts(member_counts)


if __name__ == '__main__':
    OPTS = docopt.docopt(USE_STR, version='0.0.9')
    main(OPTS)
