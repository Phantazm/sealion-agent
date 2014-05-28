__copyright__ = '(c) Webyog, Inc'
__author__ = 'Vishal P.R'
__email__ = 'hello@sealion.com'

import logging
import time
import gc
import globals
import api
import connection
from socketio_client import SocketIO, BaseNamespace
from constructs import *

_log = logging.getLogger(__name__)
session = None

class SocketIOHandShakeError(Exception):
    pass

class SocketIONamespace(BaseNamespace):
    def initialize(self):
        self.globals = globals.Globals()
    
    def on_connect(self):        
        _log.info('SocketIO connected')
        self.rtc.update_heartbeat()
        
        if self.rtc.is_stop == True or self.globals.stop_event.is_set():
            self.rtc.stop()
            return
        
        api.session.ping()
        self.rtc.is_disconnected and api.session.get_config()
        self.rtc.is_disconnected = False
        
    def on_disconnect(self):
        _log.info('SocketIO disconnected')
        self.rtc.update_heartbeat()
        self.rtc.is_disconnected = True
        
    def on_heartbeat(self):
        _log.debug('SocketIO heartbeat')
        self.rtc.update_heartbeat()

    def on_activity_updated(self, *args):
        _log.info('SocketIO received Activity Updated event')
        self.rtc.update_heartbeat()
        api.session.get_config()

    def on_activitylist_in_category_updated(self, *args):
        _log.info('SocketIO received Activity list Updated event')
        self.rtc.update_heartbeat()
        api.session.get_config()

    def on_agent_removed(self, *args):
        _log.info('SocketIO received Agent Removed event')
        self.rtc.update_heartbeat()
        
        try:
            if args[0].get('servers'):
                (self.globals.config.agent._id in args[0]['servers']) and api.session.stop(api.Status.NOT_FOUND)
            else:
                api.session.stop(api.Status.NOT_FOUND)
        except:
            pass    

    def on_org_token_resetted(self, *args):
        _log.info('SocketIO received Organization Token Reset event')
        api.session.stop()

    def on_server_category_changed(self, *args):
        _log.info('SocketIO received Category Changed event')
        self.rtc.update_heartbeat()
        
        try:
            if args[0].get('servers'):
                (self.globals.config.agent._id in args[0]['servers']) and api.session.get_config()
            else:
                api.session.get_config()
        except:
            pass

    def on_activity_deleted(self, *args):
        _log.info('SocketIO received Activity Deleted event')
        self.rtc.update_heartbeat()
        
        try:
            (args[0]['activity'] in self.globals.config.agent.activities) and api.session.get_config()
        except:
            pass
        
    def on_upgrade_agent(self, *args):
        _log.info('SocketIO received Upgrade Agent event')
        self.rtc.update_heartbeat()
        
        try:
            args[0]['agentVersion'] != self.globals.config.agent.agentVersion and self.globals.event_dispatcher.trigger('update_agent')
        except:
            pass
        
    def on_logout(self, *args):
        _log.info('SocketIO received Logout event')
        self.rtc.update_heartbeat()
        api.session.stop(api.Status.SESSION_CONFLICT)
        
class RTC(ThreadEx):    
    def __init__(self):
        ThreadEx.__init__(self)
        self.sio = None
        self.globals = globals.Globals()
        self.is_stop = False
        self.daemon = True
        self.is_disconnected = False
        self.update_heartbeat()
        
    def on_response(self, response, *args, **kwargs):
        if response.text == 'handshake error':
            raise SocketIOHandShakeError('%d; %s' % (response.status_code, response.text))
               
    def connect(self):
        SocketIONamespace.rtc = self
        kwargs = {
            'Namespace': SocketIONamespace,
            'cookies': api.session.cookies,
            'hooks': {'response': self.on_response},
            'stream': True
        }
        
        if self.sio != None:
            self.sio = None
            _log.debug('GC collected %d unreachables' % gc.collect())
        
        if self.globals.details['isProxy'] == True:
            _log.info('Proxy detected; Forcing xhr-polling for SocketIO')
            kwargs['transports'] = ['xhr-polling']
        
        _log.debug('Waiting for SocketIO connection')
        
        try:
            self.sio = SocketIO(self.globals.get_url(), **kwargs)
        except SocketIOHandShakeError as e:
            _log.error('Failed to connect SocketIO; %s' % unicode(e))
            return None
        except Exception as e:
            _log.error(unicode(e))
        
        return self
    
    def stop(self):
        self.is_stop = True
        
        if self.sio != None:
            _log.debug('Disconnecting SocketIO')
            
            try:
                self.sio.disconnect()
            except:
                pass
            
    def update_heartbeat(self):
        self.last_heartbeat = int(time.time())
        
    def is_heartbeating(self):       
        t = int(time.time())        
        is_beating = True if t - self.last_heartbeat < (60 * 60) else False
        return is_beating

    def exe(self):        
        while 1:
            try:
                self.sio.wait()
            except SocketIOHandShakeError as e:
                _log.error('Failed to connect SocketIO; %s' % unicode(e))
                connection.Connection().reconnect()
                break
            except Exception as e:
                _log.error(unicode(e))
            
            if self.is_stop == True or self.globals.stop_event.is_set():
                _log.debug('%s received stop event' % self.name)
                break
                
            if self.connect() == None:
                connection.Connection().reconnect()
                break

def create_session():
    global session
    session = RTC()
    return session