var app = angular.module("GameApp", []);

app.config(function($interpolateProvider) {
    $interpolateProvider.startSymbol('[[');
    $interpolateProvider.endSymbol(']]');
});

app.controller("GameController", ["$scope", function($scope){
    var wsGame = new WebSocket(urls.room);
    var self = this;
    self.is_error = false;
    self.is_close = false;
    self.declaration = null;
    self.unused = [];

    // When a player selects a card which can't be on a board, warn the card
    self.impossible_card = null;

    this.update = function(){
        $.get(urls.state, {}, function(data){
            $.extend(self, data);
            self.impossible_card = null;
            $scope.$apply();
        });
    };
    self.update();  // shoud update at init

    wsGame = new WebSocket(urls.room);
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

    this.send = function (json){
        if (json === undefined)
            json = {};
        json["session_id"] = $.cookie("sessionid");
        // for (var i = 0; i < 10; i++)
        wsGame.send(JSON.stringify(json));
    };

    this.pass = function(){
        self.send({"action": "pass"});
    };

    self.is_unused_careds_selected = function(){
        return self.unused.length >= self.state.rest.length;
    };

    self.select_or_discard = function(card){
        if (self.state.phase.current == 'discard')
            self.discard(card);
        else if (self.state.phase.current == 'first_round' || self.state.phase.current == 'rounds')
            self.select(card);
    };

    self.discard = function(card){
        if (!elem(self.unused, card)){
            self.unused.push(card);
            remove(self.myself.hand, card);
        }
        var unused = self.unused.map(function(i){ return i.value;});
        if (self.is_unused_careds_selected())
            self.send({"action": "discard", "unused": unused});
    };

    self.unselect = function(card){
        remove(self.unused, card);
        self.myself.hand.push(card);
    };

    self.select = function(card){
        var values = self.myself.possible_cards.map(function(i){ return i.value;});
        if (!elem(values, card.value)){
            self.impossible_card = card;
            return;
        }
        self.send({"action": "select", "selected": card.value});
    };

    self.determine_adjutant = function(){
        self.send({"action": "adjutant", "adjutant": self.adjutant});
    };

    this.declare = function(){
        self.send({"action": "declare", "declaration": self.declaration});
    };

    this.start = function(){
        self.send({"action": "start"});
    };

    this.post = function(url){
        $.post(url, {"csrfmiddlewaretoken": csrf_token}, function(){
            self.send();  // just update on all the player's browsers
        });
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
