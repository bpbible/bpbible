#TODO: on move remove popup
#TODO: \n on copy
#TODO: ($text)$text

#TODO: why don't trailing spaces get preserved between restarts?!?
import wx
import json

from xrc.copyverses_xrc import xrcCopyVerseDialog
from backend.bibleinterface import biblemgr
from backend.verse_template import VerseTemplate, Template
from backend.filterutils import COPY_VERSES_PARSER_MODE, NORMAL_PARSER_MODE
from util import string_util

from wx import stc
from templatemanager import TemplatePanel, TemplateManager
import guiconfig
import config
from gui import guiutil, fonts
from util.configmgr import config_manager
from swlib.pysw import GetBestRange
import display_options

#class CopyVerseDialog(xrcCopyVerseDialog):
#	def __init__(self, parent, settings):
#		super(CopyVerseDialog, self).__init__(parent)
#		self.sizer = wx.BoxSizer(wx.VERTICAL)
#		panel = wx.Panel(self)
#		button_sizer = wx.StdDialogButtonSizer()
#		button_sizer.AddButton(wx.Button(wx.ID_OK))
#		button_sizer.AddButton(wx.Button(wx.ID_CANCEL))
#		button_sizer.Realize()

		
		
class CopyVerseDialog(xrcCopyVerseDialog):
	def __init__(self, parent):
		super(CopyVerseDialog, self).__init__(parent)
		self.tm = TemplateManager(self)
		self.is_custom = False
		self.based_on = ""
		
		# fill up the list of templates
		self.fill_templates()
		
		fields = None

		settings = config_manager["BPBible"]["copy_verse"]

		# if we are a tuple, we represent based_on, fields
		# otherwise we are a template name
		copy_formatted = False
		if isinstance(settings, tuple):
			if len(settings) == 2:
				# old style
				based_on, fields = settings
				self.is_custom = True
			else:
				based_on, fields, copy_formatted = settings
				self.is_custom = fields != None

		else:
			# old style
			based_on = settings

		if self.is_custom:
			self.make_custom(based_on)

		else:
			item_id = 0
			for idx, item in enumerate(self.tm.templates):
				if item.name == based_on:
					item_id = idx
					break

				# remember default, but keep on looking
				if item.name == "Default":
					item_id = idx

			self.tm.change_template(item_id)
			self.gui_template_list.SetStringSelection(
				self.tm.template.name
			)
			
			fields = self.tm.template
			#self.tm.transfer_from_templatemanager(id)
			
				

		# put the template panel in
		self.template_panel = TemplatePanel(self.tp_holder, fields, False)
		self.tp_holder.Sizer.Add(self.template_panel, 1, wx.GROW)
		self.tp_holder.Fit()
		self.tp_holder.Parent.Parent.Label = _("Edit Template...")
		self.Fit()
		self.SetMinSize(self.Size)


		# do binding
		for event in [wx.EVT_KILL_FOCUS, wx.EVT_TEXT_ENTER]:
			self.reference.Bind(event, self.update)

		self.copy_formatted.SetValue(copy_formatted)
		self.copy_formatted.Bind(wx.EVT_CHECKBOX, self.update)

		for item in self.template_panel.fields:
			for event in [wx.EVT_KILL_FOCUS]:#, stc.EVT_STC_MODIFIED]:
				item.Bind(event, self.update)
			item.Bind(stc.EVT_STC_MODIFIED, self.on_text_changed)
			
			colour, text_colour = guiconfig.get_window_colours()
			for style in stc.STC_STYLE_DEFAULT, 0:
				item.StyleSetBackground(style, colour)
				item.StyleSetForeground(style, text_colour)
			
			item.SetCaretForeground(text_colour)

		self.wxID_CANCEL.Bind(wx.EVT_BUTTON, 
					lambda x:self.EndModal(wx.ID_CANCEL))

		self.gui_save_template.Bind(wx.EVT_BUTTON, self.save_template)
		self.gui_load_template.Bind(wx.EVT_BUTTON, self.load_template)
		self.gui_template_list.Bind(wx.EVT_CHOICE, self.on_template_choice)

		self.preview.book = biblemgr.bible
		self.has_preview_been_loaded = False
		
		#self.panel1instructions.Wrap(300)
		#s =self.GetSizer()
		#print self.instructions.GetBestSize(), self.instructions.Size
		#s.Layout()
		#s.RecalcSizes()
		#s.Layout()
		#self.instructions.GetSizer().Layout()
	
	def on_text_changed(self, event):
		# one of our text fields have changed
		# if we are not custom, add a custom item at the end
		event.Skip()
		if self.is_custom:
			return
		
		self.make_custom(self.gui_template_list.StringSelection)
		
	def make_custom(self, based_on):
		self.is_custom = True
		self.based_on = based_on
		self.gui_template_list.Append(
			_("<custom: based on %s>") % self.based_on
		)

	
		self.gui_template_list.SetSelection(self.gui_template_list.Count - 1)
		
	def on_template_choice(self, event):
		selection = event.Selection
		if self.is_custom:
			custom_idx = self.gui_template_list.Count - 1
			# custom one
			if selection == custom_idx:
				return

			# remove the custom one
			self.gui_template_list.Delete(custom_idx)

		event.Skip()
		self.is_custom = False
		self.transfer_from_templatemanager(selection)
		self.update()
		
	
	def load_template(self, event=None):
		was_custom, based_on = self.is_custom, self.based_on

		selection = self.tm.template.name

		ansa = self.tm.ShowModal()
		
		if ansa == wx.ID_OK:
			# transfer the fields across
			self.transfer_from_templatemanager()

			# use the new selection
			selection = self.tm.template.name

		# fill up the list again
		was_selected = self.fill_templates(selection)

		# if we were custom, put ourselves back in proper
		if was_custom and ansa != wx.ID_OK:
			self.make_custom(based_on)
		
		# if the user has deleted the template we were using, make it a custom
		# template based on the original name
		elif not was_selected:
			self.make_custom(selection)

		self.update()
			

	def transfer_from_templatemanager(self, selection=None):
		if selection is not None:
			self.tm.change_template(selection)
		
		self.gui_template_list.SetStringSelection(self.tm.template.name)

		for field in self.template_panel.fields:
			field.set_text(self.tm.template[field.field])
	
	def fill_templates(self, selection=None):
		"""Fill the template choice up with the template names.

		Returns True if selection was found, False otherwise.
		If selection isn't found, first item will be selected"""
		self.gui_template_list.Clear()
		found = False
		for idx, item in enumerate(self.tm.templates):
			self.gui_template_list.Append(item.name)
			if item.name == selection:
				self.gui_template_list.SetSelection(idx)
				found = True
		
		if not found:
			# if not found, select the last item
			self.gui_template_list.SetSelection(0)
		
		return found
		
	def Destroy(self):
		self.tm.Destroy()
		return super(CopyVerseDialog, self).Destroy()
	
	def save_template(self, event=None):
		name = self.tm.template.name
		if self.is_custom:
			name = self.based_on

		template = Template(name=name, readonly=False)
		for field in self.template_panel.fields:
			template[field.field] = field.Text

		if not self.tm.save_template(template):
			return

		self.tm.save()
		self.is_custom = False
		
		self.fill_templates(template.name)

	def get_internal_reference(self):
		return GetBestRange(self.reference.GetValue(), 
				userInput=True, userOutput=False)
		
	def update(self, event=None, ref=None, dialog_hidden_mode=False):
		if not self.has_preview_been_loaded:
			# Have to make sure this doesn't include the placeholder divs and styles,
			# since they cause boxes to appear around the text when pasted into OpenOffice.
			self.preview.SetPage("&nbsp;", include_wrapper_divs=False)
			self.has_preview_been_loaded = True

		if event: 
			event.Skip()

		plain_text = self.GetText(ref or self.get_internal_reference())
		if (not dialog_hidden_mode) or self.formatted:
			text = plain_text
			if not self.formatted: text = text.replace("\n", "<br />")
			self.preview.ExecuteScriptAfterDocumentLoaded(
				"""$("body").html(%s);""" % json.dumps(text))
		return plain_text

	def ShowModal(self, text):
		# set the reference
		self.reference.SetValue(
			GetBestRange(text, userInput=False, userOutput=True)
		)
		
		# update the text
		self.update()

		ansa = super(CopyVerseDialog, self).ShowModal()

		if ansa == wx.ID_OK:
			self.copy_verses(self.get_internal_reference())
			if self.is_custom:
				config_manager["BPBible"]["copy_verse"] = (
					self.based_on, 
					dict(
						header=self.template_panel.header.GetText(),
						body=self.template_panel.body.GetText(), 
						footer=self.template_panel.footer.GetText()
					), self.formatted
				)

			else:
				config_manager["BPBible"]["copy_verse"] = (
					self.gui_template_list.StringSelection
				), None, self.formatted
			

		return ansa

	@property
	def formatted(self):
		return self.copy_formatted.IsChecked()
	
	def copy_verses(self, ref, dialog_hidden_mode=False):
		print "Updating...", ref
		text_to_copy = self.update(ref=ref, dialog_hidden_mode=dialog_hidden_mode)
		if self.formatted:
			self.preview.copyall()
		else:
			guiutil.copy(text_to_copy)

	def GetText(self, ref):
		print "Getting text for", ref
		template = VerseTemplate(header=self.template_panel.header.GetText(),
			body=self.template_panel.body.GetText(), 
			footer=self.template_panel.footer.GetText())

		#no footnotes
		biblemgr.temporary_state(biblemgr.plainstate)
		if display_options.options["colour_speakers"] == "woc_in_red":
			biblemgr.set_option("Words of Christ in Red", "On")

		#apply template
		biblemgr.bible.templatelist.append(template)
		biblemgr.parser_mode = COPY_VERSES_PARSER_MODE
		
		data = biblemgr.bible.GetReference(ref)
		if data is None:
			data = config.MODULE_MISSING_STRING()

		if self.formatted:
			# TODO: make it scan CSS and amalgamate rules?
			data = data.replace("<span class='WoC'>",
								"<span style='color: red'>")
			data = data.replace("<span class='divineName'>",
								"<span style='font-variant:small-caps'>")

			# Use the font that has been selected for the module.
			# XXX: We could still use language specific fonts for particular
			# sections of the text, but I'm not sure it's worth doing.
			# It would probably only apply to Hebrew and Greek (which we
			# treat specially) anyway.
			default, (font, size, in_gui) = fonts.get_module_font_params(biblemgr.bible.mod)
			data = u"<span style=\"font-family: %s; font-size: %spt;\">%s</span>" % (font, size, data)
		else:
			data = string_util.br2nl(data)
			data = string_util.KillTags(data)
			data = string_util.amps_to_unicode(data)

		#restore
		biblemgr.restore_state()
		biblemgr.bible.templatelist.pop()
		biblemgr.parser_mode = NORMAL_PARSER_MODE
		return data

	def safely_destroy_dialog(self):
		"""We need to make sure that the copy has been completed before we destroy the dialog.

		To do this, we make sure of two things:
		1. The HTML preview window has been loaded if we are using it to copy from.
		2. The dialog has been open for a sufficient amount of time to allow the copy to complete.
			This should be a background task that doesn't affect the user (otherwise it sometimes just doesn't copy).
		"""
		if self.formatted:
			self.preview.defer_call_till_document_loaded(lambda cvdpreview: wx.CallLater(5000, self.Destroy))
		else:
			self.Destroy()
	

	#@classmethod
	#def show_dialog(cls, parent=None):
	#	"""Copy verses to other applications"""
	#	if not parent:
	#		parent = guiconfig.mainfrm
	#	return cls(parent).ShowModal()
	
