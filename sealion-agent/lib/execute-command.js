/*
Module is class representation of oject used to execute commands
*/

/*********************************************

(c) Webyog, Inc.
 Author: Shubhansh Varshney <shubhansh.varshney@webyog.com>

*********************************************/
var Result = require('./result.js');
var exec = require ('child_process').exec;
var SendData = require('./send-data.js');
var global = require('./global.js');


/** @constructor to execute command class*/
var ExecuteCommand = function(activityDetails, sqliteObj) {
    this.result = new Result();
    this.result.activityDetails = activityDetails;
    this.sqliteObj = sqliteObj;
};

// handles command execution output and initiates sending process
ExecuteCommand.prototype.handleCommandOutput = function () {
    var sendData = new SendData(this.sqliteObj);
    sendData.dataSend(this.result);
};

// function to process command execution output
ExecuteCommand.prototype.processCommandResult = function (error, stdout, stderr) {
    
    var tempThis = this;

    if(error) {
        var errorCodes = require('./error-code.js');
        this.result.code = error.code ? (typeof error.code === 'string' ?  (errorCodes[error.code] ? errorCodes[error.code] : -1) : error.code) : -1;
        this.result.output = stderr && stderr !== '' ? stderr : (stdout && stdout !== ''? stdout : JSON.stringify(error));
    } else {
        this.result.output = stdout && stdout !== '' ? stdout : (stderr && stderr !== '' ? stderr : 'No output to show.');
    }

    process.nextTick( function () {
        tempThis.handleCommandOutput();
    });
};

// function executes command
ExecuteCommand.prototype.executeCommand = function(options) {

    var tempThis = this;
    
    this.result.options = options;
    this.result.timeStamp = Date.now();

    try {
        var child = exec(this.result.activityDetails.command, { }, function(error, stdout, stderr){
            tempThis.processCommandResult(error, stdout, stderr);
        });
    } catch (err) {
        tempThis.processCommandResult(err, null, null);
    }
};

module.exports = ExecuteCommand;