/* Utility functions that can be used by all windows, including those only using SetPage(). */
function d(str) {
	dump("From JS: ");
	if (typeof console != "undefined" && console.log) console.log(str);
	if ((typeof str == "string" && !str.match(/\n$/)) || typeof str == "number")
		dump(str + "\n");
	else dump(str);
}

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

/*
 Strings which may contain unicode need to be encoded to UTF-8 so that they
 will be correctly converted to Unicode by wxWebConnect's ExecuteScriptWithResult().
*/
function encode_utf8(str)	{
	return unescape(encodeURIComponent(str));
}

function force_stylesheet_reload(stylesheet)	{
	// Add a unique parameter to prevent caching.
	var new_stylesheet = stylesheet + "?forceReload=true&time=" + (new Date().valueOf());
	$('link[href^="' + stylesheet + '"]').attr("href", new_stylesheet);
}

// Drag & Drop support.
$(document).ready(function()	{
	document.body.addEventListener("dragenter", checkDrag, true);
	document.body.addEventListener("dragover", checkDrag, true);
	document.body.addEventListener("dragdrop", onDrop, true);
});

function checkDrag(event)	{
	var hasFile = event.dataTransfer.types.contains('text/x-moz-url');
	// XXX: Does effectAllowed and dropEffect do anything?
	event.dataTransfer.effectAllowed = (hasFile ? 'link': 'none');
	event.dataTransfer.dropEffect = (hasFile ? 'link': 'none');
	return hasFile;
}

var dropped_file_urls = null;

function onDrop(event) {
	event.stopPropagation();
	event.preventDefault();
	var dataTransfer = event.dataTransfer;
	var count = dataTransfer.mozItemCount;
	dropped_file_urls = [];
	for (var index = 0; index < count; index++)	{
		try	{
			var fileURL = dataTransfer.mozGetDataAt('text/x-moz-url', index);
			if (fileURL.indexOf('file:') == 0)	{
				dropped_file_urls.push(fileURL);
			}
		} catch(ex)	{
			// Do nothing.
		}
	}
	
	if (dropped_file_urls.length == 0) {
		return false;
	}

	var event = document.createEvent("Event");
	event.initEvent('DropFiles', true, true);
	document.body.dispatchEvent(event);
}

// Try and find the word under the mouse cursor if the user right clicks.
// This is used to decide what to offer to search for as the selected word.
$(document).mousedown(function(event) {
	if (event.which != 3) {
		return;
	}
	window.right_click_word = "";
	var rangeOffset = event.originalEvent.rangeOffset;
	var rangeParent = event.originalEvent.rangeParent;
	if (rangeParent.nodeType !== Node.TEXT_NODE) {
		return;
	}
	var range = document.createRange();
	var startOffset = rangeOffset;
	var endOffset = rangeOffset;
	range.setStart(rangeParent, rangeOffset);
	range.setEnd(rangeParent, rangeOffset);
	// XXX: Expand the list of whitespace.  This most definitely doesn't
	// handle word segmentation systems like Thai.
	var whitespace = " \t\".,";
	for (startOffset = rangeOffset - 1; startOffset > 0; startOffset--)	{
		range.setStart(rangeParent, startOffset);
		range.setEnd(rangeParent, startOffset + 1);
		if (whitespace.indexOf(range.toString()) > -1)	{
			startOffset++;
			break;
		}
	}
	startOffset = Math.max(startOffset, 0);

	for (endOffset = rangeOffset; endOffset < rangeParent.length; endOffset++)	{
		try {
			range.setStart(rangeParent, endOffset);
			range.setEnd(rangeParent, endOffset + 1);
		} catch (e)	{
			break;
		}

		if (whitespace.indexOf(range.toString()) > -1)	{
			break;
		}
	}
	range.setStart(rangeParent, startOffset);
	range.setEnd(rangeParent, endOffset);
	window.right_click_word = range.toString();
});

/*
When a display option is changed, change the attribute on the body.
These options are then used in the stylesheet.
*/
function change_display_option(option_name, option_value)	{
	document.body.setAttribute(option_name, option_value);

	// Changing whether different speakers are coloured will never resize the
	// page or change the display, so we don't want to try to scroll to the
	// current reference.
	var resize_page = (option_name !== "colour_speakers");

	// Technically, changing the display options does not actually resize the window.
	// However, since it can dramatically change the position of the elements on the page,
	// the effect is the same.
	if (resize_page && on_resize)	{
		on_resize();
	}
}
