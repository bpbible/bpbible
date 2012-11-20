function hide_sub_strongs_popups() {
	$(".same-strongs-hint").removeClass("same-strongs-hint");
}

function show_sub_strongs_popups(elem) {
	href = elem.getAttribute("href");
	if (href == "strongs://Greek/3588") return;
	var links = elems = $('a.strongs_headword[href="' + href + '"]');
	var blocks = links.parents(".strongs-block").addClass("same-strongs-hint");
}

function hide_strongs_popup() {
	$(".current-strongs-word").removeClass("current-strongs-word");
	$(".strongs-numbers-popup").remove();
	$(".strongs-word-popup").remove();
	hide_sub_strongs_popups();
}

function show_strongs_popup(elem) {
	hide_strongs_popup();
	var t = $(elem);
	t.addClass("current-strongs-word");

	var word_popup = $("<div class='strongs-word-popup'>" + t.find(".strongs_word").html() + "</div>").appendTo(t);
	var number_popup = $("<div class='strongs-numbers-popup'><span class='strongs'>" + t.find(".strongs").html() + "</span></div>").appendTo(t);
	var s = number_popup.find(".strongs");

	s.find("span.strongs_headwords > a.strongs_headword").each(function() {
		show_sub_strongs_popups(this);
	});

	// don't ask why 2. 3 is too wide (causes wrapping) but 2 doesn't.
	word_popup.width(trunc(t.width() + (word_popup.outerWidth() - word_popup.width())/2 - 1));
	var word_popup_offset = t.offset();
	word_popup_offset.left -= read_css(word_popup, "padding-left") + read_css(word_popup, "border-left-width");
	word_popup_offset.top -= read_css(word_popup, "padding-top") + read_css(word_popup, "border-top-width");

	word_popup.offset(word_popup_offset);
	word_popup.width(trunc(word_popup.width()));

	var number_popup_offset = t.offset();
	number_popup_offset.left -= read_css(number_popup, "padding-left") + read_css(number_popup, "border-left-width");
	number_popup_offset.top -= read_css(number_popup, "padding-top");

	// Don't ask why 1. Without a little offset it looks very padded.
	number_popup_offset.top = word_popup_offset.top + word_popup.outerHeight() - 1;

	number_popup.offset(number_popup_offset);
	var diff = (number_popup.width() - word_popup.width());
	if (s.width() < word_popup.width()) {
		number_popup.width(word_popup.width());
	} else if (number_popup.width() > word_popup.width()) {
		number_popup.addClass("extra-long");
		if (diff < 10) {
			number_popup.width(trunc(word_popup.width() + 10));
		}

		number_popup_offset.left -= trunc((number_popup.width() - word_popup.width()) / 2);

		// since we have a top border, we'll need to move it up by that much
		number_popup_offset.top -= read_css(number_popup, "border-top-width");
		number_popup.offset(number_popup_offset);
		var filler = $("<div class='strongs-number-top-filler'></div>").appendTo(number_popup);
		filler.width(word_popup.outerWidth());
		var o = word_popup.offset();
		o.top = number_popup_offset.top;
		filler.offset(o);
	}
}

function on_strongs_click(event) {
	var target = $(event.target);
	if (!target.is(".strongs-block")) {
		target = target.parents(".strongs-block");
	}

	if (target.is(".strongs-block")) {
		show_strongs_popup(target[0]);
	} else {
		hide_strongs_popup();
	}
}

function on_strongs_over(event) {
	show_strongs_popup(this);
}

function on_strongs_off(event) {
	hide_strongs_popup();
}

function on_sub_strongs_over(event) {
	$(this).children("span.strongs").children("span.strongs_headwords").children("a.strongs_headword").each(function() {
		show_sub_strongs_popups(this);
	});
}

function on_sub_strongs_off(event) {
	hide_sub_strongs_popups();
}

function relayout_strongs() {
	var curr = $(".current-strongs-word");
	if (curr.length) {
		show_strongs_popup(curr[0]);
	}
}

function set_strongs_method() {
	$("body").undelegate(".strongs-block", "mouseenter", on_strongs_over);
	$("body").undelegate(".strongs-block", "mouseleave", on_strongs_off);
	$("body").unbind("click", on_strongs_click);
	$("body").delegate('span.strongs-block', "mouseenter", on_sub_strongs_over);
	$("body").delegate('span.strongs-block', "mouseleave", on_sub_strongs_off);

	hide_strongs_popup();
	strongs_method = document.body.getAttribute("strongs_position");
	
	if (strongs_method == "click") {
		$("body").bind("click", on_strongs_click);
	} else if (strongs_method == "hover") {
		$("body").delegate(".strongs-block", "mouseenter", on_strongs_over);
		$("body").delegate(".strongs-block", "mouseleave", on_strongs_off);
	}

	if (strongs_method == "underneath" || strongs_method == "inline") {
		$("body").delegate('span.strongs-block', "mouseenter", on_sub_strongs_over);
		$("body").delegate('span.strongs-block', "mouseleave", on_sub_strongs_off);
	}
}

$(document).ready(function() {
	set_strongs_method();
	$("body").bind("DOMAttrModified", function(event) {
		if(event.attrName == "strongs_position") {
			set_strongs_method();
		}
	});

	$(window).resize(relayout_strongs);
});
