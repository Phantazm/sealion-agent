"""
Module to daemonize a process. It supports start, stop, restart and status check.
Implements Daemon.
"""

__copyright__ = '(c) Webyog, Inc'
__author__ = 'Vishal P.R'
__email__ = 'hello@sealion.com'

import sys
import os
import time
import atexit
import signal
import os.path
import exit_status
from constructs import unicode

class Daemon(object):
    """
    Class to daemonize a process.
    """
    
    def __init__(self, pidfile, stdin = '/dev/null', stdout = '/dev/null', stderr = '/dev/null'):
        """
        Constructor
        
        Args:
            pidfile: file to store the process id
            stdin: input file
            stdout: output file
            stderr: error file
        """
        
        self.daemon_name = self.__class__.__name__.lower()  #daemon name
        self.stdin = stdin  #input handle
        self.stdout = stdout  #output handle
        self.stderr = stderr  #error handle
        self.pidfile = pidfile  #pid file
    
    def daemonize(self):
        """
        Method to daemonize the process.
        This uses Unix double fork to daemonize.
        """
        
        self.initialize()  #callback to perform pre daemonize tasks
        
        try: 
            pid = os.fork()  #first fork
            
            if pid > 0:
                #parent can terminate now. which means any controlling terminal wont block
                sys.stdout.write('%s started successfully\n' % self.daemon_name)
                sys.exit(exit_status.AGENT_ERR_SUCCESS)
        except OSError as e: 
            sys.stderr.write('Failed to daemonize sealion: %d (%s)\n' % (e.errno, e.strerror))
            sys.exit(exit_status.AGENT_ERR_DAEMONIZE_1)
     
        os.chdir('/')  #change the directory to root, so that the daemon can run even when the device it invoked from does not exist
        os.setsid()  #session leader
        os.umask(0)  #umask
    
        try: 
            pid = os.fork()  #second fork  
        except OSError as e: 
            sys.stderr.write('Failed to daemonize sealion: %d (%s)\n' % (e.errno, e.strerror))
            sys.exit(exit_status.AGENT_ERR_DAEMONIZE_2) 
            
        #redirect stream handlers
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(self.stdin, 'r')
        so = open(self.stdout, 'a+')
        se = open(self.stderr, 'a+')
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
        
        if pid > 0:  #parent can exit now
            sys.exit(exit_status.AGENT_ERR_SUCCESS)
        
        atexit.register(self.cleanup)  #register cleanup on exit
        
        #save pid for stop/restart/status
        with open(self.pidfile, 'w+') as f:
            f.write('%d\n' % os.getpid())
    
    def cleanup(self):
        """
        Public method to perform cleanup. It removes the pid file.
        """
        
        try:
            os.remove(self.pidfile)
        except:
            pass

    def start(self):
        """
        Public method to start the daemon.
        After demonizing the process, it calls the run method.
        """
        
        if self.status(True):  #if the daemon already running
            sys.stdout.write('%s is already running\n' % self.daemon_name)
            sys.exit(exit_status.AGENT_ERR_ALREADY_RUNNING)            
        
        self.daemonize()  #daemonize the process
        self.run()  #call run method

    def stop(self):
        """
        Public method to stop daemon.
        """
        
        if self.status(True) == False:  #make sure it is running
            sys.stdout.write('%s is not running\n' % self.daemon_name)
            return
        
        pid = self.get_pid()  #get pid from the file

        try:
            while 1:  #send SIGTERM to pid until we get a exception
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.5)
        except OSError as err:
            err = unicode(err)
            
            if err.find('No such process') > 0:  #check whether system reported unknown process
                if os.path.exists(self.pidfile):
                    try:
                        os.remove(self.pidfile)  #remove pid file
                    except Exception as e:
                        sys.stderr.write(unicode(e) + '\n')
                        sys.exit(exit_status.AGENT_ERR_FAILED_PID_FILE)
                    
                sys.stdout.write('%s stopped successfully\n' % self.daemon_name)
            else:
                sys.stderr.write(err + '\n')
                sys.exit(exit_status.AGENT_ERR_FAILED_TERMINATE)

    def restart(self):
        """
        Public method to restart the daemon.
        It stops the process and starts it.
        """
        
        self.stop()
        self.start()
        
    def status(self, is_only_query = False):
        """
        Public method to get running state of daemon.
        
        Args:
            query: True if dont want to print the status.
            
        Returns:
            True if daemon is running else False
        """
        
        pid = self.get_pid()  #pid
    
        if pid and os.path.exists('/proc/%d' % pid):  #check /proc/pid to see if process is running
            is_only_query == False and sys.stdout.write('%s is running\n' % self.daemon_name)
        else:
            is_only_query == False and sys.stdout.write('%s is not running\n' % self.daemon_name)
            return False
            
        return True
    
    def get_pid(self):
        """
        Method to get the pid of daemon by reading the pid file
        
        Returns:
            pid of daemon.
        """
        
        f = None
        
        try:
            f = open(self.pidfile, 'r')
            pid = int(f.read().strip())
        except:
            pid = None
        finally:
            f and f.close()

        return pid
            
    def initialize(self):
        """
        Called before daemonizing the process. Derived class can implment this to perform additional tasks.
        """
        
        pass

    def run(self):
        """
        Called after daemonizing the process. Derived class can implment this to run the tasks in daemon process.
        """
        
        pass
        
