/*!
 *  Hyphenator 2.X.X - client side hyphenation for webbrowsers
 *  Copyright (C) 2009  Mathias Nater, Zürich (mathias at mnn dot ch)
 *  Project and Source hosted on http://code.google.com/p/hyphenator/
 * 
 *  This JavaScript code is free software: you can redistribute
 *  it and/or modify it under the terms of the GNU Lesser
 *  General Public License (GNU LGPL) as published by the Free Software
 *  Foundation, either version 3 of the License, or (at your option)
 *  any later version.  The code is distributed WITHOUT ANY WARRANTY;
 *  without even the implied warranty of MERCHANTABILITY or FITNESS
 *  FOR A PARTICULAR PURPOSE.  See the GNU GPL for more details.
 *
 *  As additional permission under GNU GPL version 3 section 7, you
 *  may distribute non-source (e.g., minimized or compacted) forms of
 *  that code without the copy of the GNU GPL normally required by
 *  section 4, provided you include this license notice and a URL
 *  through which recipients can access the Corresponding Source.
 */
 
/* 
 *  Comments are jsdoctoolkit formatted. See jsdoctoolkit.org
 */
 
/* The following comment is for JSLint: */
/*global window, ActiveXObject, unescape */
/*jslint browser: true, eqeqeq: true, immed: true, newcap: true, nomen: true, onevar: true, undef: true, white: true, indent: 4*/

/**
 * @fileOverview
 * A script that does hyphenation in (X)HTML files
 * @author Mathias Nater, <a href = "mailto:mathias@mnn.ch">mathias@mnn.ch</a>
 * @version 2.X.X
  */

/**
 * @constructor
 * @description Provides all functionality to do hyphenation, except the patterns that are loaded
 * externally.
 * @namespace Holds all methods and properties
 * @example
 * &lt;script src = "Hyphenator.js" type = "text/javascript"&gt;&lt;/script&gt;
 * &lt;script type = "text/javascript"&gt;
 *   Hyphenator.run();
 * &lt;/script&gt;
 */
var Hyphenator = (function () {


	/**
	 * @name Hyphenator-languageHint
	 * @fieldOf Hyphenator
	 * @description
	 * A string to be displayed in a prompt if the language can't be guessed.
	 * If you add hyphenation patterns change this string.
	 * Internally, this string is used to define languages that are supported by Hyphenator.
	 * @see Hyphenator-supportedLang
	 * @type string
	 * @private
	 * @see Hyphenator-autoSetMainLanguage
	 */
	var languageHint = 'da, bn, de, en, es, fi, fr, gu, hi, hu, it, kn, ml, nl, or, pa, pl, pt, ru, sv, ta, te',

	/**
	 * @name Hyphenator-supportedLang
	 * @fieldOf Hyphenator
	 * @description
	 * A generated key-value object that stores supported languages.
	 * The languages are retrieved from {@link Hyphenator-languageHint}.
	 * @type object
	 * @private
	 * @example
	 * Check if language lang is supported:
	 * if (supportedLang[lang])
	 */
	supportedLang = (function () {
		var k, i = 0, a = languageHint.split(', '), r = {};
		while (!!(k = a[i++])) {
			r[k] = true;
		}
		return r;
	}()),

	/**
	 * @name Hyphenator-prompterStrings
	 * @fieldOf Hyphenator
	 * @description
	 * A key-value object holding the strings to be displayed if the language can't be guessed
	 * If you add hyphenation patterns change this string.
	 * @type object
	 * @private
	 * @see Hyphenator-autoSetMainLanguage
	 */	
	prompterStrings = {
		'da': 'Denne websides sprog kunne ikke bestemmes. Angiv venligst sprog:',
		'de': 'Die Sprache dieser Webseite konnte nicht automatisch bestimmt werden. Bitte Sprache angeben:',
		'en': 'The language of this website could not be determined automatically. Please indicate main language:',
		'es': 'El idioma del sitio no pudo determinarse autom%E1ticamente. Por favor, indique el idioma principal:',
		'fi': 'Sivun kielt%E4 ei tunnistettu automaattisesti. M%E4%E4rit%E4 sivun p%E4%E4kieli:',
		'fr': 'La langue de ce site n%u2019a pas pu %EAtre d%E9termin%E9e automatiquement. Veuillez indiquer une langue, s.v.p.%A0:',
		'hu': 'A weboldal nyelvét nem sikerült automatikusan megállapítani. Kérem adja meg a nyelvet:',
		'it': 'Lingua del sito sconosciuta. Indicare una lingua, per favore:',
		'ml': 'ഈ വെ%u0D2C%u0D4D%u200Cസൈറ്റിന്റെ ഭാഷ കണ്ടുപിടിയ്ക്കാ%u0D28%u0D4D%u200D കഴിഞ്ഞില്ല. ഭാഷ ഏതാണെന്നു തിരഞ്ഞെടുക്കുക:',
		'nl': 'De taal van deze website kan niet automatisch worden bepaald. Geef de hoofdtaal op:',
		'pt': 'A língua deste site não pôde ser determinada automaticamente. Por favor indique a língua principal:',
		'ru': 'Язык этого сайта не может быть определен автоматически. Пожалуйста укажите язык:',
		'sv': 'Spr%E5ket p%E5 den h%E4r webbplatsen kunde inte avg%F6ras automatiskt. V%E4nligen ange:'
	},
	
	/**
	 * @name Hyphenator-basePath
	 * @fieldOf Hyphenator
	 * @description
 	 * A string storing the basepath from where Hyphenator.js was loaded.
	 * This is used to load the patternfiles.
	 * The basepath is determined dynamically by searching all script-tags for Hyphenator.js
	 * If the path cannot be determined http://hyphenator.googlecode.com/svn/trunk/ is used as fallback.
	 * @type string
	 * @private
	 * @see Hyphenator-loadPatterns
	 */
	basePath = (function () {
		var s = document.getElementsByTagName('script'), i = 0, p, src, t;
		while (!!(t = s[i++])) {
			if (!t.src) {
				continue;
			}
			src = t.src;
			p = src.indexOf('Hyphenator.js');
			if (p !== -1) {
				return src.substring(0, p);
			}
		}
		return 'http://hyphenator.googlecode.com/svn/trunk/';
	}()),

	/**
	 * @name Hyphenator-isLocal
	 * @fieldOf Hyphenator
	 * @description
	 * isLocal is true, if Hyphenator is loaded from the same domain, as the webpage, but false, if
	 * it's loaded from an external source (i.e. directly from google.code)
	 */
	isLocal = (function () {
		var re = false;
		if (basePath.indexOf(window.location.hostname) !== -1) {
			re = true;
		}
		return re;
	}()),
	
	/**
	 * @name Hyphenator-documentLoaded
	 * @fieldOf Hyphenator
	 * @description
	 * documentLoaded is true, when the DOM has been loaded. This is set by runOnContentLoaded
	 */
	documentLoaded = false,
	
	/**
	 * @name Hyphenator-dontHyphenate
	 * @fieldOf Hyphenator
	 * @description
	 * A key-value object containing all html-tags whose content should not be hyphenated
	 * @type object
	 * @private
	 * @see Hyphenator-hyphenateElement
	 */
	dontHyphenate = {'script': true, 'code': true, 'pre': true, 'img': true, 'br': true, 'samp': true, 'kbd': true, 'var': true, 'abbr': true, 'acronym': true, 'sub': true, 'sup': true, 'button': true, 'option': true, 'label': true, 'textarea': true},

	/**
	 * @name Hyphenator-enableCache
	 * @fieldOf Hyphenator
	 * @description
	 * A variable to set if caching is enabled or not
	 * @type boolean
	 * @default true
	 * @private
	 * @see Hyphenator.config
	 * @see hyphenateWord
	 */
	enableCache = true,
	
	/**
	 * @name Hyphenator-enableRemoteLoading
	 * @fieldOf Hyphenator
	 * @description
	 * A variable to set if pattern files should be loaded remotely or not
	 * @type boolean
	 * @default true
	 * @private
	 * @see Hyphenator.config
	 * @see Hyphenator-loadPatterns
	 */
	enableRemoteLoading = true,
	
	/**
	 * @name Hyphenator-displayToggleBox
	 * @fieldOf Hyphenator
	 * @description
	 * A variable to set if the togglebox should be displayed or not
	 * @type boolean
	 * @default false
	 * @private
	 * @see Hyphenator.config
	 * @see Hyphenator-toggleBox
	 */
	displayToggleBox = false,
	
	/**
	 * @name Hyphenator-hyphenateClass
	 * @fieldOf Hyphenator
	 * @description
	 * A string containing the css-class-name for the hyphenate class
	 * @type string
	 * @default 'hyphenate'
	 * @private
	 * @example
	 * &lt;p class = "hyphenate"&gt;Text&lt;/p&gt;
	 * @see Hyphenator.config
	 */
	hyphenateClass = 'hyphenate',

	/**
	 * @name Hyphenator-dontHyphenateClass
	 * @fieldOf Hyphenator
	 * @description
	 * A string containing the css-class-name for elements that should not be hyphenated
	 * @type string
	 * @default 'donthyphenate'
	 * @private
	 * @example
	 * &lt;p class = "donthyphenate"&gt;Text&lt;/p&gt;
	 * @see Hyphenator.config
	 */
	dontHyphenateClass = 'donthyphenate',
	
	/**
	 * @name Hyphenator-min
	 * @fieldOf Hyphenator
	 * @description
	 * A number wich indicates the minimal length of words to hyphenate.
	 * @type number
	 * @default 6
	 * @private
	 * @see Hyphenator.config
	 */	
	min = 6,
	
	/**
	 * @name Hyphenator-isBookmarklet
	 * @fieldOf Hyphenator
	 * @description
	 * Indicates if Hyphanetor runs as bookmarklet or not.
	 * @type boolean
	 * @default false
	 * @private
	 */	
	isBookmarklet = (function () {
		var loc = null, re = false, jsArray = document.getElementsByTagName('script'), i, l;
		for (i = 0, l = jsArray.length; i < l; i++) {
			if (!!jsArray[i].getAttribute('src')) {
				loc = jsArray[i].getAttribute('src');
			}
			if (!loc) {
				continue;
			} else if (loc.indexOf('Hyphenator.js?bm=true') !== -1) {
				re = true;
			}
		}
		return re;
	}()),

	/**
	 * @name Hyphenator-mainLanguage
	 * @fieldOf Hyphenator
	 * @description
	 * The general language of the document
	 * @type number
	 * @private
	 * @see Hyphenator-autoSetMainLanguage
	 */	
	mainLanguage = null,

	/**
	 * @name Hyphenator-elements
	 * @fieldOf Hyphenator
	 * @description
	 * An array holding all elements that have to be hyphenated. This var is filled by
	 * {@link Hyphenator-gatherDocumentInfos}
	 * @type array
	 * @private
	 */	
	elements = [],
	
	/**
	 * @name Hyphenator-exceptions
	 * @fieldOf Hyphenator
	 * @description
	 * An object containing exceptions as comma separated strings for each language.
	 * When the language-objects are loaded, their exceptions are processed, copied here and then deleted.
	 * @see Hyphenator-prepareLanguagesObj
	 * @type object
	 * @private
	 */	
	exceptions = {},

	/**
	 * @name Hyphenator-docLanguages
	 * @fieldOf Hyphenator
	 * @description
	 * An object holding all languages used in the document. This is filled by
	 * {@link Hyphenator-gatherDocumentInfos}
	 * @type object
	 * @private
	 */	
	docLanguages = {},


	/**
	 * @name Hyphenator-state
	 * @fieldOf Hyphenator
	 * @description
	 * A number that inidcates the current state of the script
	 * 0: not initialized
	 * 1: loading patterns
	 * 2: ready
	 * 3: hyphenation done
	 * 4: hyphenation removed
	 * @type number
	 * @private
	 */	
	state = 0,

	/**
	 * @name Hyphenator-url
	 * @fieldOf Hyphenator
	 * @description
	 * A string containing a RegularExpression to match URL's
	 * @type string
	 * @private
	 */	
	url = '(\\w*:\/\/)((\\w*:)?(\\w*)@)?([\\w\\.]*)?(:\\d*)?(\/[\\w#!:\\.?\\+=&%@!\\-]*)*',

	/**
	 * @name Hyphenator-mail
	 * @fieldOf Hyphenator
	 * @description
	 * A string containing a RegularExpression to match mail-adresses
	 * @type string
	 * @private
	 */	
	mail = '[\\w-\\.]+@[\\w\\.]+',

	/**
	 * @name Hyphenator-urlRE
	 * @fieldOf Hyphenator
	 * @description
	 * A RegularExpressions-Object for url- and mail adress matching
	 * @type object
	 * @private
	 */		
	urlOrMailRE = new RegExp('(' + url + ')|(' + mail + ')', 'i'),

	/**
	 * @name Hyphenator-zeroWidthSpace
	 * @fieldOf Hyphenator
	 * @description
	 * A string that holds a char.
	 * Depending on the browser, this is the zero with space or an empty string.
	 * The zeroWidthSpace is inserted after a '-' in compound words, so even FF and IE
	 * will break after a '-' if necessary.
	 * zeroWidthSpace is also used to break URLs
	 * @type string
	 * @private
	 */		
	zeroWidthSpace = (function () {
		var zws, ua = navigator.userAgent.toLowerCase();
		if (ua.indexOf('msie 6') === -1) {
			zws = String.fromCharCode(8203); //Unicode zero width space
		} else {
			zws = ''; //IE6 doesn't support zws
		}
		return zws;
	}()),
	
	/**
	 * @name Hyphenator-onHyphenationDone
	 * @fieldOf Hyphenator
	 * @description
	 * A method to be called, when the last element has been hyphenated or the hyphenation has been
	 * removed from the last element.
	 * @see Hyphenator.config
	 * @type function
	 * @private
	 */		
	onHyphenationDone = function () {},

	/**
	 * @name Hyphenator-onError
	 * @fieldOf Hyphenator
	 * @description
	 * A function that can be called upon an error.
	 * @see Hyphenator.config
	 * @type function
	 * @private
	 */		
	onError = function (e) {
		alert("Hyphenator.js says:\n\nAn Error ocurred:\n" + e.message);
	},

	/**
	 * @name Hyphenator-selectorFunction
	 * @fieldOf Hyphenator
	 * @description
	 * A function that has to return a HTMLNodeList of Elements to be hyphenated.
	 * By default it uses the classname ('hyphenate') to select the elements.
	 * @see Hyphenator.config
	 * @type function
	 * @private
	 */		
	selectorFunction = function () {
		var tmp, el = [], i, l;
		if (document.getElementsByClassName) {
			el = document.getElementsByClassName(hyphenateClass);
		} else {
			tmp = document.getElementsByTagName('*');
			l = tmp.length;
			for (i = 0; i < l; i++)
			{
				if (tmp[i].className.indexOf(hyphenateClass) !== -1 && tmp[i].className.indexOf(dontHyphenateClass) === -1) {
					el.push(tmp[i]);
				}
			}
		}
		return el;
	},

	/**
	 * @name Hyphenator-intermediateState
	 * @fieldOf Hyphenator
	 * @description
	 * The value of style.visibility of the text while it is hyphenated.
	 * @see Hyphenator.config
	 * @type string
	 * @private
	 */		
	intermediateState = 'hidden',
	
	/**
	 * @name Hyphenator-hyphen
	 * @fieldOf Hyphenator
	 * @description
	 * A string containing the character for in-word-hyphenation
	 * @type string
	 * @default the soft hyphen
	 * @private
	 * @see Hyphenator.config
	 */
	hyphen = String.fromCharCode(173),
	
	/**
	 * @name Hyphenator-urlhyphen
	 * @fieldOf Hyphenator
	 * @description
	 * A string containing the character for url/mail-hyphenation
	 * @type string
	 * @default the zero width space
	 * @private
	 * @see Hyphenator.config
	 * @see Hyphenator-zeroWidthSpace
	 */
	urlhyphen = zeroWidthSpace,
	
	/**
	 * @name Hyphenator-Expando
	 * @methodOf Hyphenator
	 * @description
	 * This custom object stores data for elements: storing data directly in elements
	 * (DomElement.customData = foobar;) isn't a good idea. It would lead to conflicts
	 * in form elements, when the form has a child with name="foobar". Therefore, this
	 * solution follows the approach of jQuery: the data is stored in an object and
	 * referenced by a unique attribute of the element. The attribute has a name that 
	 * is built by the prefix "HyphenatorExpando_" and a random number, so if the very
	 * very rare case occurs, that there's already an attribute with the same name, a
	 * simple reload is enough to make it function.
	 * @private
	 */		
	Expando = (function () {
		var container = {},
			name = "HyphenatorExpando_" + Math.random(),
			uuid = 0;
		return {
			getDataForElem : function (elem) {
				return container[elem[name]];
			},
			setDataForElem : function (elem, data) {
				var id;
				if (elem[name] && elem[name] !== '') {
					id = elem[name];
				} else {
					id = uuid++;
					elem[name] = id;
				}
				container[id] = data;
			},
			appendDataForElem : function (elem, data) {
				var k;
				for (k in data) {
					if (data.hasOwnProperty(k)) {
						container[elem[name]][k] = data[k];
					}
				}
			},
			delDataOfElem : function (elem) {
				delete container[elem[name]];
			}
		};
	}()),
		
	/*
	 * ContentLoaded.js
	 *
	 * Author: Diego Perini (diego.perini at gmail.com)
	 * Summary: Cross-browser wrapper for DOMContentLoaded
	 * Updated: 17/05/2008
	 * License: MIT
	 * Version: 1.1
	 *
	 * URL:
	 * http://javascript.nwbox.com/ContentLoaded/
	 * http://javascript.nwbox.com/ContentLoaded/MIT-LICENSE
	 *
	 * Notes:
	 * based on code by Dean Edwards and John Resig
	 * http://dean.edwards.name/weblog/2006/06/again/
	 */
	// @w	window reference
	// @f	function reference
	//function ContentLoaded(w, f) {
	/**
	 * @name Hyphenator-runOnContentLoaded
	 * @methodOf Hyphenator
	 * @description
	 * A crossbrowser solution for the DOMContentLoaded-Event
	 * @author Diego Perini (diego.perini at gmail.com)
	 * <a href = "http://javascript.nwbox.com/ContentLoaded/">http://javascript.nwbox.com/ContentLoaded/</a>
	 * @param object the window-object
	 * @param function-object the function to call onDOMContentLoaded
	 * @private
 	 */		
	runOnContentLoaded = function (w, f) {
		var	d = w.document,
			D = 'DOMContentLoaded',
			// user agent, version
			u = w.navigator.userAgent.toLowerCase(),
			v = parseFloat(u.match(/.+(?:rv|it|ml|ra|ie)[\/: ]([\d.]+)/)[1]),
			oldonload = w.onload;
				
		function init(e) {
			if (!documentLoaded) {
				documentLoaded = true;
				// pass a fake event if needed
				f((e.type && e.type === D) ? e : {
					type: D,
					target: d,
					eventPhase: 0,
					currentTarget: d,
					timeStamp: new Date().getTime(),
					eventType: e.type || e
				});
			}
		}
	
		// safari < 525.13
		if (/webkit\//.test(u) && v < 525.13) {
	
			(function () {
				if (/complete|loaded/.test(d.readyState)) {
					init('khtml-poll');
				} else {
					setTimeout(arguments.callee, 10);
				}
			}());
	
		// internet explorer all versions
		} else if (/msie/.test(u) && !w.opera) {
	
			d.attachEvent('onreadystatechange',
				function (e) {
					if (d.readyState === 'complete') {
						d.detachEvent('on' + e.type, arguments.callee);
						init(e);
					}
				}
			);
			if (w.self === top) {
				(function () {
					try {
						d.documentElement.doScroll('left');
					} catch (e) {
						setTimeout(arguments.callee, 10);
						return;
					}
					init('msie-poll');
				}());
			}
	
		// browsers having native DOMContentLoaded
		} else if (d.addEventListener &&
			(/opera\//.test(u) && v > 9) ||
			(/gecko\//.test(u) && v >= 1.8) ||
			(/khtml\//.test(u) && v >= 4.0) ||
			(/webkit\//.test(u) && v >= 525.13)) {
	
			d.addEventListener(D,
				function (e) {
					d.removeEventListener(D, arguments.callee, false);
					init(e);
				}, false
			);
	
		// fallback to last resort for older browsers
		} else {
	
			// from Simon Willison
			/**
			 * @ignore
			 */
			w.onload = function (e) {
				init(e || w.event);
				if (typeof oldonload === 'function') {
					oldonload(e || w.event);
				}
			};
	
		}
	},
	/* end ContentLoaded.js */

	/**
	 * @name Hyphenator-getLang
	 * @methodOf Hyphenator
	 * @description
	 * Gets the language of an element. If no language is set, it may use the {@link Hyphenator-mainLanguage}.
	 * @param object The first parameter is an DOM-Element-Object
	 * @param boolean The second parameter is a boolean to tell if the function should return the {@link Hyphenator-mainLanguage}
	 * if there's no language found for the element.
	 * @private
	 */
	getLang = function (el, fallback) {
		if (!!el.getAttribute('lang')) {
			return el.getAttribute('lang').substring(0, 2).toLowerCase();
		}
		// The following doesn't work in IE due to a bug when getAttribute('xml:lang') in a table
		/*if (!!el.getAttribute('xml:lang')) {
			return el.getAttribute('xml:lang').substring(0, 2);
		}*/
		//instead, we have to do this (thanks to borgzor):
		try {
			if (!!el.getAttribute('xml:lang')) {
				return el.getAttribute('xml:lang').substring(0, 2).toLowerCase();
			}
		} catch (ex) {}
		if (el.tagName !== 'HTML') {
			return getLang(el.parentNode, true);
		}
		if (fallback) {
			return mainLanguage;
		}
		return null;
	},
	
	/**
	 * @name Hyphenator-autoSetMainLanguage
	 * @methodOf Hyphenator
	 * @description
	 * Retrieves the language of the document from the DOM.
	 * The function looks in the following places:
	 * <ul>
	 * <li>lang-attribute in the html-tag</li>
	 * <li>&lt;meta http-equiv = "content-language" content = "xy" /&gt;</li>
	 * <li>&lt;meta name = "DC.Language" content = "xy" /&gt;</li>
	 * <li>&lt;meta name = "language" content = "xy" /&gt;</li>
	 * </li>
	 * If nothing can be found a prompt using {@link Hyphenator-languageHint} and {@link Hyphenator-prompterStrings} is displayed.
	 * If the retrieved language is in the object {@link Hyphenator-supportedLang} it is copied to {@link Hyphenator-mainLanguage}
	 * @private
	 */		
	autoSetMainLanguage = function () {
		var el = document.getElementsByTagName('html')[0],
			m = document.getElementsByTagName('meta'),
			i, text, lang, e, ul;
		mainLanguage = getLang(el);
		if (!mainLanguage) {
			for (i = 0; i < m.length; i++) {
				//<meta http-equiv = "content-language" content="xy">	
				if (!!m[i].getAttribute('http-equiv') && (m[i].getAttribute('http-equiv') === 'content-language')) {
					mainLanguage = m[i].getAttribute('content').substring(0, 2).toLowerCase();
				}
				//<meta name = "DC.Language" content="xy">
				if (!!m[i].getAttribute('name') && (m[i].getAttribute('name') === 'DC.language')) {
					mainLanguage = m[i].getAttribute('content').substring(0, 2).toLowerCase();
				}			
				//<meta name = "language" content = "xy">
				if (!!m[i].getAttribute('name') && (m[i].getAttribute('name') === 'language')) {
					mainLanguage = m[i].getAttribute('content').substring(0, 2).toLowerCase();
				}
			}
		}
		if (!mainLanguage) {
			text = '';
			ul = navigator.language ? navigator.language : navigator.userLanguage;
			ul = ul.substring(0, 2);
			if (prompterStrings.hasOwnProperty(ul)) {
				text = prompterStrings[ul];
			} else {
				text = prompterStrings.en;
			}
			text += ' (ISO 639-1)\n\n' + languageHint;
			lang = window.prompt(unescape(text), ul).toLowerCase();
			if (supportedLang[lang]) {
				mainLanguage = lang;
			} else {
				e = new Error('The language "' + lang + '" is not yet supported.');
				throw e;
			}
		}
	},
    
	/**
	 * @name Hyphenator-gatherDocumentInfos
	 * @methodOf Hyphenator
	 * @description
	 * This method runs through the DOM and executes the process()-function on:
	 * - every node returned by the {@link Hyphenator-selectorFunction}.
	 * The process()-function copies the element to the elements-variable, sets its visibility
	 * to intermediateState, retrieves its language and recursivly descends the DOM-tree until
	 * the child-Nodes aren't of type 1
	 * @private
	 */		
	gatherDocumentInfos = function () {
		var elToProcess, tmp, i = 0,
			process = function (el, hide, lang) {
			var n, i = 0, hyphenatorSettings = {};
			if (hide && intermediateState === 'hidden') {
				if (!!el.getAttribute('style')) {
					hyphenatorSettings.hasOwnStyle = true;
				} else {
					hyphenatorSettings.hasOwnStyle = false;					
				}
				hyphenatorSettings.isHidden = true;
				el.style.visibility = 'hidden';
			}
			if (el.lang) {
				hyphenatorSettings.language = el.lang.toLowerCase(); //copy attribute-lang to internal lang
			} else if (lang) {
				hyphenatorSettings.language = lang.toLowerCase();
			} else {
				hyphenatorSettings.language = getLang(el, true);
			}
			lang = hyphenatorSettings.language;
			if (supportedLang[lang]) {
				docLanguages[lang] = true;
			} else {
				onError(new Error('Language ' + lang + ' is not yet supported.'));
			}
			Expando.setDataForElem(el, hyphenatorSettings);
			elements.push(el);
			while (!!(n = el.childNodes[i++])) {
				if (n.nodeType === 1 && !dontHyphenate[n.nodeName.toLowerCase()] &&
					n.className.indexOf(dontHyphenateClass) === -1 && !(n in elToProcess)) {
					process(n, false, lang);
				}
			}
		};
		if (Hyphenator.isBookmarklet()) {
			elToProcess = document.getElementsByTagName('body')[0];
			process(elToProcess, false, mainLanguage);
		} else {
			elToProcess = selectorFunction();
			while (!!(tmp = elToProcess[i++]))
			{
				process(tmp, true);
			}			
		}
		if (!Hyphenator.languages.hasOwnProperty(mainLanguage)) {
			docLanguages[mainLanguage] = true;
		} else if (!Hyphenator.languages[mainLanguage].prepared) {
			docLanguages[mainLanguage] = true;
		}
		if (elements.length > 0) {
			Expando.appendDataForElem(elements[elements.length - 1], {isLast : true});
		}
	},
	
	/*
	registerOnCopy = function () {
			document.getElementsByTagName('body')[0].oncopy = function (e) {
				var text, h;
				if (window.getSelection) {
					text = window.getSelection().toString();
				}
				else if (document.selection) { // should come last; Opera!
					text = document.selection.createRange().text;
				}
				switch (hyphen) {
					case '|':
						h = '\\|';
						break;
					case '+':
						h = '\\+';
						break;
					case '*':
						h = '\\*';
						break;
					case String.fromCharCode(173):
						h = '\u00AD';
						break;
					default:
						h = hyphen;
					}
				text = text.replace(new RegExp(h, 'g'), '');
				text = text.replace(new RegExp(zeroWidthSpace, 'g'), '');
				alert(text);
				if (!!e && !!e.clipboardData) { //Safari
					e.preventDefault();
					e.clipboardData.setData('text/plain', text);
				} else if (!!window.clipboardData) { // IE
					window.preventDefault();
					window.clipboardData.setData('Text', text);
				}
			}			
	},
	*/
	 
	/**
	 * @name Hyphenator-convertPatterns
	 * @methodOf Hyphenator
	 * @description
	 * Converts the patterns from string '_a6' to object '_a':'_a6'.
	 * The result is stored in the {@link Hyphenator-patterns}-object.
	 * @private
	 * @param string the language whose patterns shall be converted
	 */		
	convertPatterns = function (lang) {
		var plen, anfang, pats, pat, key, tmp = {};
		pats = Hyphenator.languages[lang].patterns;
		for (plen in pats) {
			if (pats.hasOwnProperty(plen)) {
				plen = parseInt(plen, 10);
				anfang = 0;
				while (!!(pat = pats[plen].substr(anfang, plen))) {
					key = pat.replace(/\d/g, '');
					tmp[key] = pat;
					anfang += plen;
				}
			}
		}
		Hyphenator.languages[lang].patterns = tmp;
		Hyphenator.languages[lang].patternsConverted = true;
	},

	/**
	 * @name Hyphenator-convertExceptionsToObject
	 * @methodOf Hyphenator
	 * @description
	 * Converts a list of comma seprated exceptions to an object:
	 * 'Fortran,Hy-phen-a-tion' -> {'Fortran':'Fortran','Hyphenation':'Hy-phen-a-tion'}
	 * @private
	 * @param string a comma separated string of exceptions (without spaces)
	 */		
	convertExceptionsToObject = function (exc) {
		var w = exc.split(', '),
			r = {},
			i, l, key;
		for (i = 0, l = w.length; i < l; i++) {
			key = w[i].replace(/-/g, '');
			if (!r.hasOwnProperty(key)) {
				r[key] = w[i];
			}
		}
		return r;
	},
	
	/**
	 * @name Hyphenator-loadPatterns
	 * @methodOf Hyphenator
	 * @description
	 * Adds a &lt;script&gt;-Tag to the DOM to load an externeal .js-file containing patterns and settings for the given language.
	 * If the iven language is not in the {@link Hyphenator-supportedLang}-Object it returns.
	 * One may ask why we are not using AJAX to load the patterns. The XMLHttpRequest-Object 
	 * has a same-origin-policy. This makes the isBookmarklet-functionality impossible.
	 * @param string The language to load the patterns for
	 * @private
	 * @see Hyphenator-basePath
	 */
	loadPatterns = function (lang) {
		var url, xhr, head, script;
		if (supportedLang[lang] && !Hyphenator.languages[lang]) {
	        url = basePath + 'patterns/' + lang + '.js';
		} else {
			return;
		}
		if (isLocal && !isBookmarklet) {
			//check if 'url' is available:
			xhr = null;
			if (typeof XMLHttpRequest !== 'undefined') {
				xhr = new XMLHttpRequest();
			}
			if (!xhr) {
				try {
					xhr  = new ActiveXObject("Msxml2.XMLHTTP");
				} catch (e) {
					xhr  = null;
				}
			}
			if (xhr) {
				xhr.open('HEAD', url, false);
				xhr.setRequestHeader('Cache-Control', 'no-cache');
				xhr.send(null);
				if (xhr.status === 404) {
					onError(new Error('Could not load\n' + url));
					delete docLanguages[lang];
					return;
				}
			}
		}
		if (document.createElement) {
			head = document.getElementsByTagName('head').item(0);
			script = document.createElement('script');
			script.src = url;
			script.type = 'text/javascript';
			head.appendChild(script);
		}
	},
	
	/**
	 * @name Hyphenator-prepareLanguagesObj
	 * @methodOf Hyphenator
	 * @description
	 * Adds a cache to each language and converts the exceptions-list to an object.
	 * @private
	 * @param string the language ob the lang-obj
	 */		
	prepareLanguagesObj = function (lang) {
		var lo = Hyphenator.languages[lang], wrd;
		if (!lo.prepared) {	
			if (enableCache) {
				lo.cache = {};
			}
			if (lo.hasOwnProperty('exceptions')) {
				Hyphenator.addExceptions(lang, lo.exceptions);
				delete lo.exceptions;
			}
			if (exceptions.hasOwnProperty('global')) {
				if (exceptions.hasOwnProperty(lang)) {
					exceptions[lang] += ', ' + exceptions.global;
				} else {
					exceptions[lang] = exceptions.global;
				}
			}
			if (exceptions.hasOwnProperty(lang)) {
				lo.exceptions = convertExceptionsToObject(exceptions[lang]);
				delete exceptions[lang];
			} else {
				lo.exceptions = {};
			}
			convertPatterns(lang);
			wrd = '[\\w' + lo.specialChars + '@' + String.fromCharCode(173) + '-]{' + min + ',}';
			lo.genRegExp = new RegExp('(' + url + ')|(' + mail + ')|(' + wrd + ')', 'gi');
			lo.prepared = true;
		}
	},
	
	/**
	 * @name Hyphenator-prepare
	 * @methodOf Hyphenator
	 * @description
	 * This funtion prepares the Hyphenator-Object: If RemoteLoading is turned off, it assumes
	 * that the patternfiles are loaded, all conversions are made and the callback is called.
	 * If RemoteLoading is on (default), it loads the pattern files and waits until they are loaded,
	 * by repeatedly checking Hyphenator.languages. If a patterfile is loaded the patterns are
	 * converted to their object style and the lang-object extended.
	 * Finally the callback is called.
	 * @param function-object callback to call, when all patterns are loaded
	 * @private
	 */
	prepare = function (callback) {
		var lang, docLangEmpty = true, interval;
		if (!enableRemoteLoading) {
			for (lang in Hyphenator.languages) {
				if (Hyphenator.languages.hasOwnProperty(lang)) {
					prepareLanguagesObj(lang);
				}
			}
			state = 2;
			callback();
			return;
		}
		// get all languages that are used and preload the patterns
		state = 1;
		for (lang in docLanguages) {
			if (docLanguages.hasOwnProperty(lang)) {
				loadPatterns(lang);
				docLangEmpty = false;
			}
		}
		if (docLangEmpty) {
			state = 2;
			callback();
			return;
		}
		// wait until they are loaded
		interval = window.setInterval(function () {
			var finishedLoading = false, lang;
			for (lang in docLanguages) {
				if (docLanguages.hasOwnProperty(lang)) {
					if (!Hyphenator.languages[lang]) {
						finishedLoading = false;
						break;
					} else {
						finishedLoading = true;
						delete docLanguages[lang];
						//do conversion while other patterns are loading:
						prepareLanguagesObj(lang);		
					}
				}
			}
			if (finishedLoading) {
				window.clearInterval(interval);
				state = 2;
				callback();
			}
		}, 100);
	},

	/**
	 * @name Hyphenator-switchToggleBox
	 * @methodOf Hyphenator
	 * @description
	 * Creates or hides the toggleBox: a small button to turn off/on hyphenation on a page.
	 * @param boolean true when hyphenation is on, false when it's off
	 * @see Hyphenator.config
	 * @private
	 */		
	toggleBox = function (s) {
		var myBox, bdy, myIdAttribute, myTextNode, myClassAttribute;
		if (!!(myBox = document.getElementById('HyphenatorToggleBox'))) {
			if (s) {
				myBox.firstChild.data = 'Hy-phe-na-ti-on';
			} else {
				myBox.firstChild.data = 'Hyphenation';
			}
		} else {
			bdy = document.getElementsByTagName('body')[0];
			myBox = document.createElement('div');
			myIdAttribute = document.createAttribute('id');
			myIdAttribute.nodeValue = 'HyphenatorToggleBox';
			myClassAttribute = document.createAttribute('class');
			myClassAttribute.nodeValue = dontHyphenateClass;
			myTextNode = document.createTextNode('Hy-phe-na-ti-on');
			myBox.appendChild(myTextNode);
			myBox.setAttributeNode(myIdAttribute);
			myBox.setAttributeNode(myClassAttribute);
			myBox.onclick =  Hyphenator.toggleHyphenation;
			myBox.style.position = 'fixed';
			myBox.style.top = '0px';
			myBox.style.right = '0px';
			myBox.style.margin = '0';
			myBox.style.backgroundColor = '#AAAAAA';
			myBox.style.color = '#FFFFFF';
			myBox.style.font = '6pt Arial';
			myBox.style.letterSpacing = '0.2em';
			myBox.style.padding = '3px';
			myBox.style.cursor = 'pointer';
			myBox.style.WebkitBorderBottomLeftRadius = '4px';
			myBox.style.MozBorderRadiusBottomleft = '4px';
			bdy.appendChild(myBox);
		}
	},

	/**
	 * @name Hyphenator-hyphenateWord
	 * @methodOf Hyphenator
	 * @description
	 * This function is the heart of Hyphenator.js. It returns a hyphenated word.
	 *
	 * If there's already a {@link Hyphenator-hypen} in the word, the word is returned as it is.
	 * If the word is in the exceptions list or in the cache, it is retrieved from it.
	 * If there's a '-' put a zeroWidthSpace after the '-' and hyphenate the parts.
	 * @param string The language of the word
	 * @param string The word
	 * @returns string The hyphenated word
	 * @public
	 */	
	hyphenateWord = function (lang, word) {
		var lo = Hyphenator.languages[lang],
			parts, i, l, w, wl, s, hypos, p, maxwins, win, pat = false, patk, patl, c, digits, z, numb3rs, n, inserted, hyphenatedword;
		if (word === '') {
			return '';
		}
		if (word.indexOf(hyphen) !== -1) {
			//word already contains shy; -> leave at it is!
			return word;
		}
		if (enableCache && lo.cache.hasOwnProperty(word)) { //the word is in the cache
			return lo.cache[word];
		}
		if (lo.exceptions.hasOwnProperty(word)) { //the word is in the exceptions list
			return lo.exceptions[word].replace(/-/g, hyphen);
		}
		if (word.indexOf('-') !== -1) {
			//word contains '-' -> put a zeroWidthSpace after it and hyphenate the parts separated with '-'
			parts = word.split('-');
			for (i = 0, l = parts.length; i < l; i++) {
				parts[i] = hyphenateWord(lang, parts[i]);
			}
			return parts.join('-' + zeroWidthSpace);
		}
		//finally the core hyphenation algorithm
		w = '_' + word + '_';
		wl = w.length;
		s = w.split('');
		w = w.toLowerCase();
		hypos = [];
		numb3rs = {'0': true, '1': true, '2': true, '3': true, '4': true, '5': true, '6': true, '7': true, '8': true, '9': true}; //check for member is faster then isFinite()
		n = wl - lo.shortestPattern;
		for (p = 0; p <= n; p++) {
			maxwins = Math.min((wl - p), lo.longestPattern);
			for (win = lo.shortestPattern; win <= maxwins; win++) {
				if (lo.patterns.hasOwnProperty(patk = w.substr(p, win))) {
					pat = lo.patterns[patk];
				} else {
					continue;
				}
				digits = 1;
				patl = pat.length;
				for (i = 0; i < patl; i++) {
					c = pat.charAt(i);
					if (numb3rs[c]) {
						if (i === 0) {
							z = p - 1;
							if (!hypos[z] || hypos[z] < c) {
								hypos[z] = c;
							}
						} else {
							z = p + i - digits;
							if (!hypos[z] || hypos[z] < c) {
								hypos[z] = c;
							}
						}
						digits++;								
					}
				}
			}
		}
		inserted = 0;
		for (i = lo.leftmin; i <= (word.length - lo.rightmin); i++) {
			if (!!(hypos[i] & 1)) {
				s.splice(i + inserted + 1, 0, hyphen);
				inserted++;
			}
		}
		hyphenatedword = s.slice(1, -1).join('');
		if (enableCache) {
			lo.cache[word] = hyphenatedword;
		}
		return hyphenatedword;
	},
		
	/**
	 * @name Hyphenator-hyphenateURL
	 * @methodOf Hyphenator
	 * @description
	 * Puts {@link Hyphenator-urlhyphen} after each no-alphanumeric char that my be in a URL.
	 * @param string URL to hyphenate
	 * @returns string the hyphenated URL
	 * @public
	 */
	hyphenateURL = function (url) {
		return url.replace(/([:\/\.\?#&_,;!@]+)/gi, '$&' + urlhyphen);
	},

	/**
	 * @name Hyphenator-hyphenateElement
	 * @methodOf Hyphenator
	 * @description
	 * Takes the content of the given element and - if there's text - replaces the words
	 * by hyphenated words. If there's another element, the function is called recursively.
	 * When all words are hyphenated, the visibility of the element is set to 'visible'.
	 * @param object The element to hyphenate
	 * @param string The language used in this element
	 * @public
	 */
	hyphenateElement = function (el) {
		var hyphenatorSettings = Expando.getDataForElem(el),
			lang = hyphenatorSettings.language, hyphenate, n, i;
		if (Hyphenator.languages.hasOwnProperty(lang)) {
			hyphenate = function (word) {
				if (urlOrMailRE.test(word)) {
					return hyphenateURL(word);
				} else {
					return hyphenateWord(lang, word);
				}
			};
			i = 0;
			while (!!(n = el.childNodes[i++])) {
				if (n.nodeType === 3 && n.data.length >= min) { //type 3 = #text -> hyphenate!
					n.data = n.data.replace(Hyphenator.languages[lang].genRegExp, hyphenate);
				}
			}
		}
		if (hyphenatorSettings.isHidden && intermediateState === 'hidden') {
			el.style.visibility = 'visible';
			if (!hyphenatorSettings.hasOwnStyle) {
				el.setAttribute('style', ''); // without this, removeAttribute doesn't work in Safari (thanks to molily)
				el.removeAttribute('style');
			} else {
				if (el.style.removeProperty) {
					el.style.removeProperty('visibility');
				} else if (el.style.removeAttribute) { // IE
					el.style.removeAttribute('visibility');
				}  
			}
		}
		if (hyphenatorSettings.isLast) {
			state = 3;
			onHyphenationDone();
		}
	},
	
	/**
	 * @name Hyphenator-removeHyphenationFromElement
	 * @methodOf Hyphenator
	 * @description
	 * Removes all hyphens from the element. If there are other elements, the function is
	 * called recursively.
	 * Removing hyphens is usefull if you like to copy text. Some browsers are buggy when the copy hyphenated texts.
	 * @param object The element where to remove hyphenation.
	 * @public
	 */
	removeHyphenationFromElement = function (el) {
		var h, i = 0, n;
		switch (hyphen) {
		case '|':
			h = '\\|';
			break;
		case '+':
			h = '\\+';
			break;
		case '*':
			h = '\\*';
			break;
		default:
			h = hyphen;
		}
		while (!!(n = el.childNodes[i++])) {
			if (n.nodeType === 3) {
				n.data = n.data.replace(new RegExp(h, 'g'), '');
				n.data = n.data.replace(new RegExp(zeroWidthSpace, 'g'), '');
			} else if (n.nodeType === 1) {
				removeHyphenationFromElement(n);
			}
		}
	},

	/**
	 * @name Hyphenator-hyphenateDocument
	 * @methodOf Hyphenator
	 * @description
	 * Calls hyphenateElement() for all members of elements. This is done with a setTimout
	 * to prevent a "long running Script"-alert when hyphenating large pages.
	 * Therefore a tricky bind()-function was necessary.
	 * @public
	 */
	hyphenateDocument = function () {
		function bind(fun, arg) {
			return function () {
				return fun(arg);
			};
		}
		var i = 0, el;
		while (!!(el = elements[i++])) {
			window.setTimeout(bind(hyphenateElement, el), 0);

		}
	},

	/**
	 * @name Hyphenator-removeHyphenationFromDocument
	 * @methodOf Hyphenator
	 * @description
	 * Does what it says ;-)
	 * @public
	 */
	removeHyphenationFromDocument = function () {
		var i = 0, el;
		while (!!(el = elements[i++])) {
			removeHyphenationFromElement(el);
		}
		state = 4;
	};

	return {
		
		/**
		 * @name Hyphenator.version
		 * @memberOf Hyphenator
		 * @description
		 * String containing the actual version of Hyphenator.js
		 * [major release].[minor releas].[bugfix release]
		 * major release: new API, new Features, big changes
		 * minor release: new languages, improvements
		 * @public
         */		
		version: '2.0.0',
		
		/**
		 * @name Hyphenator.languages
		 * @memberOf Hyphenator
		 * @description
		 * Objects that holds key-value pairs, where key is the language and the value is the
		 * language-object loaded from (and set by) the pattern file.
		 * The language object holds the following members:
		 * <table>
		 * <tr><th>key</th><th>desc></th></tr>
		 * <tr><td>leftmin</td><td>The minimum of chars to remain on the old line</td></tr>
		 * <tr><td>rightmin</td><td>The minimum of chars to go on the new line</td></tr>
		 * <tr><td>shortestPattern</td><td>The shortes pattern (numbers don't count!)</td></tr>
		 * <tr><td>longestPattern</td><td>The longest pattern (numbers don't count!)</td></tr>
		 * <tr><td>specialChars</td><td>Non-ASCII chars in the alphabet.</td></tr>
		 * <tr><td>patterns</td><td>the patterns</td></tr>
		 * </table>
		 * And optionally (or after prepareLanguagesObj() has been called):
		 * <table>
		 * <tr><td>exceptions</td><td>Excpetions for the secified language</td></tr>
		 * </table>
		 * @public
         */		
		languages: {},
		

		/**
		 * @name Hyphenator.config
		 * @methodOf Hyphenator
		 * @description
		 * Config function that takes an object as an argument. The object contains key-value-pairs
		 * containig Hyphenator-settings. This is a shortcut for calling Hyphenator.set...-Methods.
		 * @param object <table>
		 * <tr><th>key</th><th>values</th><th>default</th></tr>
		 * <tr><td>classname</td><td>string</td><td>'hyphenate'</td></tr>
		 * <tr><td>minwordlength</td><td>integer</td><td>6</td></tr>
		 * <tr><td>hyphenchar</td><td>string</td><td>'&amp;shy;'</td></tr>
		 * <tr><td>urlhyphenchar</td><td>string</td><td>'zero with space'</td></tr>
		 * <tr><td>togglebox</td><td>function</td><td>see code</td></tr>
		 * <tr><td>displaytogglebox</td><td>boolean</td><td>false</td></tr>
		 * <tr><td>remoteloading</td><td>boolean</td><td>true</td></tr>
		 * <tr><td>onhyphenationdonecallback</td><td>function</td><td>empty function</td></tr>
		 * <tr><td>onerrorhandler</td><td>function</td><td>alert(onError)</td></tr>
		 * <tr><td>intermediatestate</td><td>string</td><td>'hidden'</td></tr>
		 * </table>
		 * @public
		 * @example &lt;script src = "Hyphenator.js" type = "text/javascript"&gt;&lt;/script&gt;
         * &lt;script type = "text/javascript"&gt;
         *     Hyphenator.config({'minwordlength':4,'hyphenchar':'|'});
         *     Hyphenator.run();
         * &lt;/script&gt;
         */
		config: function (obj) {
			var assert = function (name, type) {
					if (typeof obj[name] === type) {
						return true;
					} else {
						onError(new Error('Config onError: ' + name + ' must be of type ' + type));
						return false;
					}
				},
				key;
			for (key in obj) {
				if (obj.hasOwnProperty(key)) {
					switch (key) {
					case 'classname':
						if (assert('classname', 'string')) {
							hyphenateClass = obj.classname;
						}
						break;
					case 'donthyphenateclassname':
						if (assert('donthyphenateclassname', 'string')) {
							dontHyphenateClass = obj.donthyphenateclassname;
						}						
						break;
					case 'minwordlength':
						if (assert('minwordlength', 'number')) {
							min = obj.minwordlength;
						}
						break;
					case 'hyphenchar':
						if (assert('hyphenchar', 'string')) {
							if (obj.hyphenchar === '&shy;') {
								obj.hyphenchar = String.fromCharCode(173);
							}
							hyphen = obj.hyphenchar;
						}
						break;
					case 'urlhyphenchar':
						if (obj.hasOwnProperty('urlhyphenchar')) {
							if (assert('urlhyphenchar', 'string')) {
								urlhyphen = obj.urlhyphenchar;
							}
						}
						break;
					case 'togglebox':
						if (assert('togglebox', 'function')) {
							toggleBox = obj.togglebox;
						}
						break;
					case 'displaytogglebox':
						if (assert('displaytogglebox', 'boolean')) {
							displayToggleBox = obj.displaytogglebox;
						}
						break;
					case 'remoteloading':
						if (assert('remoteloading', 'boolean')) {
							enableRemoteLoading = obj.remoteloading;
						}
						break;
					case 'enablecache':
						if (assert('enablecache', 'boolean')) {
							enableCache = obj.enablecache;
						}
						break;
					case 'onhyphenationdonecallback':
						if (assert('onhyphenationdonecallback', 'function')) {
							onHyphenationDone = obj.onhyphenationdonecallback;
						}
						break;
					case 'onerrorhandler':
						if (assert('onerrorhandler', 'function')) {
							onError = obj.onerrorhandler;
						}
						break;
					case 'intermediatestate':
						if (assert('intermediatestate', 'string')) {
							intermediateState = obj.intermediatestate;
						}
						break;
					case 'selectorfunction':
						if (assert('selectorfunction', 'function')) {
							selectorFunction = obj.selectorfunction;
						}
						break;
					default:
						onError(new Error('Hyphenator.config: property ' + key + ' not known.'));
					}
				}
			}
		},

		/**
		 * @name Hyphenator.run
		 * @methodOf Hyphenator
		 * @description
		 * Bootstrap function that starts all hyphenation processes when called.
		 * @public
		 * @example &lt;script src = "Hyphenator.js" type = "text/javascript"&gt;&lt;/script&gt;
         * &lt;script type = "text/javascript"&gt;
         *   Hyphenator.run();
         * &lt;/script&gt;
         */
		run: function () {
			var process = function () {
				try {
					autoSetMainLanguage();
					gatherDocumentInfos();
					prepare(hyphenateDocument);
					if (displayToggleBox) {
						toggleBox(true);
					}
					//registerOnCopy();
				} catch (e) {
					onError(e);
				}
			};
			if (!documentLoaded) {
				runOnContentLoaded(window, process);
			}
			if (Hyphenator.isBookmarklet() || documentLoaded) {
				process();
			}
		},
		
		/**
		 * @name Hyphenator.addExceptions
		 * @methodOf Hyphenator
		 * @description
		 * Adds the exceptions from the string to the appropriate language in the 
		 * {@link Hyphenator-languages}-object
		 * @param string The language
		 * @param string A comma separated string of hyphenated words WITH spaces.
		 * @public
		 * @example &lt;script src = "Hyphenator.js" type = "text/javascript"&gt;&lt;/script&gt;
         * &lt;script type = "text/javascript"&gt;
         *   Hyphenator.addExceptions('de','ziem-lich, Wach-stube');
         *   Hyphenator.run();
         * &lt;/script&gt;
         */
		addExceptions: function (lang, words) {
			if (lang === '') {
				lang = 'global';
			}
			if (exceptions.hasOwnProperty[lang]) {
				exceptions[lang] += ", " + words;
			} else {
				exceptions[lang] = words;
			}
		},
		
		/**
		 * @name Hyphenator.hyphenate
		 * @methodOf Hyphenator
		 * @public
		 * @description
		 * Hyphenates the target. The language patterns must be loaded.
		 * If the target is a string, the hyphenated string is returned,
		 * if it's an object, the values are hyphenated directly.
		 * @param mixed the target to be hyphenated
		 * @param string the language of the target
		 * @returns string
		 * @example &lt;script src = "Hyphenator.js" type = "text/javascript"&gt;&lt;/script&gt;
		 * &lt;script src = "patterns/en.js" type = "text/javascript"&gt;&lt;/script&gt;
         * &lt;script type = "text/javascript"&gt;
		 * var t = Hyphenator.hyphenate('Hyphenation', 'en'); //Hy|phen|ation
		 * &lt;/script&gt;
		 */
		hyphenate: function (target, lang) {
			var hyphenate, n, i;
			if (Hyphenator.languages.hasOwnProperty(lang)) {
				if (!Hyphenator.languages[lang].prepared) {
					prepareLanguagesObj(lang);
				}
				hyphenate = function (word) {
					if (urlOrMailRE.test(word)) {
						return hyphenateURL(word);
					} else {
						return hyphenateWord(lang, word);
					}
				};
				if (typeof target === 'string' || target.constructor === String) {
					return target.replace(Hyphenator.languages[lang].genRegExp, hyphenate);
				} else if (typeof target === 'object') {
					i = 0;
					while (!!(n = target.childNodes[i++])) {
						if (n.nodeType === 3 && n.data.length >= min) { //type 3 = #text -> hyphenate!
							n.data = n.data.replace(Hyphenator.languages[lang].genRegExp, hyphenate);
						} else if (n.nodeType === 1) {
							Hyphenator.hyphenate(n, lang);
						}
					}
				}
			} else {
				onError(new Error('Language "' + lang + '" is not loaded.'));
			}
		},
		
		/**
		 * @name Hyphenator.isBookmarklet
		 * @methodOf Hyphenator
		 * @description
		 * Returns {@link Hyphenator-isBookmarklet}.
		 * @returns boolean
		 * @public
         */
		isBookmarklet: function () {
			return isBookmarklet;
		},


		/**
		 * @name Hyphenator.toggleHyphenation
		 * @methodOf Hyphenator
		 * @description
		 * Checks the current state of the ToggleBox and removes or does hyphenation.
		 * @public
         */
		toggleHyphenation: function () {
			switch (state) {
			case 3:
				removeHyphenationFromDocument();
				toggleBox(false);
				break;
			case 4:
				hyphenateDocument();
				toggleBox(true);
				break;
			}
		}
	};
}());
if (Hyphenator.isBookmarklet()) {
	Hyphenator.config({displaytogglebox: true, intermediatestate: 'visible'});
	Hyphenator.run();
}

Hyphenator.languages.en = {
	leftmin : 2,
	rightmin : 2,
	shortestPattern : 2,
	longestPattern : 8,
	specialChars : '',
	patterns : {
		3 : 'a2da2fai2a1ja2n4ao2bfb1jbk44bp2btb1v1cac3c2ch1cick1c5n1coc1q1cyd1bd5cd1jd1m1dod1p1dr1dud1vd1wd2ye1fei2e1je1q4eu1fa4fd4fh1fi4fm4fn1fo2ft3fu1fy1gag3bgd4gl2g1m1gog3p1grgs2g3w1gyh1bh1fh1h4hkh1w2id2igi3hi3j4ik2io2ip4iri1u2iv4iy5ja1jek1bk3fkh4k1ikk4k1lk1mk5tk1w2ld2lf4ljl1l2lm2lp4lt1ly1ma2mh4mkm1m1mo4mt1mu4mw1nan3fn1jn5mn1qn1rn1t4nz4oaoi2o5j2oko2noo2o1qou21papd44pf4pgpr2p3wqu2r1br1cr1frg2rh4r3jr1lr1mr1pr1wsa2s2hsk21sos1r2ss1su4svsw2s4y1ta4tc2tl1to1tu4tvtw41ty4tzu5j4uk2usu3u1vav4yw1bwi2w4kw5p4wtwy4x1ax1ex1hx3ix3ox3px1uxx4y1by1cy1dy1iy1wza14zb2ze5zl4zm1zo',
		4 : '_ch4_ci2_eb4_eg2_es3_eu3_ga2_ge2_he2_in1_le2_me2_od2_os3_sh2_si2_st4_sy2_ta4_te4_th2_ti2_up3_ye44ab_abe24abr2adi4aduae4raff4ag1iag1na2goa4gya3haa3heah4la3hoa5ia2aleal1i4alm4amaa2mo4and2angano4a2pla3pu2a2rar1iar2par3q4as_as4la2ta4atha1tra2tua2tyau4bau3ra2vaav1iaw3iaws4aye4ays45ba_1batba4z2b1bb2be4b1d4be_1bel3betbe3w4b3hbi2bbi4d3bie1bilbi2tb2l2b4lo4b1m4b3n3bodbo4e3boobt4lb4tob3trbu4n4b5w5by_bys42ce_3cei1cen3cepcet4cew44ch_che23ciaci5c4cii2cim2cin5cizck3icly4coe22cogcoi4cov1cri22c1tc2tec4twcud5c4ufc4ui3cun1cuscze41d2a5da_4daf2dag3dat5dayd1d42de_d4em1dende1pd3eqdes2de1tde1v4dey4d1fd4gadg1id2gyd1h25di_3didd1ifd1in1diodir2dis1d5k22dly3do_5doed4ogd4or3dosdo4v3doxdre44dryds4pd4swd4syd2thdu2cdu4gdu4n4dup5dynead1ea4lea2tea2v2e1be3bre1ceec2ie1cre1cu4edi4edoee2cee2fee2me5ex1effeg5n5egye1h4e5icei5deig2e1lael2fel2iem5be1mee3my4enn4enoe5ofeo2ge3ole1oreos4e4ote5owe2pae1poer1a2erber1her1i2eroer1s4erues2c4eshe1sie1sp2esses4w4etnet5ze5une3upeus4e1vie5vue1wae3wh1exp5eyceys44fag5far4f5b4fe_fe4b2fedfer1fev44f1ff2fyfi3a2finf4l25fonfo2rfos54f5pfri22f3sf4tof2ty4fuggaf42gam4gaz2ge_2ged1gen1geoge4vg2geggo45gi_g1icgil45gio3girgi4u5giv3gizgla41gle3glog4mygn4ag1nig1no3go_gob55goegon25googov1g4rogth3gu4a2gue3gun3gusha4m5hazh4edhe2nhep5h1eshe4theu4hi4phi2vh2lo4h1m2h1nho4g4h5p4hr4h4shh4tyhu4ghu4thy2s2i1ai2aliam4i2anibe4i1bli5boi1br4ich2iciid5di2dii4dri2du2ie4i3et4if_i3fl4ift4igii2goi1lail5fil1i4ilnil3vim1ii2mu2in_4ind2ine2ini4ink4inl2inn2insin1u4iny4io_i1olio4mi4osipe4ip3ii1rair1i2is_4ise3isfi2sois1pi2su2ite2ithi1ti4itt4i5wix4oizi4ja4pjew3jo4p3ka_k3abk5agkal4k2ed1keeke4gk1erkes45ki_k4imki4pkis44klyko5rk3ouk4scks4lk4sy4lav2l1blce4l3cil2deldi4l3drle2ales23leyl5frl5galgo32l3h3likl1itl1izlka3l2lell2ill4o3lo_4lof4lovl4pll5pr4l1rl4scl2sel1tel1trltu2lu5aluf4lu3o4lup1lut2l1w4lya4lyb2mab2mah4map4m1b4m5c4me_2medme2gme2m1men2mesme4v4m1f5mi_mi3amig4m2ism2iz4m1l4m1nmn4amn4o4mokmo2rmos2mo2v4m1pm2pim2py4m3rm4shm5si3mummun24mupmu4unak4n2ann4asn2atn2aun1crn1cun1de2ne_ne2bne2c2ned1nen3neone2qn1er1nesne4vne4wn1gun2gynha4nhe4ni4dnik4n1imn1inni4on2it4nk2n1kl4n1lnme4nne43noe4nogno4n4nop1noun1p4npi4nru4ns4cn2sen2slns3mnt2int4snu1anu4dn4umn3uon1v2n1w4nym4nyp4n3zaoad3o1bio3bro1ceoch4o4elo3ero3evo2fio1geo4gl1ogyo1h2oig4o1laol2dol2iol2tol2vo2lyo2meon1aon1c2ondon3soo4ko2pa2opho1prop1uopy5o1rao1ryos2cos4lo2so4othou4lou5vow1io4wooy1ap4adp4aip4alpa1ppav43pay4p1b4pe_pe2cp4eepek4pe2t4ph_ph2l4phsph3t5phu1phypi3ap4idpi2n4p1m2p3npo4cpo4p1posp4ot4p1pp2pep2seps4h2p1tp2tep2thp4twpub3pue4puf4pu4mpu2n5puspu2t2rabr2air2asrbi2rb4or2cerd2i2re_re1oreu2rev2rfu4r4fyr1glr3gu4rh_ri3ar4ibri1or4iqr2isrle4r2mer4myrno4r3nur2ocro4erok2rox5r3por1r44rs2r1sars4cr2ser1shr1sir1spr5swr1tiru3aru2nrv4er3vory4cry3t5sais1apsau45saw4s5bsch2s1cu4s5d4se_se4ase2g5sei5sev5sex4s3f2s3g2sh_sho44shwsi1b1siosi2r1sis5siu1siv5siz4skes1l2s2le2s1ms3mas1n43soms4op4sov2spas1sas1sis4sls4snss2tss5w2st_st2ist4rs2tys4ulsu2msu2nsu2r4swo4syc3syl3ta_2tabta2ltav42taw2t1bt4ch4t1d4te_1teeteg41teote4p3teu3tex4tey2t1f4t1g2th_th2e4thl2ths1tiatif22tig1tim1tio5tiqti4u1tiv1tizt5lat5lo4t1mtme4to3b2toftos24t1p1trat4sctsh4t4swt5tottu4tu1atud24tue3tum3tus4two4tya2tyltz4e4uabuac4u1atuav4ub4eu3cau3cru3cuu4cyud5du4du3ufau3fl2ui2ui4nuiv3u1laul4eul2i4ulsu3luul5vu1mium2pu2neu1niunu4un5yun5zu5osu1ouu1peu3plup3pu1raurc4ur1dur2lu3ruusc2us1pu2suuts4uu4mu1v2uxu3uz4e5va_vag43vat4ve_4vedveg3v3ifvik42vilv1invi4p3viv5vo_voi43vok4vv42wacwam4w1erw3evwhi4wil2wir4wiz5w4no1wo2wom1wra4wri4w3shws4lxam3x4apxas5x3c2x2edxhi2xhu4xi5axi5cx4obx1t2x3tixu3ay5acy5aty2cey3chy5eey1eryes4ye4ty5gi4y3hy3lay3loy5luyme4yn5dyn5g5ynxy1o4yo5dyom4y4osyp3iy3poy5puy3royr4rys4cy4soyss4ys1tzar2ze4nze4pz1erzet42z1iz4ilz4iszo4mzte4z4zy',
		5 : '_ach4_af1t_al3t_an5c_ang4_ant4_ar5s_as3c_as1p_as1s_au1d_av4i_awn4_ba4g_ber4_bri2_ca4t_co3e_co4r_de3o_do4t_du4c_eer4_el5d_en3g_en3s_eye5_fes3_gi5a_gi4b_go4r_hes3_het3_hi3b_hov5_id4l_im3m_ine2_in2k_in3s_ir5r_is4i_ju3r_la4m_len4_lep5_lev1_li4g_li2n_li3o_li4t_mis1_ni4c_odd5_or3c_or1d_or3t_oth3_out3_pi4e_pi2t_ra4c_ree2_res2_ri4g_ro4q_ru4d_se2n_til4_to4p_un1a_un1e_un5k_un5o_un3u_ure3_us5aa5bala5banabi5aab3ula4carac1er4a2cia3cieac1ina3cioac3ulac4uma3diaa3dioa3dita5diuad4lead3owad4sua3ducad5uma4gabaga4nage4o4ageu4ag4l3agogag5ula3ic_ai5lya4i4nain5oak1enal5abal3ada4lar4aldiali4ea4ly_4alys5alyt3alyzam5abam3agam3icam5ifam1ina5mona3naran1dla5neea3nena3neuan1glan3ioa3nipan3ita3niuan5otan2saan4snan2span4st4antoan2tran4twan3uaan3ula5nurapar4ap5at4aphiap3inapoc5aque5ar3alara3par4ata5rauaraw4ar4dra3reear4fiar4flar4imar3ioar2izar2mia3rooarre4ar4saar2shas4abashi4a3siba3sicask3ia4socas5phas4shas1trat5acat5apate5cat5evat4ho4ati_a5tiaat1icat3ifa4toga2toma4topa4tosat4skat5teat4that5uaat5ueat3ulaugh3au3guau4l2aun5dau1thav3aga5vanav3igav5oca1vor3awayaw4lyax4icax4iday5alazz5iba4gebal1aban4eban3ib3berbeak4beat34be2dbe3dabe3debe3dibe3gibe5gube1libe3lo4be5mbe5nu4bes4be3spbe5trbe3twbe5yobi5enbi4er2b3ifbin4dbi5oubi3trb5itzb4le_blen4b3lisbne5gbod3ibon4a5bor_bor5d5bore5bori5bos4b5otaboth5bo4to4brit2b5s2bsor4bu4gabu3libumi4bu3re5bust4butab5utoca1blcach44cag42c5ah4calocan5dcan4ecany44casyca4thccha5cci4accon44ced_5cel_3cell3cenc4ceni3cent4cesaces5t4ched5chio3chitchi2z3cho2ch4ticia5r4cierci4la3cilic4inac1ing5cinocion44cipeci3ph2c1it1c4l44clarcle4m4clicclim4co5agco4grcol5i5colocon4ac4onecon3gcon5tco3paco4pl4corbcos4ecove4cow5acoz5eco5zi5credcre4vcri5fc4rincris4cru4d4c3s2cta4bc3terctu4r5culicu2mac3umecu4micu3picu5py3c4ut4cutrdach4da2m2dan3gdard5dark54dary4dato5dav4dav5edeaf52d1ed4dee_de5ifde5lo5dem_de3node3nude3padepi4de2pud4erh5dermder5sd2es_de1scde4sude2todia5bd4ice3dictdi3ge1dina5dinidio5gdi4pldi1re5disid2iti1di1v4d5la3dle_3dled2d3lo4d5lu4d1n4do5de2d5ofdo4ladoli4doni4doo3ddop4p4drai5drendri4bdril4dro4p4drow2d1s2d1u1ad1ucadu5eld3uledu4pedy4sedys5pe1a4be3actea4gee5andear3aear4cear5kear2tea5spe3asseast3eav5ieav5oe4bene4bite4cadecca5e4cibec3imeci4te2cole2corec4tee4cul2e2da4ed3dede4se3diaed3ibed3imed1itedi5ze4doledon2e4drie4duleed3ieel3iee4lyee4naee4p1ee2s4eest4ee4tye4ficefil43efit4egaleger4eg5ibeg4ice4go_e4goseg1ule5gureher4ei5gle3imbe3infe1ingeir4deit3eei3the5itye4judeki4nek4lae4la_e4lace4lawe3lea5elece4lede5lene1lese5lime3lioe2lis4ellaello4e5locel5ogel2shel4tae5ludel5uge4mace4mage5mane2mele4metemi4ee4misem3izemo4gem3pie4mulemu3ne5neae5neeen3eme3newe5niee5nile3nioen3ite5niu5enizeno4ge4nosen3oven4swen3uaen5ufe3ny_4en3ze4oi4eo3reeo4toe5oute3paie5pelephe4e4plie3proep4she4putera4ber3arer4bler3ch2ere_ere4qeret4e1rio4eriter4iueri4ver3m4er3noer5obe5rocero4rer1ou4ertler3tweru4te1s4ae2scae3scres5cue1s2ee2sece3shae2sice2sidesi4ues4mie2sole2son2estre2sureta4be3teoet1icetin4e5tire3trae3treet3uaet5ymeu3roeute4eu5tre2vase5veaev1erev3idevi4le4vinevi4ve5voce4wage5weeewil5e3wit5eye_fa3blfab3rfa4cefain4fa3ta4fatofeas44feca5fectfe3life4mofen2d5ferrf4fesf4fief4flyfic4i4ficsfi3cufil5i4fily5finafi2nefin4nflin4f2ly5fon4tfor4ifra4tf5reafril4frol5fu5elfu5nefu3rifusi4fus4s4futa5gal_3galiga3log5amo4ganogass4gath3geez44gely4geno4genyge3omg4ery5gesigeth54getoge4ty4g1g2g3gergglu5gh3ingh4to1gi4agia5rg4icogien5gir4lg3isl5glasgli4bg3ligglo3rg4na_g2ning4niog4nongo3isgo3ni5gos_g4raigran24graygre4n4gritgruf4g5ste4gu4tgy5rahach4hae4mhae4th5aguha3lahan4ghan4khap3lhap5thar2dhas5shaun4haz3a1head3hearh5elohem4phena4heo5rh4erah3ernh3eryhi5anhi4cohigh5h4il2h4inahir4lhi3rohir4phir4rhis4s4h1l4hlan4hmet4h5odshoge4ho4mahome3hon4aho5ny3hoodhoon4ho5ruhos4ehos1p1houshree54h1s2h4tarht1enht5eshun4thy3pehy3ph4iancian3iia5peiass4i4atuib5iaib3inib3lii5bun4icam5icap4icaricas5i4cayiccu44iceoi5cidi2cipi4cly4i1cr5icrai4cryic4teictu2ic4umic5uoi3curi4daiide4si5dieid3ioid1itid5iui3dlei4domid3owid5uoied4eield3ien4ei5enni1er_i3esci1estif4fri3fieiga5bi3gibig3ilig3inig3iti4g4lig3orig5oti5greigu5iig1ur4i5i4i3legil1erilev4il3iail2ibil3io2ilitil2izil3oqil4tyil5uri4mag4imet4imitim4nii3mon4inavi3nee4inga4inge4ingi4ingo4ingui5ni_i4niain3ioin1is2i1noino4si4notin3se2int_i5nusioge4io2grion3iio5phior3iio5thi5otiio4toi4ourip4icip3uli3quaira4bi4racird5ei4refi4resir5giir4isiro4gir5ulis5agis3arisas52is1cis3chis3eris3ibisi4di5sis4is4k4ismsis2piis4py4is1sis1teis1tiis5us4ita_i4tagi3tani3tatit4es4itiait3igi2tim2itio4itis4itonit5ryi5tudit3ul4itz_iv5ioiv1it4izarjac4qjer5s5judgkais4ke5like4ty5k2ick4illkilo5k4in_kin4gk5ish4kleyk5nes1k2nokosh4kro5n4k1s2l4abolaci4l4adela3dylag4nlam3o3landlar4glar3ilas4elbin44l1c2ld5isl4drile4bileft55leg_5legg4len_3lenc1lentle3phle4prler4e3lergl4ero5lesq3lessl3eva4leye4l1g4lgar3l4gesli4agli2amli4asli5bi4licsl4icul3icyl3ida3lidil4iffli4fl3lighlim3ili4mol4inalin3ili5og4l4iqlis4pl2it_l3kallka4tl4lawl5leal3lecl3legl3lell5lowl5metl4modlmon42l1n2lo4cil5ogo3logu5longlon4ilood5lop3il3opmlora45los_los4tlo4ta2loutlpa5bl3phal5phil3pit2l1s2l4sielt5aglten4lth3iltis4lu3brluch4lu3cilu3enlu5idlu4ma5lumiluo3rluss4l5venly5mely3no2lys4l5ysema2cama4cl5magnmaid54maldmar3vmas4emas1t5matemath3m5bilmbi4v4med_mel4tmen4a4menemen4imens43mentme5onme4tame1tem4etrmid4amid4gm4illmin4a3mindmin4tm4inumiot4mis5l4mithm4nin4mocrmo2d1mo4gomois2mo3memo3spmoth3m5ouf3mousm3petmpi4am5pirmp5ismpov5mp4tr4m1s25multn4abu4nac_na4can5actna4li4naltnank4nar3c4narenar3inar4ln5armnas4c3nautnav4e4n1b4ncar5n3chanc1innc4itn4dain5danndi4bn1ditn3dizn5ducndu4rnd2wen3earneb3u5neck5negene4lane5mine4mo4nenene4pon2erener4r2nes_4nesp2nest4neswn5even4gabn3gelng5han3gibng1inn5gitn4glangov4ng5shn4gum4n1h4nhab33n4iani3anni4apni3bani4blni5dini4erni2fin5igrnin4g5nis_n4ithni3trn3ketnk3innmet44n1n2nni4vnob4ln5oclnoge4no4mono3mynon5i4noscnos4enos5tno5ta3nounnowl32n1s2ns5abnsid1nsig4n4socns4pen5spinta4bn5tibnti2fnti4pnu5enn3uinnu1men5umi3nu4nnu3troard3oas4eoat5io5barobe4lo2binob3ulocif3o4cilo4codocre3od3icodi3oo2do4odor3o5engoe4tao5geoo4gero3gieog3ito4groogu5i2ogynohab5oiff4o3ingo5ismo3kenok5ieo4lanold1eol3ero3letol4fio3liao5lilo5lioo5livolo4rol5plol3ubol3uno5lusom5ahoma5lom2beom4blo4meto3miao5midom1ino4monom3pion4aco3nanon5doo3nenon4guon1ico3nioon1iso5niuonsu4on5umonva5ood5eood5ioop3io3ordoost5ope5dop1ero3pito5pono5ra_ore5aor3eiorew4or4guo5rilor1ino1rioo3riuor2miorn2eo5rofor5pe3orrhor4seorst4or4tyo5rumos3alos4ceo5scrosi4uos4paos4poos2tao4tano4teso3tifo3tisoto5sou3blou5etoun2dov4eno3visow3elown5ipa4capa4cepac4tpain4pan4apa3nypa4pu3parepa2te3pe4a2p2ed3pede3pedipee4dpe4lap4encpe5onp4erip4ernper3ope5ruper1vph4erph1ic5phie3phiz3phobpho4rpian4pi4cyp5idapi3de5pidi3piecpi3enpi3lop4in_pind4p4ino3pi1opion4p3ithpi2tu2p3k21p2l23planpli3a4pligpli4nploi4plu4m5pod_po5em5po4gpoin2po4ni1p4orpo4rypos1spo4ta5pounp4pedp5pelp3penp3perp3petpre3rpre3vpri4spro3lpro1t2p1s2p4sibpti3mptu4rpul3cpur4r5putepu3trqua5v2que_3quer3quetra3bir5aclraf4tra4lor2amir4anira5norar5crare4rau4tr4babr4bagrbi4fr2binrcen4r3charc4itrcum3r4dalrdi4ardin4re1alre3an5reavre4aw2r2edre1dere2fere3fire4fyre5itre1lire5lure1pur1er4r4erirero4re5rur4es_res2tre4whrg3err3getr3gicrgi4nr5gisr5gitrgo4n4rhalria4bri4agrib3ar4ice4ricir4icori1erri5et5rigirim5i3rimor2inarin4drin4erin4g5riphri2plr4is_ris4cr3ishris4pri2turiv3ir3ketrk4ler2ledr4ligr4lisr3lo4rma5cr3menr4mior3mitr4narr3nelr4nerr5netr3neyr5nicr3nitr3nivr4nourob3lro3crro1ferom4irom4pron4e1room5rootror3iro5roros4sro4tyro4var4pear3petrp4h4rre4crre4fr4reorri4orri4vrron4rros4rrys4r3secrs3esr5sharson3r4tagr3tebrte5ort5ibrti4dr3tigr4tivr3trirt4shru3enru4glru3inrunk5r5uscr3venr3veyr3vicrvi4v2s1ab5sacks3actsal4msa5losal4t3sancsa5tasat3usca4pscav5s4ced4sceis4cess4choscle5s4cliscof4seas4sea5w3sect4s4eds5edlseg3rse1le5self5selv4seme4sencsen4dsen5gs4erlser4os1e4sse5shses5tsew4ish1er5shevsh1insh3io3shipshiv5shon3shor4s5icc5sidisil4e4sily2s1ins2inas3ing5sionsir5as3kets3latsman3smel4s5menso4cesoft35solvsona4son4gsor5csor5dso5vi5spaispa4n2spers2phespho5spil44spios4plys4ponspor44spotssas3s2s5cs3sels5sets4siess4lis2tags2tals4tedste2ws3thes4ti_s5tias1tics4ties3tif5stirs1tles4top4stry4st3wsu1alsu4b3su2g3su5issuit3sum3isyn5o4tacita5do4taf4ta5latal3i4talkta5mota5pltar4a4tarc4taretas4eta5sytaun44teattece45tect2t1edte5dite5gi3tel_teli45tels3tenc3tend1tentte5peter3c1teriter5v4tes_4tessthan44thea3thet4thil4thooti4ab2ti2b4tickt4ico5tidi3tienti5fy5tigu4timp2t1int2ina3tiniti5octi3sa3tisetis4mti5sotis4pti3tltiv4ati3zatlan43tle_3tled2t1n24todoto2grto5icto2matom4bto3my4tono4tonyto2ra5tour4touttra3btras4tre5ftre4m5tria2trimtri4vtro3vtru5itrus44t1s24t3t2t4testu3artu4bi4tuf45tu3i3ture5turitur5otu5ry4t1watwis4type3ty5phua5nauan4iuar2duar3iuar3tu4belu3beru1b4iuci4buc4itucle3ud3erudev4u1dicud5isu5ditu4donud4siu4eneuens4ug5inu1inguir4muita4ula5bulch4u1lenul4giu5lia4ul3mu1l4oul1ti4ultuul5ulum5abum4biunat4un4erun4imu2ninuni3vun3s4un4swu4orsu5piauptu44ura_u4ragu4rasur4beur4fru3rifur1inu3riou1ritur3izur4nouros4ur4peur4piurti4u5sadu5sanus4apus3ciuse5au5siau3sicus5slus1trusur4uta4bu3tat4ute_4utel4utenu4tisu4t1lut5ofuto5gu5tonu4touvac3uva4geval5oval1uva5mova5piv3el_ve4lov4elyv4erdv4e2s4ves_ve4teve4ty5vian5vidivi5gnv2incvin5d4vingvio3lvi1ouvi5rovi3sovi3su4vitivit3r4vityvo4lav5ole5volt3volvvom5ivori4vo4ryvo4taw5ablwag5owait5w5al_war4twas4twa1tewed4nweet3wee5vwel4lwest3win4g3wisewith3wl4eswl3inws4pew5s4txac5ex4agoxer4ixe5roxhil5xi5dix4imexpe3d3yar4yc5erych4eycom4ycot4y4erfympa3yn5icy4o5gy4onsy4pedyper5y4pocyp2tayra5myr5iay3s2eys3io3ysisys3taysur4yt3icz5a2bze3rozo5ol4z1z2',
		6 : '_am5at_ani5m_an3te_ar4ty_atom5_ba5na_bas4e_be5ra_be3sm_can5c_ce4la_cit5r_de3ra_de3ri_des4c_dumb5_eas3i_el3em_enam3_er4ri_ge5og_han5k_hi3er_hon3o_idol3_in3ci_la4cy_lath5_leg5e_lig5a_mal5o_man5a_mer3c_mon3e_mo3ro_mu5ta_of5te_os4tl_pe5te_pio5n_pre3m_ran4t_rit5u_ros5t_row5d_sci3e_self5_sell5_sing4_ting4_tin5k_ton4a_top5i_tou5s_un3ce_ve5ra_wil5iab5erdab5latab5rogac5ardac5aroa5ceoua5chetac5robact5ifad4dinad5er_ad3icaadi4erad5ranaeri4eag5ellag3onia5guerain5inait5enal3enda5le5oal4ia_al5lev4allica5log_ama5raam5ascam5eraam5ilyami4noamor5iamp5enan3age3analyan3arcanar4ia3natiande4san3disan4dowang5iea4n1ica3niesan3i3fan4imea5nimia5ninean3ishan4kli5annizanoth5an4scoans3poan4surantal4an4tieap5eroa3pherap3itaa3pituap5olaapor5iapos3taps5esar3acta5radearan4gar5av4arbal4ar5easar3enta5ressar5ialar3iana3rietar5o5da5ronias3anta5sia_as3tenasur5aat3ablat3aloat5echat3egoat3en_at3eraater5nat3estath5ema5thenath5omat5i5bat3ituat5ropat4tagat3uraau5sibaut5enave4noav3eraav5ernav5eryavi4erazi4erbarbi5bari4abas4sibbi4nabe5nigbe5strbet5izbi3lizbi5netbi3ogrblath55blespblun4tbol3icbom4bibon5at4b1orabound3broth3bunt4ibus5iebuss4e3butiocab3inca5denca3latcal4lacan4iccan5iscan3izcan4tyca5percar5om4cativcav5alccou3t4ceden2cen4ece5ram3cessic5e4ta4ch3abcheap3che5lo3chemich5enech3er_ch3ers4ch1in5chinici2a5b3cinatcin3emc5ing_4cipic4cista4cisticit3iz5clareco3inccol3orcom5ercop3iccoro3ncras5t5crat_cre3at5criticro4plcrop5ocros4ect5angc5tantc4ticuctim3icu5ity3cultucu5riacuss4icu4tie2d3a4b4dativdeb5itde4bondecan4de4cilde5comdeli4e3demicde5mildemor5de4narde2s5odes3tide3strdev3ild3ge4t1d4i3adi4cam5di3en3dine_di5nizdirt5id4is3t3dles_4dlessdo5lordom5izdo3nat4d5outdrea5rduc5er4duct_4ductsdum4beead5ieea5gereal5ereal3oueam3erear5esear4icear4ileart3eeat5eneath3ie5atife4a3tueav3ene4bel_e4belsecan5cec5ifye5citee4clame4cluse4comme4concec3oraeco5roe4cremec4tanec3ulae4d1ered3icaed5ulo5eficie3fineeg5inge5git5e5instej5udielan4delaxa4el3egae4l1ere3libeel3icae3lierel5ishe3liv3el4label3op_em5anaem3icaem1in2em5ineem5ishe5miss5emnizem5ulaen5amoe4nanten3dicen5eroen5esien5esten3etren5icsen3isheop3areo5rolep5ance3pente4prece4predep3rehe4probep5utaequi3l4erander4chee3realere5coere3iner5el_er3emoer5ena4ereneer3enter5esser3este1ria45ericke3rieneri4erer3inee4rivaer4nis4ernit5ernizer3setert3er5erwaues5canes5ecres5encesh5ene2s5imes4i4ne5skines3olues5onaes3peres4preestan4es3tiges5tim4es2toe3stone5stroes5urreten4dethod3e5tideeti4noet5onaet3ricet5rifet3roget5roseuti5leva2p5ev5astev3ellevel3oe5vengeven4ie5verbew3ingfall5e4fa4mafam5isfar5thfa3thefault5feath3fend5ef5fin_f2f5is2f3ic_f3icanf3icenfi3cer5ficia5ficiefi5delfight5fin2d5f1in3gfis4tif5lessflo3refon4defo5ratfor5ayfore5tfort5afres5cfu4minga5metgan5isga3nizgar5n44gativgel4inge5lisge5lizge4natge5nizgh5out5gicia5gies_g3imen3g4in_gin5ge5g4insglad5ignet4t3g4o4ggondo5go5rizgor5ou4grada3guard5gui5t2g5y3nh3ab4lhala3mhan4cihan4cy5hand_hang5ohan4teha3ranha5rashard3ehar4lehe4canh5ecathe5do5he3l4ihel4lyhen5athera3pher4bahere5ah5erouhe2s5phet4edhimer4hion4ehis3elhlo3rih5odizhol5ar3hol4ehor5atho5rishort3eho5senhouse3hov5elhro3pohu4minhun5kehus3t4h4wart4ian4ti4ativib3eraib5ertib5it_ib5itei2b5rii4car_i4caraic5inaic3ipai2c5ocic3ulaid5ancide3alid5ianidi4aridi5ou5ie5gaien5a4i3entiif5eroiff5en4ific_ig3eraight3iil3a4bi4ladei2l5amila5rail4istill5abim3ageima5ryim5idaimi5lei5miniim3ulai4n3auincel4in3ceri5nessin5genin3ityi4no4c2in4thion3atip4re4iq5uefiq3uidire4dei4rel4iri5deiri3tuir4min5iron_is5hanis3honish5opislan4is4salissen4is4sesis4ta_ist4lyita4bi4ita5mit3erai5teri4i2ticit3icait5illi4tismi4tramit3uativ3elliv3en_iv5il_i5vorei4v3ot5izont4jestyk3en4dk3est_kin4delab3iclan4dllan5etlan4tela5tan4lativla4v4ald4ereld4erile4mat5lene_lera5b3l4erile5sco5less_li4ato5licioli4cor4lict_lid5erlif3erli4gra4l4i4llim4bll4im4p1l4inelin3ealiv3erl3le4nl3le4tl2lin4l5linall5outlm3inglob5al3logiclom3er5lope_lo5rielor5oulos5etloun5dlp5ingltane5ltera4ltur3al5umn_lus3tel5vet4mag5inma3ligma5linmal4limal4ty5maniaman5isman3izma5rizmar4lyma5scema3tismba4t55mediame3diem5e5dymel5onmem1o3men5acmen4demensu5men4tem5ersa3mestimet3alme5thime3try3miliam5ineem4inglmis4timma5rymoi5semon5etmon5gemoni3amo3nizmonol4mo3ny_4mora_mo5seympara5mpar5imphas4mp5iesm4p1inmpo3rim4pousmulti32n1a2bna5liana5mitnanci4nan4itnas5tina3talnau3sen4ces_n5cheon5chiln3chisn5d2ifne4gatnel5iznera5bn4erarn4er5i3neticn5geren3gerini3miz5nine_nis4ta3nition3itorn5keronni3alno3ble4n3o2dnois5ino5l4i3nomicnon4agn5oniznor5abnpre4cnsati4n4s3esnter3snti4ern3tinentu3menuf4fe3nu3itoast5eob3a3bob5ingo3cheto4clamoc3rac5ocritoc3ulao5cureod5dedof5iteofit4to4gatoo5gene1o1giso5g2ly3ognizoic3esoi3deroi5letoi5sonoi3terolass4o3lesco3liceol5id_o3li4fol3ingo5lis_ol3isho5liteolli4eol3umeom3enaom3ic_om3icao5miniomo4geompro53oncilon5eston3keyon4odion3omyonspi4onten4on3t4iontif53operao5phano5pherop3ingo4posio4r3ago5realore5sh4o5riaor3icaor3ityor3ougors5enor3thior3thyo3scopos4i4eos3itoos3ityos5tilos5titot3er_ot5ersoth3i4ot3ic_ot5icao3ticeouch5iover3sov4ertoviti4o5v4olow3derow5est5paganp3agatpan3elpan4typar5dipar5elp4a4ripar4ispa5terpa5thypear4lpedia4ped4icpeli4epe4nanpen4thp4era_p4eragperme5per3tipe5tenpe5tizphar5iphe3noph4es_ph5ing3phone5phonipi4ciepi5thaplas5tpli5erplum4bpo3et55pointpoly5tppa5rapray4e5precipre5copre3empre4lap3rese3press5pri4epris3op3rocapros3ept5a4bput3errach4eraf5firam3etrane5oran4gerap3er3raphyrar5ef4rarilra5vairav3elra5zier5binerch4err4ci4brdi4errd3ingre5arrre4crere3disred5itre4facreg3isren4tere5pinre4spire3strre4terre3trire5utire4valrev3elre5vilrg3ingric5as5ricidri4cierid5erri3encri3entrig5anril3iz5rimanrim4pe5rina_riph5erit3icrit5urriv5elriv3etrk4linrl5ishrm5ersrm3ingr1nis4ro5filro5ker5role_ron4alron4taro3pelrop3icro4therov5elr5pentrp5er_rp3ingrre4strsa5tirse4crrs5er_rse5v2r4si4brtach4rten4dr4tierrtil3irtil4lr4tilyr4tistru3e4lrum3plrun4tyruti5nrvel4irv5er_r5vest5ryngesac3risalar4san4desa5vor3s4cie4scopyse2c3ose4d4ese4molsen5ats5eneds5enin4sentd4sentlsep3a34s1er_4servo5se5umsev3ensh5oldshort53side_5sidessi5diz4signa5sine_sion5a3sitiosk5inesk5ingslith5small35smithso4labsol3d2so3lic3s4on_s5ophyspen4d2s5peo3sphersp5ings5sengs4ses_ssi4erss5ilyssur5astam4i5stands4ta4p5stat_s5terostew5a5stickst3ing5stockstom3a5stone3stores4trads4trays4tridsy5rintai5lotal5enta5logtan4detanta3ta5perta3riz4taticta4turtax4istch5ettead4ite5gerte2ma2tem3at3tenan4tenes5ter3dter3ist3ess_teth5eth3easthe5atthe3isth5ic_th5ica5thinkth5odeti4atot4ic1utim5ul3tine_ti3zen3tles_t5let_to3natto3rietor5izto3wartra5chtraci4trem5i4tricstro5mitron5i4tronytro3sptu4nis2t3up_tur3isu4berou3ble_ud5estud3iedud3iesuen4teuer4ilugh3enuil5izu5lati5ulcheul3derul3ingul5ishul4larul4lisuls5esultra3um4blyumor5oun5ishunt3abun4tesuper5sup3ingupt5ibure5atur4ferurs5erur5tesur3theur4tieus4linuten4i4u1t2iu3tineut3ing5u5tiz2v1a4bvac5ilva5lieva5nizvel3liven3omv5enue5vere_v4erelv3erenv4eresver3ie3versever3thves4tevet3ervi5ali5vide_5vided5vides5vilit4vi4nav3io4rvis3itvor5ab4voteewa5gerwa5verweath3win4dewo5venwrita4xi5mizxpan4dymbol5yn3chryo5netys3icay3thin',
		7 : '_ad4der_anti5s_ar4tie_aster5_be5sto_but4ti_cam4pe_capa5b_car5ol_de4moi_earth5_gen3t4_hand5i_hero5i_hon5ey_im5pin_lat5er_mag5a5_mar5ti_me5ter_mist5i_muta5b_or5ato_ped5al_pe5tit_re5mit_se5rie_sta5bl_ten5an_tim5o5_under5_ven4dea4lenti5a5lysta4matisa4m5atoan5est_a4pillaar5adisa5ratioar5ativar4chanar5dinear5inat5a5si4ta5ternaat5omizbad5gerban5dagbina5r43bi3tio3bit5uabuf4fercall5incast5ercas5tigccompa55chanic5chine_5cific_5cratic4c3retacul4tiscur5a4b4c5utivdel5i5qdem5ic_de4monsdenti5fdern5izdi4latodrag5on5drupliec5essaec5ifiee4compee4f3ereefor5ese4fuse_el5ativel5ebrae4l5ic_el5igibe4l3ingem5igraem3i3niemoni5oench4erent5age4enthesep5recaep5ti5b4erati_er5encee4sage_e4sagese4sert_e4sertse4servaes5idenes5ignaesis4tees5piraes4si4bestruc5e5titioet5itiv4f3ical4ficatefill5ingani5za4g3o3na5graph_4graphy4gress_hang5erh5a5nizharp5enhar5terhel4lishith5erhro5niziam5eteia4tricic4t3uainer4ari5nite_5initioinsur5aion4eryiphras4iq3ui3t5i5r2izis5itiviso5mer4istral5i5ticki2t5o5mi4v3er_i4vers_iv3o3ro4jestiek5iness4latelilev4er_lev4eralev4ersliar5iz5ligatelink5er5liticalloqui5l3o3nizlo4ratol5ties_5lumnia4matizam4b3ing5metricme5triem5i5liemin5glim5inglymis4er_m5istrymo5lestmon4ismmon4istmpa5rabmula5r4nag5er_ncour5and5est_nge4n4en5o5mizno4rarynov3el3nsta5bln4t3ingo5a5lesoctor5aod5uct_od5uctso2g5a5rog5ativoint5eroist5eno5litiool5ogizom5atizom5erseom5etry5ommend4operagor5alizor5angeor5est_4oscopios5itivo5statiotele4goth5esiounc5erover4nepara5blpar5age5pathicpa4tricpera5blperi5stper4mal5phistipi4grappref5acpre5tenprin4t3prof5itput4tedput4tinration4rb5ing_r5ebratrec5ollre5fer_r4en4tare4posiress5ibre5stalre4ti4zre5versre5vertrev5olurip5licri3ta3br5ited_rit5er_rit5ersr4ming_rom5etero5n4isros5perrtroph45sa3tioscan4t55scin4dscour5asmol5d45sophics5ophizsqual4lsspend4stern5i5stratuta5blestal4listen4tagter5iesteri5za5ternit5thodicthor5ittho5riztill5intion5eeto5cratton4alitrac4ittrac4tetra5ventri5ces5triciatro5pheuar5antu4b5inguiv4er_ul4li4bu4m3ingun4ter_upport5uri4ficus5tereuti5lizution5avar5iedver5encvermi4n4v3idenv3i3lizwea5riewill5inxe4cutoxpecto5ylla5bl',
		8 : '_chill5i_cor5ner_dictio5_eq5ui5t_for5mer_re5stat_trib5utab5it5abab5o5lizap5illara5rameteation5arces5si5bch5a5nisch5inesse4q3ui3sg5rapher5graphicimenta5rin5dlingin5glinglem5aticl5i5tics5losophyma5chinema5rine_mpos5itenato5mizneg5ativni5ficat5nologisntrol5lioc5ratizonspir5appo5siterec5omper5ev5er_5taboliz5tisticatrav5es5url5ing_',
		9 : '_ratio5nac5laratioec5ificatef5i5niteep5etitio5losophiz5mocratiz5nop5o5liuto5matic'
	}
};

Hyphenator.config({
	displaytogglebox : true,
	remoteloading : false
});

Hyphenator.run();
