function get_start_point(){
	return $("#original_segment");
}

function get_scroll_point() {
	return {top: 0, left: window.innerWidth/2}
}

function select_new_segment(ref_id) {
	d("select_new_segment('" + ref_id + '")');
	var reference_link = $('div.segment[ref_id="' + ref_id + '"]');
	var reference_found = reference_link.length > 0;

	if (reference_found)	{
		toggle_filler(true);
		scroll_to_current(reference_link);
	}

	return reference_found;
}

var last_segment_shown = null;
function update_current_segment_shown() {
	var current_segment = find_current_segment();
	var current_segment_ref = '';
	if (current_segment)	{
		current_segment_ref = current_segment.children('.segment').attr('ref_id');
	}
	if (!current_segment || current_segment_ref == last_segment_shown) {
		return;
	}

	last_segment_shown = current_segment_ref;
	var event = document.createEvent("Event");
	event.initEvent('ChangeSegment', true, true);
	document.body.dispatchEvent(event);
}

$(document).ready(function()	{
	$(window).scroll(function() {update_current_segment_shown()});
	$(window).resize(function() {update_current_segment_shown()});
});
