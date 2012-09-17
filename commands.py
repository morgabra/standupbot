from twisted.python import log

import time

from txscheduling.cron import CronSchedule
from txscheduling.task import ScheduledCall

SCHEDULES = {}


def schedule_standup(client, channel, cron_string=None):
    chan = client.config['channels'].get(channel)
    if not chan:
        log.msg('Channel %s not found in config, skipping standup check' % (channel))
        return False

    if not cron_string:
        cron_string = chan['time']

    try:
        cs = CronSchedule(cron_string)
    except Exception as e:
        log.msg("Exception parsing cron string '%s': %s" % (cron_string, e))

    sc = SCHEDULES.get(channel)
    if not sc:
        log.msg('Creating new scheduledcall for channel %s @ %s' % (channel, cron_string))
        sc = ScheduledCall(IRC.run, client, channel)

    if sc.running:
        sc.stop()

    SCHEDULES[channel] = sc

    try:
        sc.start(cs)
        client.config['channels'][channel]['time'] = cron_string
        client.config.flush()
        log.msg('schedule started for channel %s @ %s' % (channel, cron_string))
        return True
    except Exception as e:
        log.msg('Standup could not be scheduled for time %s in channel %s: %s' % (cron_string, channel, e))
    return False


class IRC(object):

    standup_type = 'irc'

    @classmethod
    def cancel(cls, client, channel):
        log.msg('resetting standup state in %s' % channel)
        client.config['channels'][channel]['active'] = False
        client.config['channels'][channel]['started_at'] = None
        client.config['channels'][channel]['current_user'] = None
        users = client.config['channels'][channel]['users']
        new_users = {}
        for user, active in users.items():
            new_users[user] = False
        client.config['channels'][channel]['users'] = new_users
        client.config.flush()

    @classmethod
    def run(cls, client, channel):
        log.msg('running standup in %s' % channel)
        cls.cancel(client, channel)
        users = client.config['channels'][channel]['users']
        notify = client.config['channels'][channel]['notify']
        user = list(users.keys())[0]
        client.config['channels'][channel]['started_at'] = time.time()
        client.config['channels'][channel]['current_user'] = user
        client.config['channels'][channel]['active'] = True
        client.config.flush()
        client.sendmsg(channel, '%s: it\'s standup time!' % (': '.join(users.keys() + notify.keys())))
        client.sendmsg(channel, '%s: you\'re up first (remember to tell me \'next\' when you are done)' % user)

    @classmethod
    def check(cls, client, channel):
        active = client.config['channels'][channel]['active']
        users = client.config['channels'][channel]['users']
        current_user = client.config['channels'][channel]['current_user']

        if active:
            if users[current_user]:
                for user, done in users.items():
                    if not done:
                        client.config['channels'][channel]['current_user'] = user
                        client.sendmsg(channel, '%s: you\'re up next (remember to tell me \'next\' when you are done)' % user)
                        return

        started_at = client.config['channels'][channel]['started_at']
        current_time = time.time()
        time_taken = ((int(current_time) - started_at) / 60.0)
        high_score = client.config['channels'][channel]['high_score']
        low_score = client.config['channels'][channel]['low_score']

        skipped = []
        for user, done in users.items():
            if done == 'skipped':
                skipped.append(user)

        client.sendmsg(channel, 'standup DONE! (total time: %.03f minutes high:%.03f low:%.03f)' % (time_taken, high_score, low_score))
        client.sendmsg(channel, 'skipped: %s' % ', '.join(skipped))
        if time_taken > high_score or not high_score:
            client.config['channels'][channel]['high_score'] = time_taken
            client.sendmsg(channel, 'OHNO! New high score! D: (old: %.03f minutes new:%.03f minutes)' % (high_score, time_taken))
        if time_taken < low_score or not low_score:
            client.config['channels'][channel]['low_score'] = time_taken
            client.sendmsg(channel, 'WOO! New low score! :D (old: %.03f minutes new:%.03f minutes)' % (low_score, time_taken))

        client.config.flush()
        IRC.cancel(client, channel)


class Join(object):

    command = 'join'

    @classmethod
    def help(cls):
        return 'join <chan>: have the bot join the given channel'

    @classmethod
    def do_command(cls, client, user, channel, args):
        if not args:
            return 'need channel name'

        args = args.strip()
        channel = client.config['channels'].get(args)
        if channel:
            return 'already joined %s' % (args)

        new_channel = {
            "active": False,
            "current_user": None,
            "started_at": None,
            "time": "",
            "users": {},
            "notify": {},
            "high_score": 0.00,
            "low_score": 0.00
        }
        client.config['channels'][args] = new_channel
        client.config.flush()
        client.join(str(args))
        return 'joining %s' % (args)


class Leave(object):

    command = 'leave'

    @classmethod
    def help(cls):
        return 'leave: make the bot leave'

    @classmethod
    def do_command(cls, client, user, channel, args):
        chan = client.config['channels'].get(channel)
        if chan:
            client.leave(channel)
            del client.config['channels'][channel]
            client.config.flush()


class Status(object):

    command = 'status'

    @classmethod
    def help(cls):
        return 'usage: status - shows current standup status'

    @classmethod
    def do_command(cls, client, user, channel, args):
        active = client.config['channels'][channel]['active']

        if active:
            current_user = client.config['channels'][channel]['current_user']
            started_at = client.config['channels'][channel]['started_at']
            current_time = time.time()
            time_taken = '%.03f' % ((int(current_time) - started_at) / 60)
            return 'active standup user: %s total time: %s minutes' % (current_user, time_taken)
        else:
            return 'no active standup'


class Scores(object):

    command = 'scores'

    @classmethod
    def help(cls):
        return 'usage: scores - shows current standup scores'

    @classmethod
    def do_command(cls, client, user, channel, args):
        high_score = client.config['channels'][channel]['high_score']
        low_score = client.config['channels'][channel]['low_score']

        high_score = "%.03f" % high_score if high_score else 'N/A'
        low_score = "%.03f" % low_score if low_score else 'N/A'

        return 'standup scores: high:%s low:%s' % (high_score, low_score)


class Start(object):

    command = 'start'

    @classmethod
    def help(cls):
        return 'usage: start - start an unscheduled standup'

    @classmethod
    def do_command(cls, client, user, channel, args):
        IRC.run(client, channel)


class Reset(object):

    command = 'reset'

    @classmethod
    def help(cls):
        return "usage: reset - reset standup state"

    @classmethod
    def do_command(cls, client, user, channel, args):
        IRC.cancel(client, channel)
        return "current standup is reset"


class Next(object):

    command = 'next'

    @classmethod
    def help(cls):
        return "usage: next - advance to the next person in the standup"

    @classmethod
    def do_command(cls, client, user, channel, args):
        active = client.config['channels'][channel]['active']
        if not active:
            return

        current_user = client.config['channels'][channel]['current_user']
        if args == 'force':
            client.config['channels'][channel]['users'][current_user] = 'skipped'
            client.config.flush()
            IRC.check(client, channel)
        else:
            if current_user == user:
                client.config['channels'][channel]['users'][user] = True
                client.config.flush()
                IRC.check(client, channel)


class Settime(object):
    command = 'settime'

    @classmethod
    def help(cls):
        return "usage: 'settime <cronstring>' - set the standup time"

    @classmethod
    def do_command(cls, client, user, channel, args):
        cron_string = args
        success = schedule_standup(client, channel, cron_string=cron_string)
        if success:
            return 'standup time: %s' % (cron_string)
        else:
            return 'failed setting standup time to %s' % (cron_string)


class Show(object):

    command = 'show'

    @classmethod
    def help(cls):
        return "usage: 'show (users, time, notify)' - show users/standup time/notified users currently configured"

    @classmethod
    def do_command(cls, client, user, channel, args):
        list_type = args.strip()

        val = client.config['channels'][channel].get(list_type)
        if val == None:
            return cls.help()

        if list_type == 'users' or list_type == 'notify':
            val = val.keys()
        else:
            val = [val]

        return 'standup %s: %s' % (list_type, ', '.join(val))

class Notify(object):

    command = 'notify'

    @classmethod
    def help(cls):
        return "usage: 'notify <nick>' - notify non-participant of standup"

    @classmethod
    def do_command(cls, client, user, channel, args):
        notify = args

        notified = client.config['channels'][channel].get('notify')

        if notify not in notified:
            notified[notify] = False
            client.config['channels'][channel]['notify'] = notified
            client.config.flush()
            return 'added %s to notify list' % (notify)
        else:
            return '%s already on notify list' % (notify)


class Unnotify(object):

    command = 'unnotify'

    @classmethod
    def help(cls):
        return "usage: 'unnotify <nick>' - remove user from notification list"

    @classmethod
    def do_command(cls, client, user, channel, args):
        notify = args

        notified = client.config['channels'][channel].get('notify')

        if notify in notified:
            del notified[notify]
            client.config['channels'][channel]['notify'] = notified
            client.config.flush()
            return 'removed %s from notify list' % (notify)
        else:
            return '%s not on notify list' % (notify)


class Add(object):

    command = 'add'

    @classmethod
    def help(cls):
        return "usage: 'add <nick>' - add user to standup"

    @classmethod
    def do_command(cls, client, user, channel, args):
        user = args

        users = client.config['channels'][channel].get('users')

        if user not in users:
            users[user] = False
            client.config['channels'][channel]['users'] = users
            client.config.flush()
            return 'added %s to standup' % (user)
        else:
            return '%s already part of this standup' % (user)


class Remove(object):

    command = 'remove'

    @classmethod
    def help(cls):
        return "usage: 'remove <nick>' - remove user from standup"

    @classmethod
    def do_command(cls, client, user, channel, args):
        user = args

        users = client.config['channels'][channel].get('users')

        if user in users:
            del users[user]
            client.config['channels'][channel]['users'] = users
            client.config.flush()
            return 'removed %s from standup' % (user)
        else:
            return '%s already removed from standup' % (user)


class Commander(object):
    COMMANDS = [Scores, Notify, Unnotify, Show, Settime, Add, Remove, Start, Next, Reset, Status, Join, Leave]

    def run_command(self, client, user, channel, command):
        command = command.split(' ', 1)
        args = ''
        if len(command) > 1:
            args = command[1]
            command = command[0]
        else:
            command = command[0]

        response = None
        for c in self.COMMANDS:
            if c.command == command:
                response = c.do_command(client, user, channel, args)

        if command == 'help':
            response = self.get_help(args)

        if response:
            client.sendmsg(channel, response)

    def get_help(self, command):
        response = None
        if command:
            for c in self.COMMANDS:
                if c.command == command:
                    response = c.help()

        if not response:
            response = 'available commands (try "help <command>"): %s' % ', '.join(c.command for c in self.COMMANDS)

        return response
