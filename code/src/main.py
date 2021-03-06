"""
In a development environment this script is used as the main script.
It sets up logging, Universal and api sessions.
When used as main script this starts the agent execution.
"""

__copyright__ = '(c) Webyog, Inc'
__author__ = 'Vishal P.R'
__email__ = 'hello@sealion.com'

import os
import sys
import logging
import logging.handlers
import gc

#get the exe path, which is the absolute path to the parent directory of the module's direcotry
exe_path = os.path.dirname(os.path.abspath(__file__))
exe_path = exe_path[:-1] if exe_path[len(exe_path) - 1] == '/' else exe_path
exe_path = exe_path[:exe_path.rfind('/') + 1]

#add module lookup paths to sys.path so that import can find them
#we are inserting at the begining of sys.path so that we can be sure that we are importing the right module
sys.path.insert(0, exe_path + 'lib/socketio_client') 
sys.path.insert(0, exe_path + 'lib/websocket_client')
sys.path.insert(0, exe_path + 'src')
sys.path.insert(0, exe_path + 'lib')

#to avoid the bug reported at http://bugs.python.org/issue13684 we use a stable httplib version available with CPython 2.7.3 and 3.2.3
#since httplib has been renamed to http, we have to add that also in the path so that import can find it
if sys.version_info[0] == 3:
    sys.path.insert(0, exe_path + 'lib/httplib')
    
sys.path.insert(0, exe_path + 'opt')  #path for plugins directory

import helper
import controller
import api
import exit_status
from universal import Universal
from constructs import *

_log = logging.getLogger(__name__)  #module level logging
gc.set_threshold(50, 5, 5)  #set gc threshold
logging_list = []  #modules to log for
logging_level = logging.INFO  #default logging level

#setup logging for StreamHandler
#in StreamHandler we display only messages till everything initializes. This is done not polute the terminal when running as service
logging.basicConfig(level = logging_level, format = '%(message)s') 

formatter = logging.Formatter('%(asctime)-15s %(levelname)-7s %(thread)d - %(module)-s[%(lineno)-d]: %(message)s')  #formatter instance for logging
logger = logging.getLogger()  #get the root logger

try:
    #create rotating file logger and add to root logger
    #this can raise exception if the file cannot be created
    lf = logging.handlers.RotatingFileHandler(helper.Utils.get_safe_path(exe_path + 'var/log/sealion.log'), maxBytes = 1024 * 1024 * 100, backupCount = 5)
    lf.setFormatter(formatter)
    logger.addHandler(lf)
except Exception as e:
    sys.stderr.write('Failed to open the log file; %s\n' % unicode(e))
    sys.exit(exit_status.AGENT_ERR_FAILED_OPEN_LOG)
    
try:
    #initialize Universal and create api sessions
    #this can raise exception if universal is failed to find/create config files
    univ = Universal()
    api.create_session()
    api.create_unauth_session()
except Exception as e:
    _log.error(unicode(e))
    sys.exit(exit_status.AGENT_ERR_FAILED_INITIALIZE)
    
class LoggingList(logging.Filter):
    """
    Class to filter module wise logging 
    """
    
    def __init__(self, *logs):
        """
        Constructor
        """
        
        self.logs = [logging.Filter(log) for log in logs]  #create a filter list

    def filter(self, record):
        """
        Method is called every time something is logged
        
        Args:
            record: record to be logged
            
        Returns:
            True if filter is successful else False
        """
        
        return any(log.filter(record) for log in self.logs)
    
try:
    logging_list = univ.config.sealion.logging['modules']  #read any logging list defined in the config
except:
    pass

try:    
    temp = univ.config.sealion.logging['level'].strip()  #read logging level from config
    
    #set the level based on the string
    if temp == 'error':
        logging_level = logging.ERROR
    elif temp == 'debug':
        logging_level = logging.DEBUG
    elif temp == 'none':
        logging_list = []
except:
    logging_list = ['all']  #no logging level, means default to INFO and enable logging for all the modules

#add filter to all the logging handlers
for handler in logging.root.handlers:    
    if len(logging_list) != 1 or logging_list[0] != 'all':
        handler.addFilter(LoggingList(*logging_list))
        
if hasattr(univ.config.agent, '_id') == False:  #if the agent is already registerd, thare will be _id attribute
    if api.session.register(retry_count = 2, retry_interval = 10) != api.Status.SUCCESS:
        sys.exit(exit_status.AGENT_ERR_FAILED_REGISTER)
        
logger.setLevel(logging_level)  #set the logging level

#set the formatter for all the logging handlers, including StreamHandler
for handler in logging.root.handlers:
    handler.setFormatter(formatter)
               
def run(is_update_only_mode = False):
    """
    Function that starts the agent execution.
    
    Args:
        is_update_only_mode: whether to run the agent in update only mode
    """
    
    univ.is_update_only_mode = is_update_only_mode
    _log.info('Agent starting up')
    _log.info('Using python binary at %s' % sys.executable)
    _log.info('Python version : %s' % univ.details['pythonVersion'])
    _log.info('Agent version  : %s' % univ.config.agent.agentVersion)   
    controller.run()  #call the run method controller module to start the controller
    _log.info('Agent shutting down with status code 0')
    _log.debug('Took %f seconds to shutdown' % (univ.get_stoppage_time()))
    _log.info('Ran for %s hours' %  univ.get_run_time_str())
    helper.notify_terminate()  #send terminate event so that modules listening on the event will get a chance to cleanup
    sys.exit(0)
    
if __name__ == "__main__":  #if this is the main script
    run()
