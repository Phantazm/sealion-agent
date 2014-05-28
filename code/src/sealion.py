__copyright__ = '(c) Webyog, Inc'
__author__ = 'Vishal P.R'
__email__ = 'hello@sealion.com'

import logging
import os
import sys
import time
import traceback
import signal
import pwd
import subprocess
import json
import re

exe_path = os.path.dirname(os.path.abspath(__file__))
exe_path = exe_path[:-1] if exe_path[len(exe_path) - 1] == '/' else exe_path
exe_path = exe_path[:exe_path.rfind('/') + 1]
sys.path.insert(0, exe_path + 'src') 
sys.path.insert(0, exe_path)

if sys.version_info[0] == 3:
    sys.path.insert(0, exe_path + 'lib/httplib')

import exit_status
from daemon import Daemon

_log = logging.getLogger(__name__)

class sealion(Daemon):
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        Daemon.__init__(self, pidfile, stdin, stdout, stderr)
        self.user_name = 'sealion'
        self.monit_interval = 30
        self.crash_loop_count = 5
        self.monit_pid = -1
    
    @property
    def crash_dump_path(self):
        return '%svar/crash/' % exe_path 
    
    def save_dump(self, stack_trace):
        from globals import Globals
        globals = Globals()
        timestamp = int(time.time() * 1000)
        path = self.crash_dump_path + ('sealion-%s-%d.dmp' % (globals.config.agent.agentVersion, timestamp))
        dir = os.path.dirname(path)
        f = None
        
        try:
            os.path.isdir(dir) or os.makedirs(dir)            
            report = {
                'timestamp': timestamp,
                'stack': stack_trace,
                'orgToken': globals.config.agent.orgToken,
                '_id': globals.config.agent._id,
                'os': {'pythonVersion': globals.details['pythonVersion']},
                'process': {
                    'uid': os.getuid(),
                    'gid': os.getgid(),
                    'uptime': int(globals.get_run_time() * 1000),
                    'agentVersion': globals.config.agent.agentVersion,
                    'isProxy': globals.details['isProxy']
                }
            }
            f = open(path, 'w')
            json.dump(report, f)
        except:
            return None
        finally:
            f and f.close()
        
        return path
    
    def read_dump(self, file_name):
        f, report = None, None
        keys = ['timestamp', 'stack', 'orgToken', '_id', 'os', 'process']
        
        try:
            f = open(file_name, 'r')
            report = json.load(f)
        except:
            pass
        finally:
            f and f.close()
            
        if report == None or all(key in report for key in keys) == False:
            report = None
        
        return report
    
    def send_crash_dumps(self):        
        from globals import Globals
        import api
        crash_dump_timeout = (self.crash_loop_count * self.monit_interval) + 10
        globals = Globals()
        path = self.crash_dump_path
        agent_version_regex = globals.config.agent.schema['agentVersion'].get('regex', '.*')
        _log.debug('CrashDumpSender waiting for stop event for %d seconds' % crash_dump_timeout)
        globals.stop_event.wait(crash_dump_timeout)
        
        try:
            for file in os.listdir(path):
                file_name = path + file

                if os.path.isfile(file_name) and re.match('^sealion-%s-[0-9]+\.dmp$' % agent_version_regex, file) != None:
                    report = None

                    while 1:
                        if globals.stop_event.is_set():
                            _log.debug('CrashDumpSender received stop event')
                            return

                        report = report if report != None else self.read_dump(file_name)

                        if report == None or api.is_not_connected(api.unauth_session.send_crash_report(report)) == False:
                            break

                        _log.debug('CrashDumpSender waiting for stop event for 10 seconds')
                        globals.stop_event.wait(10)
                    
                    try:
                        os.remove(file_name)
                        _log.info('Removed dump %s' % file_name)
                    except Exception as e:
                        _log.error('Failed to remove dump %s; %s' % (file_name, str(e)))

                if globals.stop_event.is_set():
                    _log.debug('CrashDumpSender received stop event')
                    return
        except:
            pass
    
    def set_procname(self, proc_name = None):
        proc_name = proc_name if proc_name else self.__class__.__name__
        
        try:
            from ctypes import cdll, byref, create_string_buffer
            libc = cdll.LoadLibrary('libc.so.6')
            buff = create_string_buffer(len(proc_name) + 1)
            buff.value = proc_name.encode('utf-8')
            libc.prctl(15, byref(buff), 0, 0, 0)
        except Exception as e:
            _log.error('Failed to set process name; %s' % str(e))
        
    def initialize(self):        
        try:
            user = pwd.getpwnam(self.user_name)

            if user.pw_uid != os.getuid():
                os.setgroups([])
                os.setgid(user.pw_gid)
                os.setuid(user.pw_uid)
                os.environ['HOME'] = '/'
        except KeyError as e:
            sys.stderr.write('Failed to find user %s; %s\n' % (self.user_name, str(e)))
            sys.exit(exit_status.AGENT_ERR_FAILED_FIND_USER)
        except Exception as e:
            sys.stderr.write('Failed to change the group or user to %s; %s\n' % (self.user_name, str(e)))
            sys.exit(exit_status.AGENT_ERR_FAILED_CHANGE_GROUP_OR_USER)
            
        try:
            dir = os.path.dirname(self.pidfile)
            
            if os.path.isdir(dir) != True:
                os.makedirs(dir)
            
            f = open(self.pidfile, 'w');
            f.close()
        except Exception as e:
            sys.stderr.write(str(e) + '\n')
            sys.exit(exit_status.AGENT_ERR_FAILED_PID_FILE)
        
        sys.excepthook = self.exception_hook
        import main        
        
    def get_crash_dump_details(self):
        from globals import Globals
        globals = Globals()
        t = int(time.time())
        path = self.crash_dump_path
        crash_loop_timeout = self.crash_loop_count * self.monit_interval
        file_count, loop_file_count = 0, 0
        loop_regex = '^sealion-%s-[0-9]+\.dmp$' % globals.config.agent.agentVersion.replace('.', '\.')
        agent_version_regex = globals.config.agent.schema['agentVersion'].get('regex', '.*')
        
        try:
            for f in os.listdir(path):
                if os.path.isfile(path + f) and re.match('^sealion-%s-[0-9]+\.dmp$' % agent_version_regex, f) != None:
                    file_count += 1
                    
                    if re.match(loop_regex, f) != None and t - os.path.getmtime(path + f) < crash_loop_timeout:
                        loop_file_count += 1
        except:
            pass
        
        return (loop_file_count >= 5, file_count)
        
    def exception_hook(self, type, value, tb):
        if type != SystemExit:
            import helper
            helper.Utils.restart_agent('%s crashed' % self.__class__.__name__, ''.join(traceback.format_exception(type, value, tb)))
    
    def run(self): 
        try:
            self.monit_pid = subprocess.Popen([exe_path + 'bin/monit.sh', str(os.getpid()), '%d' % self.monit_interval], preexec_fn = os.setpgrp).pid
        except Exception as e:
            _log.error('Failed to open monitoring script; %s' % str(e))
        
        self.set_procname('sealiond')
        is_update_only_mode = False
        crash_dump_details = self.get_crash_dump_details()
        import helper
        helper.terminatehook = self.termination_hook
        from constructs import ThreadEx
        
        if crash_dump_details[1] > 0:
            _log.info('Found %d dumps' % crash_dump_details[1])
            ThreadEx(target = self.send_crash_dumps, name = 'CrashDumpSender').start()
        
        if crash_dump_details[0] == True:
            _log.info('Crash loop detected; Starting agent in update-only mode')
            is_update_only_mode = True
        
        import main
        main.run(is_update_only_mode)
        
    def cleanup(self):        
        try:
            self.monit_pid != -1 and os.killpg(self.monit_pid, signal.SIGKILL)
        except:
            pass
        
        Daemon.cleanup(self)
        
    def termination_hook(self, message, stack_trace):
        self.cleanup()
        message and _log.error(message)
        
        if stack_trace:
            dump_file = self.save_dump(stack_trace)

            if dump_file:
                _log.info('Dump file saved at %s' % dump_file)
            else:
                _log.info('Failed to save dump file')
            
def sig_handler(signum, frame):    
    if signum == signal.SIGINT:
        sys.exit(exit_status.AGENT_ERR_SUCCESS)
    
signal.signal(signal.SIGINT, sig_handler)
daemon = sealion(exe_path + 'var/run/sealion.pid')
is_print_usage = False

if len(sys.argv) == 2:
    if sys.argv[1] == 'start':
        daemon.start()
    elif sys.argv[1] == 'stop':
        daemon.stop()
    elif sys.argv[1] == 'restart':
        daemon.restart()
    elif sys.argv[1] == 'status':
        daemon.status()
    else:
        sys.stderr.write('Invalid Usage: \'%s\'\n' % sys.argv[1])    
        is_print_usage = True
else:
    is_print_usage = True
    
if is_print_usage == True:
    sys.stdout.write('Usage: %s start|stop|restart|status\n' % daemon.__class__.__name__)
    
sys.exit(exit_status.AGENT_ERR_SUCCESS)
