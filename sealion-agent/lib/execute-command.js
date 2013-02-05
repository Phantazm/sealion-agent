var Result = require('./result.js');
var exec = require ('child_process').exec;
var SendData = require('./send-data.js');

var Sealion = { };

Sealion.ExecuteCommand = function(serviceDetails, sqliteObj) {
    this.result = new Result();
    this.result.serviceDetails = serviceDetails;
    this.sqliteObj = sqliteObj;
};

Sealion.ExecuteCommand.prototype.handleCommandOutput = function () {
    var tempThis = this;
    var sendData = new SendData(this.sqliteObj);
    
    sendData.dataSend(this.result.output);
};

Sealion.ExecuteCommand.prototype.processCommandResult = function (error, stdout, stderror) {
    
    var tempThis = this;

    if(error) {
        this.result.code = error.code;
        this.result.output = stderr;
    } else {
        this.result.output = stdout !== '' ? stdout : stderr;
    }

    process.nextTick( function () {
        tempThis.handleCommandOutput();
    });
};

Sealion.ExecuteCommand.prototype.executeCommand = function(options) {

    var tempThis = this;
    
    this.result.options = options;
    this.result.timeStamp = new Date().getTime();
    
    var child = exec(this.result.serviceDetails.command, { }, function(error, stdout, stderr){
        tempThis.processCommandResult(error, stdout, stderr);
    });
};

module.exports = Sealion.ExecuteCommand;