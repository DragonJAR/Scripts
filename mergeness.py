#!/usr/bin/env python

""" mergeness is a .nessus report file merge tool. """


import sys
import os
import tempfile


__author__ = "Dejan Levaja"
__license__ = "GPL"
__version__ = "2.0.0"
__email__ = "dejan.levaja@ras-it.rs"


header = []
tail = ['</Report>', '</NessusClientData_v2>']


def saveHeader(filepath):
    string = 'Report name'
    with open(filepath, 'r') as f:
        txt = f.readlines()
    for line in txt:
        if string not in line:
            header.append(line.rstrip())
        else:
            return


def saveData(tmpfile, filepath, filename, i):
    print "[%s.] Merging file: %s" % (i, filename)
    string = 'Report name'

    with open(tmpfile, "a") as datafile:
        with open(filepath, 'r') as f:
            txt = f.readlines()
        copy = False
        for line in txt:
            if string not in line:
                if copy:
                    if '</Report>' in line.rstrip():
                        pass
                    elif '</NessusClientData_v2>' in line.rstrip():
                        pass
                    else:
                        datafile.write(line)
            else:
                copy = True


def merge(report_name, reportfile, tmpfile):
    with open(reportfile, "a") as merged:
        with open(tmpfile) as raw:
            for line in header:
                merged.write(line + "\n")
            merged.write('<Report name="%s">' % report_name)
            for line in raw:
                merged.write(line)
            for line in tail:
                merged.write(line)


def file_check(reportfile):
    if os.path.exists(reportfile):
        answer = raw_input("\n[!] I am going to overwrite the old report file! Is that OK with you [Y|N]? ")
        if answer.upper() == "Y":
            os.remove(reportfile)
            print '\t[+] OK. Merging...\n'
        elif answer.upper() == "N":
            sys.exit("[+] OK than, goodbye.\n")
        else:
            sys.exit("[*] I don't understand that...Exiting.\n")


def main():
    cwd = raw_input("[!] Enter path to the folder containing .nessus files (ENTER for CWD): ").strip()
    if cwd == "":
        cwd = os.getcwd()
        print '\t[+] Using current working directory: "%s".' % cwd
    report_name = raw_input('\n[!] Output file name (ENTER for "mergeness.out"):').strip()
    if report_name == "":
        report_name = "mergeness.out"
    print '\t[+] Output file name set to "%s"\n' % report_name
    tempdir = tempfile.gettempdir()
    tmpfile = os.path.join(tempdir, report_name)
    if os.path.exists(tmpfile):
        os.remove(tmpfile)
    reportfile = os.path.join(cwd, report_name)
    file_check(reportfile)
    for i, filename in enumerate(os.listdir(cwd)):
        try:
            if filename.split(".")[-1] == "nessus":
                filepath = os.path.join(cwd, filename)
                if i == 1:
                    saveHeader(filepath)
                    saveData(tmpfile, filepath, filename, i)
                else:
                    saveData(tmpfile, filepath, filename, i)

        except Exception as e:
            print '[-] Error! Message was: %s' % e.message
    merge(report_name, reportfile, tmpfile)


def title():
    banner = """
                                                              _                                     _              _ 
    _ __   ___  ___ ___ _   _ ___   _ __ ___ _ __   ___  _ __| |_   _ __ ___   ___ _ __ __ _  ___  | |_ ___   ___ | |
   | '_ \ / _ \/ __/ __| | | / __| | '__/ _ \ '_ \ / _ \| '__| __| | '_ ` _ \ / _ \ '__/ _` |/ _ \ | __/ _ \ / _ \| |
  _| | | |  __/\__ \__ \ |_| \__ \ | | |  __/ |_) | (_) | |  | |_  | | | | | |  __/ | | (_| |  __/ | || (_) | (_) | |
 (_)_| |_|\___||___/___/\__,_|___/ |_|  \___| .__/ \___/|_|   \__| |_| |_| |_|\___|_|  \__, |\___|  \__\___/ \___/|_|
                                            |_|                                        |___/                         
"""
    print banner


if __name__ == "__main__":
    title()
    main()
    sys.exit()
