#! /bin/python
import re
import datetime
import argparse
import os
import sys
import logging

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=('''
*nix Package Manager log parser.
'''))
    parser.add_argument('input', type=str, help='Filename of the log to parse')
    parser.add_argument('--daysback', '-d', type=int, default=1,
                        help='How many days back to search.')
    parser.add_argument('--os', '-o', type=str,
                        choices=['rhel', 'suse', 'debian'],
                        help='force log file type to parse')
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()

    # Including "warning" ANSI codes on logging.
    logformat = "\033[93m%(asctime)s [%(levelname)s] %(message)s\033[0m"
    if args.verbose:
        logging.basicConfig(format=logformat, level=logging.DEBUG)
    else:
        logging.basicConfig(format=logformat)
    # logging.info("This should be verbose.")
    # logging.warning("This is a warning.")
    # logging.error("This is an error.")

    # <-- Initialize -->
    rhel = False
    debian = False
    suse = False

    # Input File Validation and OS test
    if os.path.isfile(args.input):
        logFile = args.input
        if args.os:
            if args.os == 'rhel':
                rhel = True
            if args.os == 'debian':
                debian = True
            if args.os == 'suse':
                suse = True
        else:
            # Try to guess OS via filename
            if 'dpkg.log' in logFile:
                debian = True
            elif 'yum.log' in logFile:
                rhel = True
            elif 'history' in logFile:
                suse = True
            else:
                sys.exit('Cannot auto-determine log format.')
    else:
        sys.exit('Input file not found.')

    now = datetime.datetime.now()
    before = now - datetime.timedelta(days=args.daysback)

    if rhel:
        logging.info('Detected RHEL.')
        # DateTime|action|package
        pattern = re.compile(r'^(.+ \d{1,2} [\d:]+) (.*): (.*)$')
    elif debian:
        logging.info('Detected debian.')
        # DateTime|action|package|version
        pattern = re.compile(
            r'^([\d\-]+ [\d:]+) (status [\w\-]+|startup [\w ]+|configure|' +
            r'trigproc) ([\d\w\-.:]+) ([\d\w\-:.\+]+)(?: <none>)?$'
        )
    elif suse:
        logging.info('Detected SuSE.')
        # DateTime|action|package|version|arch|repo|user@host|uuid
        pattern = re.compile(
            r'^([\d\-]+ [\d:]+)\|(\w+)\|([\w\-]+)\|([\w\d\-.]+)\|\w+\|' +
            r'[\w@\d\-]*\|[\w\-]+\|[a-f0-9]+\|$'
        )
    earliestTimestamp = ''
    matchedLogs = []
    with open(logFile) as f:
        for line in f:
            if line[0] == '#':  # Skip line if it's a comment
                continue
            try:
                if rhel:
                    timestamp, action, package = pattern.match(line).groups()
                elif debian:
                    timestamp, action, package, \
                        version = pattern.match(line).groups()
                elif suse:
                    timestamp, action, package, \
                        version = pattern.match(line).groups()
            except:
                logging.info('Regex failed on line:\n' + line)
                continue
            # We only care if this is an "install package" action
            if 'status ' in action:
                action = action[7:]
            if action.lower() == 'installed':
                # Time detection:
                if debian:
                    dt = datetime.datetime.strptime(
                        timestamp,
                        '%Y-%m-%d %H:%M:%S')
                elif rhel:
                    dt = datetime.datetime.strptime(
                        timestamp,
                        '%b %d %H:%M:%S').replace(
                            year=datetime.datetime.now().year
                        )
                elif suse:
                    dt = datetime.datetime.strptime(
                        timestamp,
                        '%Y-%m-%d %H:%M:%S')
                # dt = dateutil.parser.parse(timestamp)
                if earliestTimestamp is '':
                    earliestTimestamp = dt
                if (dt < now and dt > before):
                    matchedLogs.append((dt, action, package))

if matchedLogs == []:
    print('No updates found in the last {} days.'.format(args.daysback))
else:
    print(
        '{} updates found in the last {} days.'.format(
            len(matchedLogs), args.daysback))
    print ('Earliest timestamp: {}'.format(
        earliestTimestamp.strftime('%Y-%m-%d %H:%M:%S')))
    for entry in matchedLogs:
        print(entry[2])
