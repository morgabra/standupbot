standupbot
==========

standupbot will keep track of who is in standups and what time they are and will either run the IRC standup or provide you a google+ hangout link automatically.

### usage

1. Add users
2. Add standup times/types ('googleplus' or 'irc' are supported)

### example sessions
    <morgabra> standupbot: start googleplus
    <standupbot> testuser4: morgabra: testuser2: testuser3: testuser1: it's standup time!
    <standupbot> hangout link: https://hangoutsapi.talkgadget.google.com/hangouts?authuser=0&gid=771040692084
    ...
    <morgabra> standupbot: start irc
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
    <standupbot> standup DONE! (total time: 0.29)

#### commands
You can configure the json file directly or do with with the bot

###### help
    <morgabra> standupbot: help
    <standupbot> available commands (try "help <command>"): list, add, remove, start, next, reset, status,
    <morgabra> standupbot: help add
    <standupbot> usage: 'add (user, time) <argument>' - add user/time to standup


###### list - list users and times for your standup
    <morgabra> standupbot: list users
    <standupbot> standup users: morgabra, testuser2, testuser3, testuser1
    <morgabra> standupbot: list times
    <standupbot> standup times: F@11:45 (irc), M@11:45 (irc), R@11:45 (googleplus), W@11:45 (irc), T@11:45 (googleplus)


###### add - add users and times to your standup
    <morgabra> standupbot: add user testuser4
    <standupbot> added testuser4 to users
    <morgabra> standupbot: add time W@12:00 irc
    <standupbot> added W@12:00 (irc) to times

###### remove - remove users and times from your standup
    <morgabra> standupbot: list times
    <standupbot> standup times: F@12:00 (irc), R@11:45 (googleplus), M@11:45 (irc), T@11:45 (googleplus), F@11:45 (irc), W@11:45 (irc)
    <morgabra> standupbot: remove time F@12:00
    <standupbot> removed F@12:00 (F@12:00) from times

###### status - show status of currently running standup
    <morgabra> standupbot: status
    <standupbot> no active standup
    ...
    <morgabra> standupbot: status
    <standupbot> active standup user: morgabra total time: 0.05 minutes

###### start - manually start a standup
    <morgabra> standupbot: start googleplus
    <standupbot> testuser4: morgabra: testuser2: testuser3: testuser1: it's standup time!
    <standupbot> hangout link: https://hangoutsapi.talkgadget.google.com/hangouts?authuser=0&gid=771040692084
    ...
    <morgabra> standupbot: start irc
    <standupbot> testuser4: morgabra: testuser2: testuser3: testuser1: it's standup time!
    <standupbot> testuser2: you're up first (remember to tell me 'next' when you are done)

###### next - advance standup
    <standupbot> morgabra: you're up next (remember to tell me 'next' when you are done)
    <morgabra> standupbot: next
    <standupbot> testuser3: you're up next (remember to tell me 'next' when you are done)

###### reset - cancel channel standup
    <morgabra> standupbot: reset
    <standupbot> current standup is reset
    <morgabra> standupbot: status
    <standupbot> no active standup

###### join - force bot to join another channel
    <morgabra> standupbot: join ##testbot-877
    <standupbot> joining ##testbot-877

###### leave - force bot to leave current channel
    <morgabra> standupbot: leave
    standupbot left the channel ()

### todo

* have the bot follow nick changes
* track standup history (rollcall, keep logs, etc)
* clean up code and write tests
* make file io/datastore non-blocking and better
* make command parsing and standup runner hooks better