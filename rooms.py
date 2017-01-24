#! /usr/bin/env python
"""
based on this quickstart:
from  https://developers.google.com/google-apps/calendar/quickstart/python
I had to use easy_tools to install instead of pip
"""


# from __future__ import print_function  # sorry, I don't really like the future

lcUuseStr = """
 --Show room usage in Lone Clone Ski Cabin--
 Usage:
  rooms  [--counts] [--debug] [--guests] [--member=<M>] [--nights] [--offline] [--raw] [--whosup] [--year=<Y>]
  rooms  -h | --help
  rooms  -v | --version

 Options:
  -h --help               Show this screen.
  -c --counts             show how many times each member has used each room
  -d --debug              show stuff
  -g --guests             show nights with guests
  -m --member <M>         show nights with guests for a single member
  -n --nights             show who slept where, each night
  -o --offline            don't get the live calendar. Use a test data set
  -r --raw                show the raw calendar events
  -v --version            show the version
  -w --whosup             show who's up in the next week
  -y --year <Y>           year season starts [default: 2016]
    """

import httplib2
import os
import sys

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
import docopt

import datetime

if False:
    import logging
    logger = logging.getLogger()
    # logger.setLevel(logging.INFO)
    logger.setLevel(logging.WARNING)
    logging.basicConfig()


# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'

rooms =  ('in-law', 'master', 'middle',  'bunk',  'loft')    # assignable rooms in the cabin

""" gPeak is a list of days-of-the-week or dates that guest fee is higher than not.
    The dates are specific to the Julian calendar of each season.
    The year index is the season start year.
"""
gPeak = {
    '2016': ['Fri','Sat']+['12/%2d'%x for x in range(18,32)]+['01/01','01/02','02/19',],
    '2017': ['Fri','Sat']+['12/%2d'%x for x in range(17,32)]+['01/01',        '02/19',],
    }


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
    credential_path = os.path.join(credential_dir,'calendar-python-quickstart.json')
    if opts['--debug']:
        print '** using credentials at '+credential_path
    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print 'Storing credentials to ' + credential_path
    return credentials


def get_events(cred, **kwargs):
    """  Wraps the service.events() call
    """
    http = cred.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)      # throws Warning and ImportError
    eventsResult = service.events().list(**kwargs).execute()
    ev = eventsResult.get('items',[])
    return ev


def get_season(credentials,opts):
    """  Grab the entire calendar for the season
    """
    day0 = datetime.datetime(int(opts['--year']),12,1).isoformat()+'Z'
    dayLast = datetime.datetime(1+int(opts['--year']),5,1).isoformat()+'Z'
    events = get_events(credentials,timeMin=day0,timeMax=dayLast, singleEvents=True, orderBy='startTime',calendarId="primary")
    datesRaw = []
    for event in events:
        e = {}
        e['night'] = event['start'].get('dateTime', event['start'].get('date'))[:10]  # {'night':'2016-12-15'}
        # summary is the member name, description has room assignment
        for k in ('summary','description','colorId'):
            try:
                e[k] = event[k]
            except KeyError:
                e[k] = ''
        datesRaw += [e]
    # datesRaw[] is a list of  {'night':'2016-12-15', 'summary':'Logan', 'description':'master'}
    return datesRaw


def more_dates(datesRaw):
    for e in datesRaw:             # add day of week
        e['date'] = datetime.datetime.strptime(e['night'],'%Y-%m-%d')
        e['nightShort'] = e['date'].strftime('%a %m/%d')   # turn "2016-12-23" into "Fri 12/23"


def fix_spelling(datesRaw, opts):
    """  Common data entry errors: fix the dict and flag it for me to fix the google calendar
    """
    for e in datesRaw:
        for field, wrong, right in [('description','inlaw','in-law'),('summary','Bob S','BobS ')]:
            if opts['--debug']:
                if wrong in e[field]:
                    print '** spellcheck:', e
            e[field] = e[field].replace(wrong,right)    #  in-law, not inlaw, e.g.
    return datesRaw


def select_dates(datesRaw, opts, day0=None, day1=None):
    """ return a subset of the events from today+day0 to today+day1
        None in day0 means begining of current ski season
        None in day1 means end of current ski season
    """
    dateSeasonStart = datetime.datetime(int(opts['--year']),12,1)  # season starts Dec 1
    dateSeasonEnd = datetime.datetime(1+int(opts['--year']),5,1)   # season ends May 1
    dateFirst = dateSeasonStart if day0 == None else datetime.datetime.utcnow() + datetime.timedelta(days=day0)
    dateLast =  dateSeasonEnd   if day1 == None else datetime.datetime.utcnow() + datetime.timedelta(days=day1)
    # print 'select',dateFirst.strftime('%a %m/%d'), dateLast.strftime('%a %m/%d')
    return [e for e in datesRaw if bool(dateFirst <= e['date'] <= dateLast) ]


def show_raw(datesRaw,bdict=False):
    """  Debugging aid
    """
    if bdict:
        print '** datesRaw'
        print '{'+ '},\n{'.join([', '.join(["'%s':'%s'"%(n,e[n]) for n in ('nightShort','summary','description')]) for e in datesRaw]) +'}'
    else:
        print ''
        print '%10s %10s %-20s'%('','','Raw Calendar')+' '.join(['%10s'%r for r in rooms])
        for e in datesRaw:
            print '%10s %-10s %-20s'%(e['nightShort'],e['summary'],e['description'])+' '.join(['%10s'%e[r] for r in rooms])


def put_members_in_rooms(datesRaw,opts):
    # add ['middle']='Logan' or blank for all rooms
    for e in datesRaw:
        for r in rooms:
            if r in e['description'].lower():
                e[r] = gevent_to_member_name(e)   # just the first name
            else:
                e[r] = ''


def show_guest_fees(datesRaw,opts):
    """ Calculate guest fees based on the cabin rules (Fri, Sat, and holiday  nights are "Peak" rates)
        note: Special rule for Jon and Dina's daughter Sam who doesn't pay guest fee but does take a room.
    """
    m = '' if not opts['--member'] else opts['--member']
    print '%10s %20s %-20s'%('%s-%2d'%(opts['--year'],int(opts['--year'])-1999),'Guests Calendar',m)
    gFeeTot, gTot = 0, 0
    for e in datesRaw:
        if '+' in e['summary'] and 'Z+1' not in e['summary']: # guests but not Z+1 (Sam). Enter "Z +1" to indicate not Sam (chargable)
            gFee = 40 if any([x in e['nightShort'] for x in gPeak[opts['--year']]]) else 35
            gFee *= int(e['summary'].split('+')[1])
            gFeeTot += gFee
            gTot += 1
            # if not any([c in e['summary'] for c in ('Erin','Jon','Bob ',)]):
            print '%10s %4d %-20s %-20s'%(e['nightShort'],gFee,e['summary'],e['description'])
    print 'Total %d guests and $%d in fees'%(gTot,gFeeTot)


def show_whos_up(datesRaw,opts):
    """ This output gets pasted into my periodic emails
        who day date, date, date
    """
    print "Here's who I've heard from:"
    datesRaw = select_dates(datesRaw, opts, -2, 7)
    membs = {}
    for e in datesRaw:
        m = e['summary']
        try:
            membs[m] += [(e['date'],e['nightShort']),]
        except KeyError:
            membs[m] = [(e['date'],e['nightShort']),]

    for m in sorted(membs.items(),key=lambda(k,v): v[0][0]):  # sort by the begining night of stay
        # print m
        print '%15s %s %s'%(m[0],m[1][0][1].split()[0],', '.join([x[1].split()[1] for x in m[1]]))


def show_missing_rooms(datesRaw,opts):
    """ Flag the data entry error condition: all members in the cabin on a given night
        must be in a room. Otherwise, the count will be wrong and the priority system breaks down.
    """
    datesRaw = select_dates(datesRaw, opts, None, 0)
    outS = ''
    for e in datesRaw:
        if not e['description']:        # catch members in cabin but not assigned to any room
            outS = outS + '** On %s where did %s sleep?'%(e['nightShort'],e['summary'])
    if outS:
        print '%10s %20s %-20s'%('',"Missing rooms",'')
        print outS


def show_nights(datesToNow,opts):
    """ colapse the raw calendar to show each night on one line
        date,      inlaw, master, middle,  bunk,  loft
                   who,   who,    who,     who,   who
    """
    datesComb = [datesToNow[0]]
    for e in datesToNow[1:]:
        if datesComb[-1]['nightShort'] not in e['nightShort']:        # new date
            datesComb += [e]
        else:
            for r in rooms:
                sep = ',' if e[r] and datesComb[-1][r] else ''
                datesComb[-1][r] = datesComb[-1][r]+sep+e[r]
    # datesComb[] is {'night':'2016-12-15', 'summary':'Logan', 'description':'master', 'master':'Logan', 'in-law':'Bob', 'midle':'Mark', ...}
    print '\n%10s '%('Nights')+' '.join(['%16s'%r for r in rooms])
    for e in datesComb:
        print '%10s '%(e['nightShort'])+' '.join(['%16s'%e[r] for r in rooms])


def count_members_in_rooms(datesRaw,opts):
    """ Construct the memberCount dict { 'Bob': {'inlaw': count, 'master' count, ...}...}
        for season up to today.
    """
    memberCnts = {}
    for e in datesRaw:
        memberCnts[ gevent_to_member_name(e) ] = {t:0 for t in rooms+('total',)}              # init the memberCnts with the first name {rooms}
    for e in datesRaw:                                                       # add ['middle']='Logan' or blank for all rooms
        memberCnts[gevent_to_member_name(e)]['total'] = memberCnts[gevent_to_member_name(e)]['total']+1
        for r in rooms:
            if r in e['description'].lower():
                memberCnts[ e[r] ][r] = memberCnts[ e[r] ][r]+1
    return memberCnts


def show_room_counts(memberCnts):
    """     Room priority is based on which member has used the room the least.
            date, who, where    inlaw, master, middle,  bunk,  loft
            total who,          count,  count,  count, count, count
    """
    print '\n%4s%10s'%('','Counts')+' '.join(['%8s'%r for r in rooms])   # show how many times each member has slept in each room
    for c in memberCnts:
        print '%4d%10s'%(memberCnts[c]['total'],c)+' '.join(['%8s'%('%d'%memberCnts[c][r] if memberCnts[c][r] else '' ) for r in rooms])


def gevent_to_member_name(e):
    """ Each calendar event has only one member name as the first word in the summary.
        extract the member name ignoring whatever else is in the summary.
        Should be run *after* fix_spelling()
    """
    mem = e['summary'].split()[0].replace(',','')
    return mem


def main(opts):
    if opts['--offline']:
        datesRaw = [
            {'night':'2016-12-03', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-03', 'summary':'Bob', 'description':'inlaw'},     # test inlaw->in-law sub
            {'night':'2016-12-03', 'summary':'Mark', 'description':'bunk'},
            {'night':'2016-12-03', 'summary':'Jon', 'description':'middle'},
            {'night':'2016-12-04', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-04', 'summary':'Jon', 'description':'in-law'},
            {'night':'2016-12-05', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-05', 'summary':'Jon', 'description':'in-law'},
            {'night':'2016-12-06', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-06', 'summary':'James', 'description':'in-law'},
            {'night':'2016-12-07', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-08', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-09', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-11', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-11', 'summary':'James', 'description':'in-law'},
            {'night':'2016-12-12', 'summary':'Logan', 'description':'master'},
            {'night':'2016-12-12', 'summary':'James', 'description':'in-law'},
            {'night':'2016-12-13', 'summary':'Bob S +1', 'description':'master, middle'}, # test Bob S to BobS sub
            {'night':'2016-12-13', 'summary':'James', 'description':'in-law'},
            {'night':'2016-12-14', 'summary':'James', 'description':'in-law'},
            {'night':'2016-12-15', 'summary':'Logan', 'description':'master'}
            ]
    else:
        credentials = get_credentials(opts)
        datesRaw = get_season(credentials,opts)

    more_dates(datesRaw)        # add 'date' and 'nightShort' fields to the events
    datesRaw = fix_spelling(datesRaw, opts)

    if opts['--debug']:
        show_raw(datesRaw, True)

    put_members_in_rooms(datesRaw,opts)

    datesToNow = select_dates(datesRaw, opts, None, 0)
    memberCnts = count_members_in_rooms(datesToNow,opts)
    show_missing_rooms(datesToNow,opts)

    if opts['--whosup']:
        show_whos_up(datesRaw,opts)
    # datesRaw[] is now a list of  {'night':'2016-12-15', 'summary':'Logan', 'description':'master', 'master':'Logan', 'in-law':'', 'midle':'', ...}
    # memberCnts{} = {'Bob':{'in-law':1, 'master':0, 'middle':0,  'bunk':1,  'loft':0}, 'Mark:{'master':1,...},...}

    if opts['--raw']:
        show_raw(datesRaw, False)

    if opts['--guests']:
        show_guest_fees(datesToNow,opts)

    if opts['--member']:
        datesToNowSingle = [x for x in datesToNow if opts['--member'] in x['summary'].split()]
        show_guest_fees(datesToNowSingle,opts)

    if opts['--nights']:
        show_nights(datesToNow,opts)

    if opts['--counts']:
        show_room_counts(memberCnts)



if __name__ == '__main__':
    opts = docopt.docopt(lcUuseStr,version='0.0.9')
    # print(opts)
    main(opts)
