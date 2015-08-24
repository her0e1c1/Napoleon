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
            self.is_passed = elem(self.pass_ids, self.user_id);

            $scope.$apply();

            if (data.waiting_next_turn){
                var time = 1 * 1000;
                $("body").delay(time).queue(function(){
                    self.next_turn();
                });
            }
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
        json["session_id"] = sid;
        wsGame.send(JSON.stringify(json));
    };

    self.next_turn = function(){
        self.send({"next_turn": true});
    };

    this.pass = function(){
        self.send({"mode": "pass"});
    };

    self.is_unused_careds_selected = function(){
        return self.unused.length >= self.rest.length;
    };

    self.select_or_discard = function(card){
        if (self.phase == 'discard' && self.is_napoleon)
            self.discard(card);
        else if (self.is_my_turn && (self.phase == 'first_round' || self.phase == 'rounds'))
            self.select(card);
    };

    self.discard = function(card){
        var unused = self.unused.map(function(i){ return i.value;});
        if (self.is_unused_careds_selected())
            self.send({"selected": card.value, "unused": unused});
        else if (!elem(self.unused, card)){
            self.unused.push(card);
            remove(self.hand, card);
        }
    };

    self.unselect = function(card){
        remove(self.unused, card);
        self.hand.push(card);
    };

    self.select = function(card){
        if (!self.is_my_turn)
            return;
        else if (!elem(self.possible_cards, card.value)){
            alert("You can't select");
            return;
        }
        self.send({"mode": "select", "selected": card.value});
    };

    self.determine_adjutant = function(){
        self.send({"mode": "adjutant", "adjutant": self.adjutant});
    };

    this.declare = function(){
        self.send({"mode": "declare", "declaration": self.declaration});
    };

    this.start = function(){
        self.send({"mode": "start"});
    };

    this.join = function(){
        self.send({"mode": "join", user_id: self.user_id});
    };

    this.quit = function(){
        self.send({"mode": "quit"});
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
