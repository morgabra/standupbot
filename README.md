standupbot
==========

standupbot will keep track of who is in standups and what time they are and will run the IRC standup.

### usage

1. Add users ('standupbot: add user morgabra')
2. Add standup time ('standupbot: settime 30 18 * * 1,2,3,4,5' is M-F 18:30 UTC)
3. (Optional) Add notified users ('standupbot notify manager_nick')
4. Wait

### example sessions
    <standupbot> testuser4: morgabra: testuser2: testuser3: testuser1: it's standup time!
    <standupbot> testuser2: you're up first (remember to tell me 'next' when you are done)
    <morgabra> standupbot: next force
    <standupbot> testuser4: you're up next (remember to tell me 'next' when you are done)
    <morgabra> standupbot: next force
    <standupbot> morgabra: you're up next (remember to tell me 'next' when you are done)
    <morgabra> standupbot: next
    <standupbot> testuser3: you're up next (remember to tell me 'next' when you are done)
    <morgabra> standupbot: next force
    <standupbot> testuser1: you're up next (remember to tell me 'next' when you are done)
    <morgabra> standupbot: next force
    <standupbot> standup DONE! (total time: 0.438 minutes high:0.000 low:0.000)

#### commands
You can configure the json file directly or do with with the bot

###### help
    try 'standupbot: help'

### todo

* have the bot follow nick changes
* track standup history (rollcall, keep logs, etc)
* clean up code and write tests
* make file io/datastore non-blocking and better
* make command parsing and standup runner hooks better