var app = angular.module("GameApp", []);

app.config(function($interpolateProvider) {
    $interpolateProvider.startSymbol('[[');
    $interpolateProvider.endSymbol(']]');
});

app.controller("GameController", ["$scope", function($scope){
    var wsGame;
    var self = this;
    self.is_error = false;
    self.is_close = false;
    self.unused = [];

    this.update = function(){
        $.get(urls.state + self.game_id, {}, function(data){
            $.extend(self, data);

            self.impossible_card = null;
            self.is_my_turn = self.user_id == data.turn;
            self.is_napoleon = self.user_id == data.napoleon;
            self.is_passed = elem(self.pass_ids, self.user_id);

            $scope.$apply();
        });
    };

    $scope.$watch("game.game_id", function(){
        self.update();
        wsGame = new WebSocket(urls.room + self.game_id);
        wsGame.onmessage = function (evt) {
            var json = JSON.parse(evt.data);
            if (json.update)
                self.update();  // 本来はAjaxでなくWebSocketで更新すべき
        };
        wsGame.onerror = function(err){  // when is this called?
            self.is_error = true;
        };
        wsGame.onclose = function(evt){
            self.is_close = true;
        };
    });

    this.send = function (json){
        if (json === undefined)
            json = {};
        json["session_id"] = $.cookie("sessionid");
        wsGame.send(JSON.stringify(json));
    };

    this.pass = function(){
        self.send({"action": "pass"});
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
        $scope.$apply();
    };

    self.unselect = function(card){
        remove(self.unused, card);
        self.hand.push(card);
    };

    self.select = function(card){
        if (!self.is_my_turn)
            return;
        else if (!elem(self.possible_cards, card.value)){
            self.impossible_card = card;
            return;
        }
        self.send({"selected": card.value});
    };

    self.determine_adjutant = function(){
        self.send({"adjutant": self.adjutant});
    };

    this.declare = function(){
        self.send({"action": "declare", "declaration": self.declaration});
    };

    this.start = function(){
        self.send();
    };

    this.post = function(url){
        $.post(url, {"csrfmiddlewaretoken": csrf_token}, self.update);
    };

    this.join = function(){
        self.post(urls.join);
    };

    this.quit = function(){
        self.post(urls.quit);
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
