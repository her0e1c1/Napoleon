var app = angular.module("GameApp", ['ngSanitize']);

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

    // When a player sends data to a server, he can't select any before he gets its response.
    self.disabled = false;

    this.update = function(state){
        var myself = _.find(state.players, (function(p){
            return p.user_id == user_id;
        }));
        state["turn"] = _.find(state.players, (function(p){
            return p.user_id == state.turn_user_id;
        }));

        $.extend(self, {"state": state, "myself": myself});
        self.impossible_card = null;
        self.disabled = false;
        $scope.$apply();
    };

    // shoud update at init
    $.get(urls.state, {}, function(data){
        self.update(data.state);
    });

    wsGame = new WebSocket(urls.room);
    wsGame.onmessage = function (evt) {
        self.update(JSON.parse(evt.data));
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
        json["session_id"] = $.cookie("sessionid") || $.cookie("user_session");
        wsGame.send(JSON.stringify(json));
        self.disabled = true;
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
        else if (self.state.phase.current == 'first_round'
              || self.state.phase.current == 'rounds')
            self.select(card);
    };

    self.discard = function(card){
        if (!_.contains(self.unused, card)){
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
        if (!_.contains(values, card.value)){
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

    this.post = function(url, json){
        if (json === undefined)
            json = {};
        json["csrfmiddlewaretoken"] = csrf_token;
        $.post(url, json, function(){
            self.send();  // just update on all the player's browsers
        });
    };

    this.add = function(name){
        self.post(urls.add, {"name": name});
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
}]);
