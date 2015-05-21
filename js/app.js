// Simple backbone app for Omas Client demo

window.BlobBuilder = window.BlobBuilder || window.WebKitBlobBuilder ||
                     window.MozBlobBuilder || window.MSBlobBuilder;
window.URL = window.URL || window.webkitURL;

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
  $(selector).html("<img src='../omas/images/load.gif' alt='loading'/>");
}

OmasClient.Utils.parseRangeVals = function (range) {
    field_el = $("#"+range);
    m = field_el.val();
    ranges = m.replace(" ", "").split(",");
    mm = []
    _.each(ranges, function(r){
      if (r.indexOf("-") == -1){
        if (!isNaN(parseInt(r))){
          mm.push(parseInt(r));
        }
        else {
          // error
          field_el.css("background-color", "#FA9191");
          setTimeout(function(){
            field_el.css('backgroundColor','white'); 
          }, 500);
          console.log("problem in singleton");
        }
      }
      else {
        parts = r.split("-")
        valid = []
        _.each(parts, function(p){
          if (isNaN(parseInt(p))){
            // error
            field_el.css("background-color", "#FA9191");
            setTimeout(function(){
              field_el.css('backgroundColor','white'); 
            }, 500);
            console.log("problem in range");
          }
          else {
            valid.push(parseInt(p))
          }          
        });
        if (valid.length == 2) {
          mm.push.apply(mm, _.range(valid[0], valid[1]+1))
        }
      }
    });
    return mm
  },

// Backcbone models

OmasClient.Info = Backbone.Model.extend({
  
  initialize: function(props){
    this.url = props.url;
  } 

});

OmasClient.StaffSel = Backbone.Model;
OmasClient.BeatSel = Backbone.Model;

OmasClient.Content = Backbone.Model;

// Global storage for EMA expression
OmasClient.EMAexpr = new Backbone.Model;

// Backbone views

OmasClient.App = Backbone.View.extend({
  el: "#main",

  events: {
    "submit #requestInfo" : "getInfo",
    "click #addstaves" : "addStaves",
    "click #resetstaves" : "resetStaves"
  },

  getInfo: function (e) {
    e.preventDefault();
    url = $(e.target).find("#meiUrl").val();
    encodedUrl = encodeURIComponent(url);
    new OmasClient.InfoView({model: 
      new OmasClient.Info({url: "http://mith.umd.edu/ema/"+encodedUrl+"/info.json"})
    });
  },

  addStaves: function (e) {
    e.preventDefault();
    $("#addstaves").hide();
    $("#resetstaves").removeClass("collapse");
    mm = OmasClient.Utils.parseRangeVals("measures");
    new OmasClient.StaffSelView({model: 
      new OmasClient.StaffSel({"measures":mm})
    }).render();
    // update EMA expr obj
    OmasClient.EMAexpr.set("measures", mm)
  },

  resetStaves: function (e) {
    e.preventDefault();
    mm = OmasClient.Utils.parseRangeVals("measures");
    new OmasClient.StaffSelView({model: 
      new OmasClient.StaffSel({"measures":mm})
    }).render();
    // update EMA expr obj
    OmasClient.EMAexpr.set("measures", mm)
  }
  
});

OmasClient.StaffSelView = Backbone.View.extend({
  template: _.template($('#staff-tpl').html()),

  el: "#g-staves",

  events: {
    "click #s_applyall" : "applyAll",
    "click #addbeats" : "addBeats",
    "click #resetbeats" : "resetBeats"    
  },

  applyAll: function (e) {
    e.preventDefault();
    target = $(e.target).data("ref");
    value = $(target).val();
    _.each(this.model.get("measures"), function(m){
      $("#staves_for_m"+m).val(value);
    });
  },

  addBeats: function (e) {
    e.preventDefault();
    $("#addbeats").hide();
    $("#resetbeats").removeClass("collapse");  
    OmasClient.EMAexpr.set("staves", []);
    _.each(OmasClient.EMAexpr.get("measures"), function(m){
      ss = OmasClient.Utils.parseRangeVals("staves_for_m"+m);
      mm = {"m_idx": m, "staves": ss};
      OmasClient.EMAexpr.get("staves").push(mm);
    });
    sel_mod = {"staves_by_measure": OmasClient.EMAexpr.get("staves")};
    new OmasClient.BeatSelView({"model": 
      new OmasClient.BeatSel(sel_mod)
    }).render();
  },

  resetBeats: function (e) {
    e.preventDefault();
    OmasClient.EMAexpr.set("staves", []);
    _.each(OmasClient.EMAexpr.get("measures"), function(m){
      ss = OmasClient.Utils.parseRangeVals("staves_for_m"+m);
      mm = {"m_idx": m, "staves": ss};
      OmasClient.EMAexpr.get("staves").push(mm);
    });
    sel_mod = {"staves_by_measure": OmasClient.EMAexpr.get("staves")};
    new OmasClient.BeatSelView({"model": 
      new OmasClient.BeatSel(sel_mod)
    }).render();
  },

  render: function () {
    this.$el.html(this.template(this.model.toJSON()));
  }
});

OmasClient.BeatSelView = Backbone.View.extend({
  template: _.template($('#beat-tpl').html()),

  el: "#g-beats",

  events: {
    "click #b_applyalls" : "applyAllStaves",
    "click #b_applyall" : "applyAll",
    "click #getselection" : "getSelection"
  },

  applyAll: function (e) {
    e.preventDefault();
    target = $(e.target).data("ref");
    value = $(target).val();
    _.each(this.model.get("staves_by_measure"), function(m){
      $("[id^=beats_for_m"+m.m_idx+"]").val(value);
    });
  },

  applyAllStaves: function (e) {
    e.preventDefault();
    target = $(e.target).data("ref");
    value = $(target).val();
    measure = parseInt(/for_m(\d+)_/.exec(target)[1]);
    _.each(this.model.get("staves_by_measure"), function(m){
      if (m.m_idx == measure){
        _.each(m.staves, function(s){
          $("#beats_for_m"+measure+"_s"+s).val(value);
        });
      }
    });
  },

  getSelection: function (e) {
    e.preventDefault();
    OmasClient.EMAexpr.set("beats", []);
    _.each(OmasClient.EMAexpr.get("staves"), function(measure){
      m_obj = {"m_idx": measure.m_idx, "staves": []}
      _.each(measure.staves, function(staff){
        b = $("#beats_for_m"+measure.m_idx+"_s"+staff).val();
        m_obj["staves"].push({"s_idx": staff, "beats": b});
      });
      OmasClient.EMAexpr.get("beats").push(m_obj);
    });
    url = $("#meiUrl").val();
    if (url == '' || !url) {
      OmasClient.Utils.alert('"Enter a URL "in MEI location"', 2000);
    }
    else {
      $("#dataTabs a:last").tab("show");
      OmasClient.Utils.showLoader("#mei");

      measureSel = "";
      staffSel = "";
      beatSel = "";
      _.each(OmasClient.EMAexpr.get("beats"), function(measure, i_m) {
        measureSel += measure.m_idx;
        _.each(measure.staves, function(staff, i_s){
          sidx = String(staff.s_idx);
          staffSel += sidx.replace(",","+");
          beatSel += "@"+staff.beats.replace(",","@");
          if (i_s+1 < measure.staves.length){
            staffSel += "+"
            beatSel += "+";
          }
        });
        if (i_m+1 < OmasClient.EMAexpr.get("beats").length){
          measureSel += ",";
          staffSel += ","
          beatSel += ",";
        }
      });

      encodedUrl = encodeURIComponent(url);
      reqUrl = "http://mith.umd.edu/ema/"
             + encodedUrl + "/"
             + measureSel + "/"
             + staffSel + "/"
             + beatSel

      $.get(reqUrl, function (data) {
        doc = (new XMLSerializer()).serializeToString(data);
        esc_doc = doc.replace(/</g, "&lt;").replace(/>/g, "&gt;");
        new OmasClient.ContentView({model : 
          new OmasClient.Content({reqUrl: reqUrl, lang: "markup", data: esc_doc})
        }).render();
        Prism.highlightAll();
        // Create a sessionStorage object for rendering and other operations
        sessionStorage.setItem('MEI', doc);  
      }).fail( function (resp) {
        data = JSON.stringify(resp.responseJSON, undefined, 2);
        Prism.highlightAll();
      });

    }
  },

  render: function () {
    this.$el.html(this.template(this.model.toJSON()));
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
    var p = $("<pre/>");
    p.html(JSON.stringify(j, undefined, 2));
    this.$el.find("#json").html(p);
    // Render summary view
    this.$el.find("#summary").html(this.template(j));
  }

});

OmasClient.ContentView = Backbone.View.extend({

  template: _.template($('#mei-tpl').html()),

  el: "#mei",

  render: function () { 
    // Render summary view
    this.$el.html(this.template(this.model.toJSON()));
    mei = sessionStorage.getItem("MEI");
    var b = new Blob([mei]);
    url = window.URL.createObjectURL(b)
    d = this.$el.find("#download");
    d.attr("href", url).attr("download", "mei-slice.xml");

  }

});

// And this is where we start:
new OmasClient.App;

// Some extra code for bootstrap tabs

$('#dataTabs a').click(function (e) {
  e.preventDefault();
  $(this).tab('show');
});