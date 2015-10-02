
app.controller("ChatController", ["$scope", "$sce", function($scope, $sce){
    var wsChat = new WebSocket(urls.chat);
    var self = this;

    wsChat.onopen= function () {
        self.send();
    };

    wsChat.onmessage = function (evt) {
        var json = JSON.parse(evt.data);
        self.messages = json["messages"];
        $scope.$apply();
    };

    self.send = function(json){
        if (json === undefined)
            json = {};
        json["session_id"] = $.cookie("sessionid");
        wsChat.send(JSON.stringify(json));
    };

    self.chat = function(){
        if (!self.msg)
            return;
        self.send({"msg": self.msg});
        self.msg = "";
    };

    self.handleKeydown = function(evt){
        if (evt.which === 13)
            self.chat();
    };

    // emoji
    var size = 10;  // colum size
    var r = _.range(128513, 128549, 1);
    self.emojis = _.range(0, r.length, size).map(function(i){
        return r.slice(i, i + size).map(function(j){
            return $sce.trustAsHtml("&#" + j + ";");
        });
    });

    self.select_emoji = function(emoji){
        $("#emoji").modal('hide');
        self.send({"msg": emoji.toString()});
    };

}]);
