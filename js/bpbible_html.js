function d(str) {
	if (typeof console != "undefined" && console.log) console.log(str);
	if ((typeof str == "string" && !str.match(/\n$/)) || typeof str == "number")
		dump(str + "\n");
	else dump(str);
}

// dump to the js console (xulrunner -jsconsole)
function jsdump(str)
{
	dump(str);
/*	Components.classes['@mozilla.org/consoleservice;1']
			  .getService(Components.interfaces.nsIConsoleService)
			  .logStringMessage(str);*/
}

function jserror(str)
{
	Components.utils.reportError(str);
}

function pick_element(selector, range, before) {
	var last = null;
	var done = false;
	$(selector).each(function() {
		// 0 means inside range, 1 means we have passed it
		// If we are not before, and we are inside the range, but we are 
		// right on the right-hand edge of it, (or on the far left hand edge
		// if before is set) we should use this one
		var r = range.comparePoint(this, 0);
		if (r == 0) {
			if(before) {
				// If we are looking for the previous one, and we have now
				// entered the range, use the last one, as long as we have
				// something significant selected in the previous verse
				var newRange1 = range.cloneRange();
				newRange1.setStartAfter(this);
				if(range.toString().replace(/^\s+/, '') == newRange1.toString().replace(/^\s+/, ''))
				{
					last = this;
				}
				done = true;
			}
			else {
				var newRange1 = range.cloneRange();
				newRange1.setEndAfter(this);
				if(range.toString().replace(/\s+$/, '') == newRange1.toString().replace(/\s+$/, ''))
				{
					last = this;
					done = true;
				}
			}
			
			if(!done)
				last = this;

			return !done;
		}
		if (r > 0) {
			if(!before) last = this;
			if(before && !last) {
				alert("Before but not last? pre-something content selected?");
				last = this;
			}
			
			// Stop processing
			done = true;
			return false;
		}
		//if(r == 0) alert("Right on the spot? really?");

		last = this;
		return true;
	});

	if(!done) alert("Didn't finalize element finding " + selector)
	if(!last) alert("Last is null!");

	return last;
}

function get_normalized_selection(){
	var selection = window.getSelection();

	// We ignore multiple selections At the Moment
	var range = selection.getRangeAt(0);
	if(range.collapsed) return null;
	return range;
}

function get_scroll_offset() {
	return 300;
	return window.innerHeight;
}

var reached_top = false;
function load_above() {
	var filler = $(".filler");
	var filler_offset = filler.length > 0 ?  filler[0].offsetHeight: 0;
	var cnt = 0;
	const LOAD_OFFSET = get_scroll_offset() + filler_offset;
	var ref =  $("#content").children()[0];
	var ref_height = $(ref).offset().top;
	while (window.scrollY < LOAD_OFFSET && cnt < 10) {
		var c = load_text($(".page_segment:first-child")[0], true);
		if (!c) break;
		c.prependTo("#content");
		process_new_text(c);
		var diff = $(ref).offset().top - ref_height;
		if (diff != Math.ceil(diff)) 
			d("Non-rounded pixel values in load_above: " + diff);
		window.scrollBy(0, diff);
		if (!c[0].getElementsByClassName("segment").length) {
			reached_top = true;
			toggle_filler(false);
		}
		ref_height = $(ref).offset().top;
		
		cnt++;
	}
	
	if(cnt == 10) d("Didn't work\n");
}

function load_below() {
	const LOAD_OFFSET = get_scroll_offset();
	
	var cnt = 0;
	while (window.scrollMaxY - window.scrollY < LOAD_OFFSET && cnt < 10) {
		var c = load_text($(".page_segment:last-child")[0], false);
		if (!c) break;
		c.appendTo("#content");
		process_new_text(c);
		cnt++;
	}
	if(cnt == 10) d("Didn't work\n");
}

var reentrancy_check = false;
function ensure_sufficient_content() {
//	dump("Ensure sufficient content being called\n");
	var ref =  $("#content").children()[0];
	var ref_height = $(ref).offset().top;
//	dump(window.scrollY + "\n");
	// We may be called re-entrantly if it is scrolling while we add content,
	// for example. This is very bad to allow (we can load one chapter more
	// than once
	if(reentrancy_check) return;
	reentrancy_check = true;
	if(document.body.getAttribute("columns") == "true")
	{
		d("Not proceeding as this doesn't work for columns yet...");
		reentrancy_check = false;
		
		return;
	}

	// Loading underneath is reasonably safe, while loading above is tricky
	// (as we have to scroll).
	// I've found that in the TSK, we don't scroll to the right spot if these
	// are the other way around...
	load_below();
	load_above();
	
	reentrancy_check = false;	
}

function load_text(item, before) {
	var i = item.getElementsByClassName("segment");
	if (!i.length) {
		//d("Reached first/last item, quitting\n");
		return null;
	}

	if (i.length != 1) {
		alert("ERROR: Too many page_segments, aborting\n");
		return null;		
	}

	var ref_id = i[0].getAttribute("ref_id");

	var request = new XMLHttpRequest();
	var t;
	
	// We don't like XML errors, but unless we change this mime-type (or I
	// suppose in the channel), we get them.
	request.overrideMimeType("text/x-bm");

	try {
		request.open("GET", "bpbible://content/pagefrag/" + $("body").attr("module") + "/" + ref_id + "/" + (before?"previous": "next"), false);
		request.send(null);
		t = request.responseText;
	} catch (e) {
		// Fallback for in firebug in firefox or something - pretty boring
		d(e);
		t = "<div class='page_segment'><div class='segment' ref_id='test'>text<br>test<ul><li>item1<li>item2</ul></div></div>";
	}
	return $(t);
}

function dispatch_event(firer, leaving) {
	d("Dispatching event\n");
	var element = document.createElement("MyExtensionDataElement");
	element.setAttribute("id", "process_tooltip");
	element.setAttribute("href", firer.getAttribute("href"));
	element.setAttribute("leaving", leaving ? "true" : "false");
	var hadId = Boolean(firer.id);
	if (hadId) {
		alert("Had ID?!?");
		var old_id = firer.getAttribute("id");
	} else {
		firer.id = "firer";
	}
	element.setAttribute("firer", firer.id);
	document.documentElement.appendChild(element);

	var evt = document.createEvent("Event");
	evt.initEvent("process_tooltip", true, false);
	element.dispatchEvent(evt);

	/* I hope/presume that dispatchEvent is synchronous... :D */
	element.parentNode.removeChild(element);
	if (!hadId) {
		firer.id = "";
	}
}

function process_new_text(c) {
	c.find('a[href]').bind("mouseleave", function(){
		dispatch_event(this, true);
	});
		
	c.find('a[href]').bind("mouseenter", function(){
		dispatch_event(this, false);
	});
}
	

$(document).ready(function(){
	d("ready!!!!" + window.location.href);

	d(window.top.document.title);
/*	window.addEventListener( 'pageshow', function(e){ d('!!!!!!!!!!!!!!pageshow fired'); }, false );
	window.addEventListener( 'pagehide', function(e){ d('!!!!!!!!!!!!!!pagehide fired'); }, false );*/

	// Scroll to current first; if this is big enough and we are far enough
	// down, we may not have to load content above us.

	toggle_filler(true);
	scroll_to_current();
	$("body").bind("DOMAttrModified", function(event) {
		if(event.attrName == "continuous_scrolling")
			set_continuous(event.newValue == "true");
	});

	set_continuous($('body[continuous_scrolling="true"]').length);
	process_new_text($("#content"));
	
});

function toggle_filler(to) {
	/* we keep a friendly blank area around so that we can scroll to the top
	 * of a chapter before the previous one has loaded and not jump around so
	 * much */
	var oldTop = $("#content").offset().top;
	if (to) {
		if (!reached_top && $(".filler").length == 0) {
			$("body").prepend("<div class='filler'><div class='infiller'></div>Loading...</div>");
			$("div.infiller").height(120);
		}
	} else {
		d("removing it");
		$(".filler").remove();
	}

	window.scrollBy(0, $("#content").offset().top - oldTop);
	
}

function continuous_onsize() {ensure_sufficient_content()};
function set_continuous(to) {
//	alert("set", to);
	if (!to) {
		toggle_filler(false);
		$(window).unbind('resize', continuous_onsize);
		$(window).unbind('scroll', continuous_onsize);
	} else {
		toggle_filler(true);
		$(window).scroll(continuous_onsize);
		$(window).resize(continuous_onsize);
		ensure_sufficient_content();
	}
}

function get_scroll_point() {
	return {top:  window.innerHeight < 240 ? 
		Math.max(window.innerHeight/2 - 40, 0) : 120,
			left: window.innerWidth/2};
}

function scroll_to_current(start) {
	// get_start_point define in page_view and chapter_view
	if(!start) start = get_start_point();
	//alert(start);
	// Now scroll down to the right point
	var off = start.offset();
	var t = off.top;
	var l = off.left;
	/* Try and keep in middle
	 -40 is to correct for verse length, as we do not want start of 
	 verse to start half way down, but the middle to be in the middle */
	var offset = get_scroll_point();
	t -= offset.top;
	l -= offset.left;
	
	window.scrollTo(l, t);
	d(t + "," + l);

}


