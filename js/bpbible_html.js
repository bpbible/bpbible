
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
		// We used to do .page_segment:last-child but it broke when we
		// encountered bad html in AmTract (e.g. article Lord) where it didn't
		// close the <b> tags and parsing went awry
		var page_segments = $(".page_segment");
		if (!page_segments.length) alert("No page segments found!!!");
		var last_page_segment = page_segments[page_segments.length-1];
		var c = load_text(last_page_segment, false);
		if (!c) break;
		c.appendTo("#content");
		cnt++;
	}
	if(cnt == 10) d("Didn't work\n");
}

function remove_excess_page_segments() {
	var page_segments = $(".page_segment");
	var start_segment_index = -1;
	var end_segment_index = -1;
	var startY = window.scrollY;
	var endY = window.scrollY + window.innerHeight;
	for (var index = 0; index < page_segments.length; index++)	{
		var page_segment = $(page_segments.get(index));
		var segment_top = page_segment.offset().top;
		var segment_bottom = segment_top + page_segment.attr('offsetHeight');
		var is_on_screen = (segment_top < endY && segment_bottom > startY);
		if (is_on_screen)	{
			if (start_segment_index == -1)	{
				start_segment_index = index;
			}
			end_segment_index = index;
		}
	}

	var MIN_SEGMENTS_TO_LEAVE = 2;
	var MIN_PIXELS_TO_LEAVE = 800;
	for (index = page_segments.length - 1; index > end_segment_index + MIN_SEGMENTS_TO_LEAVE; index--)	{
		page_segment = $(page_segments.get(index));
		segment_top = page_segment.offset().top;
		segment_bottom = segment_top + page_segment.attr('offsetHeight');
		if (page_segment.offset().top > endY + MIN_PIXELS_TO_LEAVE)	{
			page_segment.remove();
		} else {
			break;
		}
	}

	var deleted_items_height = 0;
	for (index = start_segment_index - MIN_SEGMENTS_TO_LEAVE - 1; index >= 0; index--)	{
		var page_segment = $(page_segments.get(index));
		var segment_bottom = page_segment.offset().top + page_segment.attr('offsetHeight');
		if (segment_bottom < startY - MIN_PIXELS_TO_LEAVE)	{
			deleted_items_height += page_segment.attr('offsetHeight');
			page_segment.remove();
		}
	}

	if (deleted_items_height > 0)	{
		window.scrollTo(window.scrollX, startY - deleted_items_height);
	}
}

var reentrancy_check = false;
function ensure_sufficient_content() {
	var ref =  $("#content").children()[0];
	var ref_height = $(ref).offset().top;
	// We may be called re-entrantly if it is scrolling while we add content,
	// for example. This is very bad to allow (we can load one chapter more
	// than once).
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
	remove_excess_page_segments();
	
	reentrancy_check = false;	
}

function load_text(item, before) {
	if (!item) {
		d("ERROR!!!!! Load text, but not item");
		return null;
	}
	var i = item.getElementsByClassName("segment");
	if (!i.length) {
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
		t = "";
	}
	return $(t);
}
	

$(document).ready(function(){
	d("ready!!!!" + window.location.href);

	d(window.top.document.title);
	// Scroll to current first; if this is big enough and we are far enough
	// down, we may not have to load content above us.

	toggle_filler(true);
	scroll_to_current();
	$("body").bind("DOMAttrModified", function(event) {
		if(event.attrName == "continuous_scrolling")
			set_continuous(event.newValue == "true");
	});

	set_continuous($('body[continuous_scrolling="true"]').length);
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
		$(".filler").remove();
	}

	window.scrollBy(0, $("#content").offset().top - oldTop);
	
}

function continuous_onsize() {ensure_sufficient_content()};
function set_continuous(to) {
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

/* Try and keep in middle
 -40 is to correct for verse length, as we do not want start of 
 verse to start half way down, but the middle to be in the middle */
function get_scroll_point() {
	return {top:  window.innerHeight < 240 ? 
		Math.max(window.innerHeight/2 - 40, 0) : 120,
			left: window.innerWidth/2};
}

function scroll_to_current(start) {
	do_scroll_to_current(start, 0);
}

function do_scroll_to_current(start, call_count) {
	// get_start_point define in page_view and chapter_view
	if(!start) start = get_start_point();
	// Now scroll down to the right point
	var off = start.offset();
	var t = off.top;
	var l = off.left;
	var offset = get_scroll_point();
	t -= offset.top;
	l -= offset.left;
	/*
	 * If the window does not yet have enough content to make this the top
	 * element on screen by scrolling it, then wait a bit and try scrolling
	 * again.
	 */
	if ((t + window.innerHeight > document.height) && call_count <= 10) {
		window.setTimeout(do_scroll_to_current, 25, start, call_count + 1);
		return;
	}
	
	window.scrollTo(l, t);
}

function find_current_segment() {
	var top = window.scrollY + get_scroll_point().top;
	var current_segment = null;
	var page_segments = $('.page_segment');
	page_segments.each(function() {
		var segment = $(this);
		if (segment.offset().top + this.offsetHeight >= top) {
			current_segment = segment;
			return false;
		}
		return true;
	});
	return current_segment;
}
