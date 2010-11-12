/* Highlighting utilities */
function extract_range(r, tag) {
	/* pull out a range and replace with a span. 
	 * Note: the way we use this can end up with (for example) <span>'s
	 * being the parents of <div>'s. I'm not sure if this is strictly legal...
	 */
	if(!r.collapsed) {
		var newNode = document.createElement("span");
		newNode.className = "highlight had_highlight";
		if (tag) {
			newNode.setAttribute(tag[0], tag[1]);
		}
		r.surroundContents(newNode);
		return true;
	}
	return false;
}

function highlight_range(start, end, tag) {
	var range = document.createRange();
	range.setStartAfter(start);
	range.setEndBefore(end);
	var common_parent = range.commonAncestorContainer;
	var r = document.createRange();
	
	// We need to travel up from our start point, collecting all to the 
	// right of our start node.
	var s = start;
	while (s.parentNode != common_parent) {
		r.selectNodeContents(s.parentNode);
		//d("Left hand side");
		//d(s);
		r.setStartAfter(s);
		extract_range(r, tag);
		s = s.parentNode;
	}
	
	/* This controls whether on our next level up, we include after this
	 * rather than just before. If our parent is an indentedline, and we are
	 * its last child, we want all of it to be included, otherwise the last
	 * selected line looks wrong in poetry - it is short and on its own.
	 * Note that we have to be careful with this - ESV Acts 15:18 starts in the
	 * middle of a line of poetry... (thus the last child check)
	 */
	var try_indented = false;
	var e = end;
	// Now, we need to travel up from our end point, collecting everything to
	// the left of our start node.
	/* Note: if we are doing an indentedline, we want *all* of it */
	while (e.parentNode != common_parent) {
		r.selectNodeContents(e.parentNode);
		//d("Right hand side");
		//d(e);
		r.setEndBefore(e);
		var set_end_after = false;
		if(e.className.match(/\bindentedline\b/))
		{
			// If we were in
			r.setEndAfter(e);
			set_end_after = true;
		}
			
		var try_this_indented = try_indented;
		try_indented = (e.parentNode.className.match(/\bindentedline\b/) 
			&& e == e.parentNode.lastChild) 

		if(extract_range(r, tag) && try_this_indented) {
			//d("Moving up a level");
			// We just put in another level in extract_range - we don't want
			// to do it again - infinite loops result...
			e = e.parentNode;
		}

		e = e.parentNode;
	}

	/* and now we need to get the part at the top of our range, between the
	 * two topmost points */
	//d("Both");
	//d(s);
	//d(e);
	
	r.setStartAfter(s);
	r.setEndBefore(e);
	if(try_indented) {
		r.setEndAfter(e);
	}
	
	extract_range(r, tag);
}

// XXX: We ought to be able to just unhighlight a single range.
// Until I figure that out, unhighlight_all will probably do just fine.
function unhighlight_all()	{
	$('span.highlight').removeClass('highlight');
}
