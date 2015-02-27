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

      var startM = $(e.target).find("#startM").val(),
          endM = $(e.target).find("#endM").val(),
          staves = $(e.target).find("#staves").val(),
          startBeat = $(e.target).find("#startB").val(),
          endBeat = $(e.target).find("#endB").val(),
          opt_raw = $(e.target).find("#opt_raw").is(":checked"),
          opt_signature = $(e.target).find("#opt_signature").is(":checked"),
          opt_nospace = $(e.target).find("#opt_nospace").is(":checked"),
          opt_cut = $(e.target).find("#opt_cut").is(":checked");

      var options = []
      if (opt_raw) {options.push("raw")}
      if (opt_signature) {options.push("signature")}
      if (opt_nospace) {options.push("nospace")}
      if (opt_cut) {options.push("cut")}
      var options_str = options.join();

      encodedUrl = encodeURIComponent(url);
      reqUrl = "http://ema.mith.org/"
             + encodedUrl + "/"
             + startM + "-"
             + endM + "/"
             + staves + "/"
             + startBeat + "-"
             + endBeat;

      if (options_str) {
        reqUrl += "/" + options_str;
      }

      var pre = $("<pre/>"),
          code = $("<code class='language-markup'/>");

      pre.html(code);

      $.get(reqUrl, function (data) {
        doc = (new XMLSerializer()).serializeToString(data);
        doc = doc.replace(/</g, "&lt;").replace(/>/g, "&gt;")          
        code.html(doc);
        $("#mei").html(pre);   
        Prism.highlightAll();    
      }).fail( function (resp) {
        code.html(JSON.stringify(resp.responseJSON, undefined, 2));
        $("#mei").html(pre);
        Prism.highlightAll();
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