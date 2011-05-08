function get_start_point(){
	return get_current_verse_bounds()[0];
}


function highlight_verse(){
	var osisRef = get_current_verse_ref();
	var old_highlight = $('.had_highlight[highlighted_reference="' + osisRef + '"]');
	if (old_highlight.length) {
		old_highlight.addClass("highlight");
		return;
	}
		
	var [start, end] = get_current_verse_bounds();

	if (start[0]) {
		// Highlight the verse's background
		highlight_range(start[0], end[0], ["highlighted_reference", osisRef]);
	}
}

/* Find the current reference on screen to use when changing versions, etc.
 * This returns the actual current reference if it is on or near the screen.
 * Otherwise, it returns the top verse currently visible on the screen.
 */
function get_current_reference_on_screen()	{
	var CURRENT_VERSE_OFFSCREEN_ALLOWANCE = 200;
	var top = window.scrollY - CURRENT_VERSE_OFFSCREEN_ALLOWANCE;
	var bottom = window.innerHeight + window.scrollY +CURRENT_VERSE_OFFSCREEN_ALLOWANCE;
	var [start, end] = get_current_verse_bounds();
	var current_reference_top = start.offset().top;
	var current_reference_bottom = end.offset().top + end.attr('offsetHeight');
	if (current_reference_top < bottom && current_reference_bottom > top)	{
		return start.get(0).getAttribute("osisRef");
	}

	var [first, _last] = get_current_reference_range_bounding_elements();

	return first.getAttribute("osisRef");
}

function get_current_reference_range_bounding_elements()	{
	var top = window.scrollY;
	var bottom = window.innerHeight + window.scrollY;

	// Don't use chapter numbers
	var start = $('a.vnumber');
	var end = $('a.vnumber');
	var first = null;
	/* TODO: we can narrow down based on our page segments first... */
	start.each(function() {
		if ($(this).offset().top + this.offsetHeight >= top) {
			first = this;
			return false;
		}
		return true;
	});

	var last = null;
	$(end).each(function() {
		if ($(this).offset().top >= bottom) {
			if (!last) d("Not last");
			return false;
		}
		last = this;
		return true;
	});
	return [first, last];
}

function get_current_reference_range()	{
	var [first, last] = get_current_reference_range_bounding_elements();
	var ref1 = first.getAttribute("reference");
	var ref2 = last.getAttribute("reference");
	
	if(!ref1 || !ref2) d("Not ref1 or ref2 '" + ref1 + "' '" + ref2 + "'");

	function extract_reference(ref) {
		if(!ref.match(":")) ref += ":1";
		var d = ref.match(/(.+) (\d+):(\d+)/);
		if (d) return d;
		
		// single chapter book
		var [whole, book, verse] = ref.match(/(.+):(\d+)/);
		whole = whole.replace(":", " ");
		return [whole, book, null, verse];
	}
			
	var [whole1, book1, chapter1, verse1] = extract_reference(ref1);
	var [whole2, book2, chapter2, verse2] = extract_reference(ref2);

	var delim = "-";
	if (book1 == book2)	{
		if(chapter1 == chapter2 || !chapter2)	{
			whole2 = verse2;
			if (verse1 == verse2) {
				/* If the two references are the same, only show the first one. */
				whole2 = "";
				delim = "";
			}
		} else	{
			whole2 = chapter2 + ":" + verse2;
		}
	}
	return whole1 + delim + whole2;
}

function show_current_reference() {
	fill_reference_bar();
	update_header_bar();
}

function fill_reference_bar() {
	$("div.reference_bar").text(get_current_reference_range());
}

function create_reference_bar() {
	$("body").prepend('<div class="reference_bar">This should give the current reference</div>');
}

var last_chapter_in_header_bar = null;
function update_header_bar() {
	var current_chapter = find_current_chapter();
	if (current_chapter == last_chapter_in_header_bar) {
		return;
	}

	last_chapter_in_header_bar = current_chapter;
	var event = document.createEvent("Event");
	event.initEvent('ChangeChapter', true, true);
	document.body.dispatchEvent(event);
}

function find_current_chapter() {
	var top = window.scrollY + get_scroll_point().top;
	var chapter1 = '';
	var page_segments = $('.page_segment');
	page_segments.each(function() {
		if ($(this).offset().top + this.offsetHeight >= top) {
			chapter1 = this.firstChild.firstChild.getAttribute('osisRef');
			return false;
		}
		return true;
	});
	return chapter1;
}

$(document).ready(function() {
	highlight_verse();
	create_reference_bar();
	$(window).scroll(function() {show_current_reference()});
	$(window).resize(function() {show_current_reference()});
	show_current_reference();
	setup_drag_drop_handler();

/*	var [start, end] = get_current_verse_bounds();
	scroll_to_current(start);*/
	
});

function get_current_verse() {
	//var current_verse = $("#original_segment a.currentverse");
	var current_verse = $("a.currentverse");
	if(current_verse.length != 1) {
		jsdump("Wrong number of current verses: " + current_verse.length + "\n");
		return current_verse;
	}
	return current_verse;
}

function get_current_verse_ref() {
	var current_verse = get_current_verse();
	return current_verse.attr("osisRef");
}

function select_new_verse(osisRef) {
	d("select_new_verse('" + osisRef + '")');
	// XXX: Use OSISRefs?
	var reference_link = $('a.vnumber[osisRef="' + osisRef + '"]');
	var reference_found = reference_link.length > 0;

	if (reference_found)	{
		var current_verse = get_current_verse();
		current_verse.removeClass("currentverse");
		unhighlight_all();
		reference_link.addClass("currentverse");
		highlight_verse();
		toggle_filler(true);
		scroll_to_current();
	}

	return reference_found;
}

function get_current_verse_bounds() {
	var osisRef = get_current_verse_ref();
	var start = $('a[name="' + osisRef + '_start"]');
	var end = $('a[name="' + osisRef + '_end"]');
	return [start, end];
}

function get_selected_verse_ref() {
	var range = get_normalized_selection();
	if(!range) {
		var ref = get_current_verse_ref();
		return [ref, ref];
	}
	
	var last = null;
	var start = pick_element("a[name$=_start]", range, true);
	var end = pick_element("a[name$=_end]", range, false);
	
	return [start.getAttribute("osisRef"), end.getAttribute("osisRef")];
}

$('body').bind("mouseup", function() {
	d('up\n');
	var [start, end] = get_selected_verse_ref();
	d(start + ' --- ' + end);
});

