#!/usr/bin/env python
'''
Fetch historical share price quotes from Yahoo! and output in csv format.
'''

# 2015-07-27 - Shaun L. Cloherty <s.cloherty@ieee.org>

import os, sys;
import csv;
import logging;
#import pdb;

from datetime import datetime;
from cStringIO import StringIO;

from argparse import ArgumentParser;
import argparse;

import requests;
from bs4 import BeautifulSoup;

def getQuote(symbol,start,end):
    # the Yahoo! finance url takes the form:
    #
    #   http://ichart.yahoo.com.au/table.csv?s=xxx.xx&c=%Y&a=%m&b=%d&f=%Y&d=%m&e=%d&g=d&ignore=.csv
    #
    # note: months are specified as integers between 0 and 11
    url = 'http://ichart.yahoo.com/table.csv';

    payload = {'s': symbol,
               'c': start.year, 'b': start.day, 'a': start.month-1,
               'f': end.year, 'e': end.day, 'd': end.month-1,
               'g': 'd',
               'ignore': '.csv'};
    
#    logging.disable(logging.INFO); # temporarily disable logging from the requests module
    r = requests.get(url, params = payload);
#    logging.disable(logging.NOTSET); # restore logging

    if r.status_code is not requests.codes.ok:
        logging.warning("Failed to get quotes for %s. Request returned %i.", symbol, r.status_code);
        return(1);
        
    soup = BeautifulSoup(r.text);

    f = StringIO(soup.p.get_text()); # read the string like a file
    reader = csv.DictReader(f);

    quotes = []; # empty list
    for row in reader:
        quotes.append(row);
        logging.debug("%i: %s", len(quotes), row);
        
    logging.debug('Got %i quotes for %s.', len(quotes), symbol);
    return(quotes);


def main(args):
    logging.basicConfig(stream = sys.stderr,
                        format='%(levelname)s:%(message)s',
                        level = args.loglevel or logging.INFO);
    
    logging.debug("args = %s", args);
    logging.debug("symbol = %s", getattr(args,"symbol"));

    # parse start and end dates
    start = datetime.strptime(args.start,"%Y-%m-%d");
    end = datetime.strptime(args.end,'%Y-%m-%d');

    # assert: start < end
    if start > end:
        logging.error("START must precede END!");
        return(1);

    if args.dryrun:
        return(0);

    # configure csv output
    fnames = ['Symbol','Date','Open','High','Low','Close','Volume'];

    # optionally force column headings/field names to lowercase
    if args.lowercase:
        fnames = [f.lower() for f in fnames];
    
    writer = csv.DictWriter(args.csvfile,fnames,extrasaction = 'ignore');

    # optionally suppress output of the header row
    if args.noheader is False:
        writer.writeheader();

    for symbol in args.symbol:
        # fetch quote(s)...
        quotes = getQuote(symbol,start,end);

        # Yahoo! returns quotes in reverse chronological order, here we
        # "reverse" the list unless args.reverse is True
        step = -1 if args.reverse is False else 1;

        for q in quotes[::step]:
            q["Symbol"] = symbol;

            if args.lowercase:
                q = dict([(k.lower(),v) for (k,v) in q.iteritems()]);
            writer.writerow(q);
    
    return(0);
    

if __name__ == "__main__":
    prog = os.path.basename(sys.argv[0]);
    
    rev = 0.1; # increment this if modifying the script

    version = "%s v%s" % (prog, rev);

    p = ArgumentParser(usage = "%(prog)s [options] SYM",
                       description = __doc__,
                       conflict_handler = "resolve");

    # add arguments here
    p.add_argument("--version", action = "version", version = version);

    # control debugging output/verbosity
    group = p.add_mutually_exclusive_group();
    group.add_argument('-v','--verbose',
                       action = 'store_const', const = logging.DEBUG,
                       dest = 'loglevel',
                       help = 'increase verbosity');
    group.add_argument('-q','--quiet',
                       action = 'store_const', const = logging.WARN,
                       dest = 'loglevel',
                       help = 'suppress non-error messages');

    p.add_argument('-n','--dry-run',
                   action = 'store_true',
                   dest = "dryrun",
                   help = 'perform a dry run, no quotes retrieved');

    # optional arguments
    p.add_argument('-s','--start',
                   action = 'store', type = str,
                   default = datetime.today().strftime('%Y-%m-%d'),
                   help = 'specify the start date (yyyy-mm-dd)');

    p.add_argument('-e','--end',
                   action = 'store', type = str,
                   default = datetime.today().strftime('%Y-%m-%d'),
                   help = 'specify the end date (yyyy-mm-dd)');

    p.add_argument('-r','--reverse',
                   action = 'store_true',
                   dest = "reverse",
                   help = 'output quotes in reverse order');

    p.add_argument('-l','--lowercase',
                   action = 'store_true',
                   dest = "lowercase",
                   help = 'output header in lowercase');

    p.add_argument('--no-header',
                   action = 'store_true',
                   dest = "noheader",
                   help = 'suppress output of the header line');

    p.add_argument("-o","--output",
                   action = "store", type = argparse.FileType('w', 0),
                   default = sys.stdout,
                   metavar = "FILE",
                   dest = "csvfile",
                   help = "write quotes to FILE in csv format");

    p.add_argument("symbol", action = "store", nargs = "+",
                   help = argparse.SUPPRESS);

    args = p.parse_args();
    exit(main(args));
