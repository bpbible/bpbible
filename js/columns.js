$(document).ready(function(){	
	set_columns($('body[columns="true"]').length);
	$("body").bind("DOMAttrModified", function(event) {
		if(event.attrName != "columns") {
			if(event.attrName != "style" && $('body[columns="true"]'.length)) {
				// setting an option, may need to resize
				handle_resize();
			}
			return;			
		}
		set_columns(event.newValue == "true");
	});
});

var hyphenation_setting = true;
var on_loading = true;
function set_columns(to) {
	var was_on_loading = on_loading;
	if(!to) {
		var v = $("#HyphenatorToggleBox");
		if(v.length) {
			//alert("Turning off");
			// Now turn it off just in case
			hyphenation_setting = v[0].firstChild.data == 'Hy-phe-na-ti-on';
			if(hyphenation_setting) 
				Hyphenator.toggleHyphenation();
		
			$(window).unbind('resize', handle_resize);
		}
	} else {
		//alert("Running");
		$("#content").addClass("hyphenate");
		var hyphenatorSettings = {
			onhyphenationdonecallback : function () {
				if(was_on_loading) 
					scroll_to_current(null);

				$(window).bind('resize', handle_resize);
				if(!hyphenation_setting) {
					Hyphenator.toggleHyphenation();
				}
			},
			onerrorhandler : function(e) {
				jserror("Hyphenate error: " + e.message);
				$("#content")[0].style.removeProperty('visibility');

			}
		};
		Hyphenator.config(hyphenatorSettings);
		Hyphenator.run();

	}
	on_loading = false;
	
}


var next = "inherit";
function handle_resize(twice, dont_reflow) {
	var c = $("#content");

	// Body has an 8px margin
	c.height($(window).height() - c.offset().top - 8);
}

function toggle() {
	if(document.body.getAttribute("columns") == "true")
		document.body.setAttribute("columns", "false");
	else
		document.body.setAttribute("columns", "true");		
}
