#!/usr/bin/env python

"""
mergeness is a .nessus report file merge tool.


Copyright (C) 2011, Dejan Levaja

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""




import sys
import os
import platform
header=[]
tail=['</Report>', '</NessusClientData_v2>']


def saveHeader(filepath, dirpath):
    string = 'Report name'
    txt=open(filepath, 'r')
    for line in txt.readlines():
        if string not in line:
            header.append(line.rstrip())
        else:
            return
            

def saveData(filepath, dirpath):
    print "\nMerging file: ", filepath, 
    string = 'Report name'
    datafile=open(dirpath+"data.txt", "a")
    txt=open(filepath, 'r')
    copy=False
    for line in txt.readlines():
        if string not in line:
            if copy:
                if '</Report>' in line.rstrip():
                    pass
                elif '</NessusClientData_v2>' in line.rstrip():
                    pass
                else:
                    datafile.write(line)               
        else:
            copy=True
    datafile.close()

        
def merge(dirpath, report_name, rep_out_name):
    merged=open(dirpath+report_name, "a")
    raw=open(dirpath+"data.txt", "r")
    for line in header:
        merged.write(line+"\n")
    merged.write('<Report name="'+rep_out_name+'">')
    for line in raw:
        merged.write(line)
    for line in tail:
        merged.write(line)
    merged.close()
    raw.close()
    
    
def tmpFileCheck(dirpath, report_name):
    tmpfile=dirpath+"data.txt"
    mergedfile=dirpath+report_name
    if os.path.exists(tmpfile):
        os.remove(tmpfile)
    if os.path.exists(mergedfile):
        answer=raw_input("\a\n[!] I am going to overwrite the old report file! Is that OK with you [Y|N]? ")
        if answer.upper()=="Y": 
            os.remove(mergedfile)
        elif answer.upper()=="N": 
            sys.exit("\nOK than, goodbye.")
        else:
            sys.exit("\nI don't understand that...Exiting.")
        
    
    
   

def main():
    dirpath=raw_input("Enter path to the folder containing the nessus reports (ENTER for CWD): ")
    rep_out_name=raw_input("Enter name for the merged report: ")
    if dirpath=="":
        dirpath=os.getcwd()
        print "\n[!] Using current working directory."
    system=platform.system()
    if system=='Windows':   
        if dirpath[-1] !="\\":
            dirpath=dirpath+"\\"
    elif system=='Linux':
            if dirpath[-1] !="/":
                dirpath=dirpath+"/"
    else:
        sys.exit("\n[!] Unknown operating system :)")
    
    report_name=raw_input("\nOutput file name (ENTER for \"mergeness.out\"):" )
    if report_name=="":
        report_name="mergeness.out"
    tmpFileCheck(dirpath, report_name)
    i=0
    for file in os.listdir(dirpath):
        try:
            if file.split(".")[-1] =="nessus":
                i=i+1
                filepath=dirpath+file
                if i == 1:
                    saveHeader(filepath, dirpath)
                    saveData(filepath, dirpath)
                else:
                    saveData(filepath, dirpath)
        except:
            pass
    merge(dirpath, report_name, rep_out_name)
    os.remove(dirpath+"data.txt")

def selfPraise():
    print "\n"
    print "***********************************"
    print "***   .nessus report merge tool ***"
    print "***\tDejan Levaja\t\t***"
    print "***\thttp://www.netsec.rs\t***"
    print "***\tdejan.levaja@netsec.rs\t***"
    print "***********************************"
    print "Update: Ability to change report name"
    print "iampuky - iampuky[at]gmail[dot]com"
    print "***********************************"
    print "\n\n"

if __name__ == "__main__":
    selfPraise()
    main()
    sys.exit()
