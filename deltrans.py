#!/usr/bin/env python
'''
Delete transactions from the gnucash register.
'''

# 2016-07-26 - Shaun L. Cloherty <s.cloherty@ieee.org>

import os, sys;
#import csv;
import logging;
#import pdb;

from datetime import datetime;

from argparse import ArgumentParser;
import argparse;

#from gnucash import GncNumeric, GncPrice;
import gnucash;

# GnuCash account types:
#
#  0 ACCT_TYPE_BANK       *
#  1 ACCT_TYPE_CASH       *
#  2 ACCT_TYPE_ASSET
#  3 ACCT_TYPE_CREDIT     *
#  4 ACCT_TYPE_LIABILITY  *
#  5 ACCT_TYPE_STOCK
#  6 ACCT_TYPE_MUTUAL
#  8 ACCT_TYPE_INCOME     *
#  9 ACCT_TYPE_EXPENSE    *
# 10 ACCT_TYPE_EQUITY     *
# 11 ACCT_TYPE_RECEIVABLE
# 12 ACCT_TYPE_PAYABLE
# 13 ACCT_TYPE_ROOT
# 14 ACCT_TYPE_TRADING
# 15 ACCT_TYPE_CHECKING

# account types for deletable splits...
acctTypes = {gnucash.ACCT_TYPE_BANK,
             gnucash.ACCT_TYPE_CASH,
             gnucash.ACCT_TYPE_CREDIT,
             gnucash.ACCT_TYPE_LIABILITY,
             gnucash.ACCT_TYPE_INCOME,
             gnucash.ACCT_TYPE_EXPENSE,
             gnucash.ACCT_TYPE_EQUITY};

def isDeletable(trans,start,end,types):
    # returns TRUE if the transaction is deletable... i.e., if the
    # transaction date is after 'begin' and before 'end', and *all*
    # splits are against account types listed in types
    
    d = datetime.fromtimestamp(trans.GetDate());                

    logging.info("%s %s",d.date(),trans.GetDescription());
    
    flag = ((d >= start) and (d <= end));
    for split in trans.GetSplitList():
        accnt = split.GetAccount();
        flag = flag & (accnt.GetType() in types);
        logging.info("\t%s(%i)\t%.2f",accnt.GetName(),
                     accnt.GetType(),split.GetValue().to_double());
        
    return flag;

                
def delSplits(accnt,start,end,types):
    # recursively delete splits on the supplied account...
    logging.info("---------------");
    logging.info("%s",accnt.GetName());
    logging.info("---------------");
    # get a list of all the splits on the given account, and for
    # each split, retrieve the corresponding transaction
    #
    # only delete a split if all splits for the transaction are
    # deletable...
    for split in accnt.GetSplitList():
        trans = split.parent;
        if isDeletable(trans,start,end,types):
            logging.info("\tDeletable");
            trans.Destroy(); # ?
        else:
            logging.info("\tNOT Deletable");
            
    for child in accnt.get_children():
        delSplits(child,start,end,types);

        
def main(args):
    logging.basicConfig(stream = sys.stderr,
                        format='%(levelname)s:%(message)s',
                        level = args.loglevel or logging.INFO);

    logging.debug("args = %s", args);

    url = "xml://" + args.gcfile

    logging.debug("url = %s", url);

    # parse start and end dates
    start = datetime.strptime(args.start,"%Y-%m-%d");
    end = datetime.strptime(args.end,'%Y-%m-%d');

    # assert: start < end
    if start > end:
        logging.error("START must precede END!");
        return(1);

    logging.info("Deleting transactions from %s to %s, inclusive...",
                 start.date(),end.date());
        
    # initialize the Gnucash session
    try:
        session = gnucash.Session(url, False, False, False);
    except gnucash.GnuCashBackendException, msg:
        logging.error("Failed to begin session on %s, %s.", url, msg);
        return(1);
        
    book = session.book;
    root = book.get_root_account(); # the root account

    delSplits(root,start,end,acctTypes); # recursively delete splits
    
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

    # optional arguments
    p.add_argument('-s','--start',
                   action = 'store', type = str,
                   default = datetime(1900,1,1).strftime('%Y-%m-%d'),
                   help = 'specify the start date (yyyy-mm-dd)');

    p.add_argument('-e','--end',
                   action = 'store', type = str,
                   default = datetime(1900,1,1).strftime('%Y-%m-%d'),
                   help = 'specify the end date (yyyy-mm-dd)');
    
    p.add_argument("gcfile", action = "store", metavar = "gcfile",
                   help = argparse.SUPPRESS);

    args = p.parse_args();
    exit(main(args));
