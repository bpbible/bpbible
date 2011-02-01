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
