/* 
module to initiate updating agent.
It will initiate update script in /usr/local/sealion-agent/update.sh and exit

*/

/*********************************************

Author: Shubhansh <shubhansh.varshney@webyog.com>

*********************************************/

var spawn = require('child_process').spawn;
var fs = require('fs');
var agentDetails = require('../etc/config/agent-config.json');

var updateAgent = function(version) {
    var out = fs.openSync('/tmp/sealion_update.log', 'a');
    var err = fs.openSync('/tmp/sealion_update.err', 'a');
    var options ={
          cwd:'/usr/local/sealion-agent'
        , uid: process.getuid()
        , detached: true
        , stdio:['ignore', out, err]
    };

    var child = spawn('/usr/local/sealion-agent/etc/update.sh', 
        ['-a', agentDetails.agentId, '-v', version, '-o', agentDetails.orgToken],
        options);
    child.unref();
}

module.exports = updateAgent;
