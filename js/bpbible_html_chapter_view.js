function get_start_point(){
	return get_current_verse_bounds()[0];
}


function highlight_verse(){
	var [start, end] = get_current_verse_bounds();
	if (start[0]) {
		// Highlight the verse's background
		highlight_range(start[0], end[0]);
	}
}

function get_current_reference_range()	{
	var top = window.scrollY;
	var bottom = window.innerHeight + window.scrollY;

	// Don't use chapter numbers
	var start = $('a.vnumber');
	var end = $('a.vnumber');
	var ref1 = null, ref2 = null;
	/* TODO: we can narrow down based on our page segments first... */
	start.each(function() {
		if ($(this).offset().top + this.offsetHeight >= top) {
			ref1 = this.getAttribute("reference");
			return false;
		}
		return true;
	});

	var last = null;
	$(end).each(function() {
		//d($(this).offset().top);
		if ($(this).offset().top >= bottom) {
			if (!last) d("Not last");
			return false;
		}
		last = this;
		return true;
	});
	ref2 = last.getAttribute("reference");
	
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
	if (book1 == book2)
		if(chapter1 == chapter2 || !chapter2)
			whole2 = verse2;
		else
			whole2 = chapter2 + ":" + verse2;
	return whole1 + delim + whole2;
}

function fill_reference_bar() {
	$("div.reference_bar").text(get_current_reference_range());
}

function create_reference_bar() {
	$("body").prepend('<div class="reference_bar">This should give the current reference</div>');
}

$(document).ready(function() {
	highlight_verse();
	create_reference_bar();
	$(window).scroll(function() {fill_reference_bar()});
	$(window).resize(function() {fill_reference_bar()});
	fill_reference_bar();

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

function select_new_verse(reference) {
	d("select_new_verse('" + reference + '")');
	// XXX: Use OSISRefs?
	var reference_link = $('a.vnumber[reference="' + reference + '"]');
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

