// Simple backbone app for Omas Client demo

this.OmasClient = {};

OmasClient.Utils = {};

OmasClient.Utils.alert = function (msg, delay) {
  var alert = $('<div class="alert alert-danger" role="alert"> \
      <span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> \
      <span class="sr-only">Error:</span>'+msg+'</div>');
  $("#status").html(alert);
  alert.alert();
  window.setTimeout(function() { alert.alert('close') }, delay);
}

OmasClient.Utils.showLoader = function (selector) {
  $(selector).html("<img src='load.gif' alt='loading'/>");
}

// Backcbone models

OmasClient.Info = Backbone.Model.extend({
  
  initialize: function(props){
    this.url = props.url;
  } 

});

// OmasClient.InfoData = new OmasClient.Info;

// Backbone views

OmasClient.App = Backbone.View.extend({
  el: "#main",

  events: {
    "submit #requestInfo" : "getInfo",
    "submit #sendSelection" : "getSelection"
  },

  getInfo: function (e) {
    e.preventDefault();
    url = $(e.target).find("#meiUrl").val();
    encodedUrl = encodeURIComponent(url);
    new OmasClient.InfoView({model: 
      new OmasClient.Info({url: "http://54.152.53.212/"+encodedUrl+"/info.json"})
    });
  },

  getSelection: function (e) {
    e.preventDefault();    
    url = $("#meiUrl").val();
    if (url == '' || !url) {
      OmasClient.Utils.alert('"Enter a URL "in MEI location"', 2000);
    }
    else {
      $("#dataTabs a:last").tab("show");
      OmasClient.Utils.showLoader("#mei");

      var startM = $(e.target).find("#startM").val();
      var endM = $(e.target).find("#endM").val();
      var staves = $(e.target).find("#staves").val();
      var startBeat = $(e.target).find("#startB").val();
      var endBeat = $(e.target).find("#endB").val();

      encodedUrl = encodeURIComponent(url);
      reqUrl = "http://54.152.53.212/"
             + encodedUrl + "/"
             + startM + "-"
             + endM + "/"
             + staves + "/"
             + startBeat + "-"
             + endBeat;

      $.get(reqUrl, function (data) {
        var p = $("<pre class='pre-scrollable'/>");
        doc = (new XMLSerializer()).serializeToString(data);
        doc = doc.replace(/</g, "&lt;").replace(/>/g, "&gt;")          
        p.html(doc);
        $("#mei").html(p);        
      }).fail( function (resp) {
        var p = $("<pre class='pre-scrollable'/>");
        p.html(JSON.stringify(resp.responseJSON, undefined, 2));
        $("#mei").html(p);
      });
    }
  }
  
});

OmasClient.InfoView = Backbone.View.extend({

  template: _.template($('#info-tpl').html()),

  el: "#info",

  initialize: function () {
    this.model.fetch();
    $("#dataTabs a:first").tab("show");
    OmasClient.Utils.showLoader(this.$el.find("#summary"));
    this.listenTo(this.model, "change", this.render);
  },

  render: function () {    
    var j = this.model.toJSON();
    // Paste the JSON as is 
    var p = $("<pre class='pre-scrollable'/>");
    p.html(JSON.stringify(j, undefined, 2));
    this.$el.find("#json").html(p);
    // Render summary view
    this.$el.find("#summary").html(this.template(j));
  }

});

// And this is where we start:
new OmasClient.App;

// Some extra code for bootstrap tabs

$('#dataTabs a').click(function (e) {
  e.preventDefault();
  $(this).tab('show');
});