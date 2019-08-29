# rooms
## What is this?
This python script grabs a google calendar of room assignments in the ski lease I run and displays some useful stats.
## What's a Ski Lease?
A group of us lease a cabin near Lake Tahoe for the ski season (December through April). Ski lease members can use the cabin as much as they like.
There are more members (and their guests) than there are rooms so when two or more members want to use the same room on the same night,
 we have a system for determining who gets to use it: Whoever has used the room the least, gets it.
## How do I run this script?
You can't run it with live calendar data because the calendar is private to the members of the ski lease. The script requires a json key file that I haven't put in the git repository. You can run the test data `python rooms.py -o -w -s -2` and should see this:

```
Shifted to  2019-01-10 09:12
Here's who I've heard from:
         James, Jean  middle: Wed 01/09, 01/10, 01/11,
              Bob +1  master: Sat 01/12,
      James, Jean +2 middle, bunk: Sat 01/12,
                 Jon  in-law: Sun 01/13, 01/14, 01/15, 01/16,
      Jean, James +1 middle, bunk: Sun 01/13, 01/14, 01/15,
               Peter  master: Tue 01/15, 01/16, 01/17,

Members who owe guest fees:
$ 175       Erin: 12/23, 12/24, 12/25, 12/26, 12/27
$ 175      total

Members who have paid their guest fees:  (Yay!)
$ 140        Bob: 12/22, 12/23, 12/24, 12/25
$ 140      total
```
Use -h to see all the switches. This script has been tested on Python 3.4.2 on a raspberry pi and 3.7.4 on Windoze and OSX. use 'pip install -r requirements.txt' to install the required libs.

## How do I join the ski lease?
Contact me. I'm ski boy bob on gmail
