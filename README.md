# rooms
## What is this?
This python script grabs a google calendar of room assignments in the ski lease I run and displays some useful stats.
## What's a Ski Lease?
A group of us lease a cabin near Lake Tahoe for the ski season (December through April). Ski lease members can use the cabin as much as they like. 
There are more members (and their guests) than there are rooms so when two or more members want to use the same room on the same night,
 we have a system for determining who gets to use it: Whoever has used the room the least, gets it.
## How do I run this script?
You can't run it with live calendar data because the calendar is private to the members of the ski lease. The script requires a json key file that I haven't put in the git repository. You can run the test data `python rooms.py -o -n -g` and should see this:

```
                                Guests Calendar     
2016-12-13 BobS  +1             master, middle      

    Nights           in-law           master           middle             bunk             loft
2016-12-03              Bob            Logan              Jon             Mark                 
2016-12-04              Jon            Logan                                                   
2016-12-05              Jon            Logan                                                   
2016-12-06            James            Logan                                                   
2016-12-07                             Logan                                                   
2016-12-08                             Logan                                                   
2016-12-09                             Logan                                                   
2016-12-11            James            Logan                                                   
2016-12-12            James            Logan                                                   
2016-12-13            James             BobS             BobS                                  
2016-12-14            James                                                                    
2016-12-15                             Logan                                                   

        Counts  in-law   master   middle     bunk     loft
   5     James       5                                    
   1      Mark                                  1         
  10     Logan               10                           
   1       Bob       1                                    
   1      BobS                1        1                  
   3       Jon       2                 1                  
```

## How do I join the ski lease?
Contact me.
