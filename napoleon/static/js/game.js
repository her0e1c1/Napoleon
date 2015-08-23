var app = angular.module("GameApp", []);

app.config(function($interpolateProvider) {
    $interpolateProvider.startSymbol('[[');
    $interpolateProvider.endSymbol(']]');
});

app.controller("GameController", ["$scope", function($scope){
    var wsGame;
    var self = this;
    var sid = $.cookie("sessionid");

    self.sid = sid;
    self.unused = [];

    this.update = function(){
        $.get("/games/json/state/" + self.game_id, {}, function(data){
            $.extend(self, data);

            self.is_my_turn = self.user_id == data.turn;
            self.is_napoleon = self.user_id == data.napoleon;
            self.is_passed = self.pass_ids.indexOf(self.user_id) >= 0;

            $scope.$apply();
        });
    };

    $scope.$watch("game.game_id", function(){
        self.update();
        wsGame = new WebSocket("ws://192.168.56.2:8888/game/" + self.game_id); 
        wsGame.onmessage = function (evt) {
            var json = JSON.parse(evt.data); 
            if (json.update)
                self.update();  // 本来はAjaxでなくWebSocketで更新すべき
        };
    });

    this.send = function (json){
        wsGame.send(JSON.stringify(json));
    };
    
    this.pass = function(){
        self.send({"mode": "pass", "session_id": sid});
    };

    self.is_unused_careds_selected = function(){
        return self.unused.length >= self.rest.length;
    };

    self.select = function(card){
        if (!self.is_my_turn)
            return;

        if (self.is_unused_careds_selected())
            self.send({"mode": "unused", "session_id": sid, "selected": card, "unused": self.unused});

        else if (!elem(self.unused, card))
            self.unused.push(card);

    };

    self.unselect = function(card){
        remove(self.unused, card);
    };

    this.declare = function(){
        self.send({"mode": "declare", "declaration": self.declaration, "session_id": sid});
    };

    this.start = function(){
        self.send({"mode": "start"});
    };

    this.join = function(){
        self.send({"mode": "join", "session_id": sid, user_id: self.user_id});
    };

    this.quit = function(){
        self.send({"mode": "quit", "session_id": sid});
    };

    // utility
    function remove(list, item){
        var i = list.indexOf(item);
        if (i >= 0)
            list.splice(i, 1);
    }

    function elem(list, item){
        var i = list.indexOf(item);
        return (i >= 0) ? true : false;
    }

}]);