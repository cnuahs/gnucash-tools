#!/usr/bin/env python
'''
Read share price quotes in csv format and add them to the gnucash price database.
'''

# 2015-07-27 - Shaun L. Cloherty <s.cloherty@ieee.org>

import os, sys;
import csv;
import logging;
#import pdb;

from datetime import datetime;
from fractions import Fraction;

from argparse import ArgumentParser;
import argparse;

from gnucash import GncNumeric, GncPrice;
import gnucash;

def floatToGncNumeric(val = 0, denom = 1000000):
    # convert val (as float) to a rational form
    rval = Fraction.from_float(val).limit_denominator(denom);
    # and then to GncNumeric
    return GncNumeric(rval.numerator, rval.denominator)

# the following comes from Henning Jacobs, see
# https://github.com/hjacobs/gnucash-stock-portfolio. It allows you to
# create a new price in the database using the intuitive syntax:
#   p = GncPrice(book);
from gnucash.function_class import ClassFromFunctions

def create_price(self, book = None, instance = None):
    if instance:
        price_instance = instance;
    else:
        price_instance = gnucash.gnucash_core_c.gnc_price_create(book.get_instance());
    ClassFromFunctions.__init__(self, instance=price_instance);

GncPrice.__init__ = create_price;
#

def main(args):
    logging.basicConfig(stream = sys.stderr,
                        format='%(levelname)s:%(message)s',
                        level = args.loglevel or logging.INFO);

    logging.debug("args = %s", args);
    logging.debug("csvfile = %s", getattr(args,"csvfile"));

    url = "xml://" + args.gcfile

    logging.debug("url = %s", url);

    ns = getattr(args,'ns'); # namespace for symbol(s)

    quotes = {}; # empty dict

    with getattr(args,'csvfile') as fid:
#        import pdb; pdb.set_trace();
        logging.info("Reading quotes from %s...", fid.name);

        dialect = 'excel';

        # note: cannot seek() on stdin, so don't attempt to
        #       determine the dialect and just use the default
        #       'excel' dialect
        
        if fid is not sys.stdin:
            logging.info('Sniffing csv dialect...');
            dialect = csv.Sniffer().sniff(fid.read(2*1024));
#            dialect.skipinitialspace = True;
#            csv.register_dialect(ns,dialect)

            fid.seek(0); # reset file pointer?
            
        reader = csv.DictReader(fid,dialect=dialect);

        cnt = 0;
            
        for row in reader:
            logging.debug("%i:row = %s", cnt, row);
                
            symbol = row["Symbol"]; # symbol
            date = datetime.strptime(row["Date"],"%Y-%m-%d"); # date
            price = float(row["Close"]); # closing price

            if symbol not in quotes.keys():
                quotes[symbol] = []; # empty list
            quotes[symbol].append((date,price)); # (date,price) tuple
            cnt = cnt + 1;

        logging.info("Ok. Read %i quotes.", cnt);

    # Initialize Gnucash session
    try:
        session = gnucash.Session(url, False, False, False);
    except gnucash.GnuCashBackendException, msg:
        logging.error("Failed to begin session on %s, %s.", url, msg);
        return(1);
        
    book = session.book;
    pdb = book.get_price_db();
    tbl = book.get_table(); # the commodity table

    logging.debug("{0} <- {1}".format(ns,quotes.keys()));
    for symbol in quotes.keys():
        stock = tbl.lookup(ns, symbol);
        if stock is None:
            logging.error("Failed to find %s in %s.", symbol, ns);
            return(1);
        else:
            logging.debug('Found symbol %s in %s.', symbol, ns);
                
        cur = tbl.lookup('CURRENCY', args.currency);
        if cur is None:
            logging.error("Failed to find currency %s.", args.currency);
            return(1);
        else:
            logging.debug('Found currency %s.', args.currency);

        if args.purge:
            # purge existing quotes
            logging.info("Purging quotes for %s in %s...", symbol, ns);
            # get existing quotes from the database
            p = pdb.get_prices(stock,cur);
            for i in range(0,len(p)):
                pdb.remove_price(p[i]);

        # add new quotes
        logging.info("Adding quotes for %s in %s...", symbol, ns);

        q = quotes[symbol];

        cnt = 0;
        for (date,price) in q:
#            import pdb; pdb.set_trace();
            p = GncPrice(book); # new GncPrice object
            p.set_time(date);
            p.set_commodity(stock);
            p.set_currency(cur);
            p.set_value(floatToGncNumeric(price));
            p.set_typestr('last');
            p.set_source('user:price-editor'); # almost true!
            pdb.add_price(p);
            cnt = cnt + 1;
                
        logging.info("Ok. Added %i quotes for %s.",cnt,symbol);

    # clean up
    if not args.dryrun:
        session.save();
    session.end();
    session.destroy();
    

if __name__ == "__main__":
    prog = os.path.basename(sys.argv[0]);
    
    rev = 0.1; # increment this if modifying the script

    version = "%s v%s" % (prog, rev);

    p = ArgumentParser(usage = "%(prog)s [options] gcfile",
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
                   help = 'perform a dry run, saving no changes');

    p.add_argument('-p','--purge',
                   action = "store_true",
                   help = "purge existing quotes for imported symbols");

    # optional arguments
    p.add_argument("--namespace",
                   action = "store", type = str,
                   metavar = "NAMESPACE",
                   dest = "ns",
                   default = "ASX",
                   help = "specify the namespace");

    p.add_argument("--currency",
                   action = "store", type = str, dest = "currency",
                   default = "AUD",
                   help = "specify the currency");

    # required arguments
    p.add_argument("-i","--input",
                   action = 'store', type = argparse.FileType('r', 0),
                   default = sys.stdin,
                   metavar = "FILE",
                   dest = "csvfile",
                   help = "read quotes from FILE in csv format");

    p.add_argument("gcfile", action = "store", metavar = "gcfile",
                   help = argparse.SUPPRESS);

    args = p.parse_args();
    exit(main(args));
