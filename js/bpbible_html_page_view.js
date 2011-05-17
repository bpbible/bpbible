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
