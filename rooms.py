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
    The year index is the season start year.
"""
DAYS_PEAK = {
    '2016': ['Fri', 'Sat']+['12/%2d'%x for x in range(18, 32)]+['01/01', '01/02', '02/19',], #pylint: disable=C0326
    '2017': ['Fri', 'Sat']+['12/%2d'%x for x in range(17, 32)]+['01/01',          '02/18',], #pylint: disable=C0326
    '2018': ['Fri', 'Sat']+['12/%2d'%x for x in range(16, 32)]+['01/01',          '02/18',], #pylint: disable=C0326
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
    # print(f'service={dir(service)}')
    cal_events = service.events().list(**kwargs).execute() #pylint: disable=E1101
    return cal_events.get('items', [])


def get_season(credentials, opts):
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
    dates_raw = []
    for event in events:
        # e = collections.OrderedDict()
        day_dict = {}
        day_dict['night'] = event['start'].get('dateTime', event['start'].get('date'))[:10]
        day_dict['leave'] = event['end'].get('dateTime', event['end'].get('date'))[:10]
        # summary is the member name, description has room assignment
        for k in ('summary', 'description',):
            try:
                day_dict[k] = event[k].strip()
            except KeyError:
                day_dict[k] = ''
        dates_raw += [day_dict]
    # dates_raw[] is a list of
    # {'night':'2016-12-15', 'summary':'Logan', 'description':'master', 'leave':'2016-12-16',}
    return dates_raw


def more_dates(dates_raw):
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
    for one_date in dates_raw:             # add day of week
        # turn "2016-12-23" into "Fri 12/23"
        one_date['nightShort'] = one_date['date'].strftime('%a %m/%d')
    dates_raw = dates_raw.sort(key=lambda x: x['date'])


def fix_spelling(dates_raw, opts):      #pylint: disable=W0613
    """  Common data entry errors: fix the dict and flag it for me to fix the google calendar
    """
    for date in dates_raw:
        for field, wrong, right in [
                ('description', 'inlaw', 'in-law',), ('summary', 'Sarah', 'Sara',),
            ]:
            if wrong in date[field]:
                print('** spellcheck:', date)
                date[field] = date[field].replace(wrong, right)    #  in-law, not inlaw, e.g.
        if 'Glen ' in date['summary']: # special treatment for missing n in Glenn
            print('** spellcheck:', date)
            date['summary'] = date['summary'].replace('Glen', 'Glenn')    #  two n in Glenn
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
            ["'%s':'%s'"%(n, e[n]) for n in ('nightShort', 'summary', 'description', 'leave')]
            ) for e in dates_raw]) +'}')
    else:
        print('')
        print('%10s %20s %-30s'%('', '', 'Raw Calendar',)+' '.join(['%10s'%r for r in ROOMS]))
        for date in dates_raw:
            print('%10s %-20s %-30s'%(date['nightShort'],
                                      date['summary'],
                                      date['description'].strip()) +
                  ' '.join(['%10s'%date[room] for room in ROOMS]))


def put_members_in_rooms(dates_raw, opts):  #pylint: disable=W0613
    """ add ['middle']='Logan' or blank for all rooms
    """
    for date in dates_raw:
        for room in ROOMS:
            if room in date['description'].lower():
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
    guest_fee_accum, guest_nights_accum = 0, 0
    for event in dates_raw:
        if '+' in event['summary'] and 'Z+1' not in event['summary']:
            # guests but not Z+1 (Sam). Enter "Z +1" to indicate not Sam (chargable)
            guest_fee = GUEST_FEE_PEAK if any([x in event['nightShort'] \
                for x in DAYS_PEAK[opts['--year']]]) else GUEST_FEE_MID
            guest_count = int(event['summary'].split('+')[1])
            guest_fee *= guest_count
            guest_fee_accum += guest_fee
            guest_nights_accum += guest_count
            # if not any([c in e['summary'] for c in ('Erin','Jon','Bob ',)]):
            print('%10s %4d %-20s %-20s'%
                  (event['nightShort'], guest_fee, event['summary'], event['description']))
    print('Total %d guest-nights and $%d in fees'%(guest_nights_accum, guest_fee_accum))


def show_whos_up(dates_raw, opts):
    """ This output gets pasted into my periodic emails
        who room: day date, date, date [, room: date, date]
    """
    print("Here's who I've heard from:")
    dates_raw = select_dates(dates_raw, opts, -2, 7)

    members_dict = {}
    p_ord = 0
    for event in dates_raw:
        member = event['summary']
        try:
            members_dict[member] += [(event['description'], event['nightShort']),]
        except KeyError:
            members_dict[member] = [p_ord, member, (event['description'], event['nightShort']),]
            p_ord += 1

    # members_dict['Bob'] = [0, 'Bob', ('middle','Mon 12/24'), ('middle','Tue 12/25'), ]
    # sort by the begining night of stay
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
        if not date['description']:        # catch members in cabin but not assigned to any room
            missing_rooms_str += \
                ['** On %s, where did %s sleep?'%(date['nightShort'], date['summary'])]
    if missing_rooms_str:
        print('%10s %20s %-20s'%('', "Missing rooms", ''))
        print('\n'.join(missing_rooms_str))


def show_nights(dates_past, opts):      #pylint: disable=W0613
    """ colapse the raw calendar to show each night on one line
        date,      inlaw, master, middle,  bunk,  loft
                   who,   who,    who,     who,   who
    """
    dates_combo = [dates_past[0]]
    for date in dates_past[1:]:
        if dates_combo[-1]['nightShort'] not in date['nightShort']:        # new date
            dates_combo += [date]
        else:
            for room in ROOMS:
                sep = ',' if date[room] and dates_combo[-1][room] else ''
                dates_combo[-1][room] = dates_combo[-1][room]+sep+date[room]
    # dates_combo[] is {'night':'2016-12-15', 'summary':'Logan', 'description':'master',
    #       'master':'Logan', 'in-law':'Bob', 'middle':'Mark', ...}
    print('\n%10s '%('Nights')+' '.join(['%16s'%room for room in ROOMS]))
    for date in dates_combo:
        print('%10s '%(date['nightShort'])+' '.join(['%16s'%date[room] for room in ROOMS]))


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
        #       '+++', event['summary'], '====', event['description'], '*****'
        member_counts[gevent_to_member_name(event)]['total'] = \
            member_counts[gevent_to_member_name(event)]['total']+1
        for room in ROOMS:
            if room in event['description'].lower():
                member_counts[event[room]][room] = member_counts[event[room]][room]+1
    return member_counts


def show_room_counts(member_counts):
    """     Room priority is based on which member has used the room the least.
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
    member = event['summary'].split()[0].replace(',', '')
    return member


def main(opts):
    """ the program
    """
    if opts['--debug']:
        print(repr(opts))

    # ignore line-to-long
    #pylint: disable=C0301
    if opts['--offline']:
        dates_raw = [
            {'leave': '2018-12-02', 'summary': 'Bob', 'description': 'master', 'night': '2018-12-01'},
            {'leave': '2018-12-02', 'summary': 'James, Jean', 'description': 'in-law', 'night': '2018-12-01'},
            {'leave': '2018-12-02', 'summary': 'Peter', 'description': 'middle', 'night': '2018-12-01'},
            {'leave': '2018-12-06', 'summary': 'James, Jean', 'description': 'in-law', 'night': '2018-12-02'},
            {'leave': '2018-12-03', 'summary': 'Peter', 'description': 'middle', 'night': '2018-12-02'},
            {'leave': '2018-12-09', 'summary': 'Bob', 'description': 'master', 'night': '2018-12-08'},
            {'leave': '2018-12-14', 'summary': 'Jon', 'description': 'loft', 'night': '2018-12-10'},
            {'leave': '2018-12-24', 'summary': 'James, Jean', 'description': 'in-law', 'night': '2018-12-14'},
            {'leave': '2018-12-23', 'summary': 'Dina', 'description': 'master', 'night': '2018-12-20'},
            {'leave': '2018-12-30', 'summary': 'Jon, Sam, Z', 'description': 'bunk', 'night': '2018-12-20'},
            {'leave': '2018-12-26', 'summary': 'Bob +1', 'description': 'middle', 'night': '2018-12-22'},
            {'leave': '2018-12-28', 'summary': 'Erin +1', 'description': 'master', 'night': '2018-12-23'},
            {'leave': '2018-12-26', 'summary': 'Dina', 'description': 'in-law', 'night': '2018-12-23'},
            {'leave': '2018-12-28', 'summary': 'Peter', 'description': 'in-law', 'night': '2018-12-25'},
            {'leave': '2018-12-30', 'summary': 'Dina', 'description': 'middle', 'night': '2018-12-26'},
            {'leave': '2019-01-12', 'summary': 'James, Jean', 'description': 'middle', 'night': '2019-01-09'},
            {'leave': '2019-01-13', 'summary': 'Bob +1', 'description': 'master', 'night': '2019-01-12'},
            {'leave': '2019-01-13', 'summary': 'James, Jean +2', 'description': 'middle, bunk', 'night': '2019-01-12'},
            {'leave': '2019-01-17', 'summary': 'Jon', 'description': 'in-law', 'night': '2019-01-13'},
            {'leave': '2019-01-16', 'summary': 'Jean, James +1', 'description': 'middle, bunk', 'night': '2019-01-13'},
            {'leave': '2019-01-18', 'summary': 'Peter', 'description': 'master', 'night': '2019-01-15'},
            {'leave': '2019-01-21', 'summary': 'Jon +1 +Z', 'description': 'bunk', 'night': '2019-01-18'},
            {'leave': '2019-01-21', 'summary': 'Dina', 'description': 'in-law', 'night': '2019-01-18'},
            {'leave': '2019-01-22', 'summary': 'Glenn', 'description': 'master', 'night': '2019-01-18'},
            {'leave': '2019-01-20', 'summary': 'Erin', 'description': 'loft', 'night': '2019-01-18'},
            {'leave': '2019-01-20', 'summary': 'Bob +1', 'description': 'middle', 'night': '2019-01-19'},
            {'leave': '2019-01-25', 'summary': 'James', 'description': 'in-law', 'night': '2019-01-21'},
            {'leave': '2019-01-27', 'summary': 'Mark +1', 'description': 'middle, loft', 'night': '2019-01-25'},
            {'leave': '2019-01-27', 'summary': 'Glenn', 'description': 'in-law', 'night': '2019-01-25'},
            {'leave': '2019-02-01', 'summary': 'James', 'description': 'bunk', 'night': '2019-01-25'},
            {'leave': '2019-01-27', 'summary': 'Bob', 'description': 'master', 'night': '2019-01-26'},
            {'leave': '2019-02-01', 'summary': 'Jon', 'description': 'in-law', 'night': '2019-01-27'},
            {'leave': '2019-02-06', 'summary': 'Mark', 'description': 'master', 'night': '2019-02-04'},
            {'leave': '2019-02-08', 'summary': 'Jon', 'description': 'in-law', 'night': '2019-02-05'},
            {'leave': '2019-02-10', 'summary': 'Mark', 'description': '', 'night': '2019-02-08'},
            {'leave': '2019-02-10', 'summary': 'Bob', 'description': '', 'night': '2019-02-09'},
            ]
    else:
        credentials = get_credentials(opts)
        dates_raw = get_season(credentials, opts)
        # print ',\n'.join([repr(x) for x in dates_raw])
    #pylint: enable=C0301

    more_dates(dates_raw)        # add 'date' and 'nightShort' fields to the events
    dates_raw = fix_spelling(dates_raw, opts)

    if opts['--debug']:
        show_raw(dates_raw, True)

    put_members_in_rooms(dates_raw, opts)

    dates_past = select_dates(dates_raw, opts, None, 0)
    member_counts = count_members_in_rooms(dates_past, opts)
    show_missing_rooms(dates_past, opts)

    if opts['--whosup']:
        show_whos_up(dates_raw, opts)
    # dates_raw[] is now a list of  {'night':'2016-12-15', 'summary':'Peter',
    #           'description':'master', 'master':'Peter', 'in-law':'', 'midle':'', ...}
    # member_counts{} = {'Bob':{'in-law':1, 'master':0, 'middle':0,
    #           'bunk':1,  'loft':0}, 'Mark:{'master':1,...},...}

    if opts['--raw']:
        show_raw(dates_raw, False)

    if opts['--guests']:
        show_guest_fees(dates_past, opts)

    if opts['--member']:
        for one_member in opts['--member'].split(','):
            dates_past_member = [x for x in dates_past if one_member in x['summary'].split()]
            show_guest_fees(dates_past_member, opts)

    if opts['--nights']:
        show_nights(dates_past, opts)

    if opts['--counts']:
        show_room_counts(member_counts)



if __name__ == '__main__':
    OPTS = docopt.docopt(USE_STR, version='0.0.9')
    # print(opts)
    main(OPTS)
