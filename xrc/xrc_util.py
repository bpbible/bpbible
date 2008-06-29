"""This module contains utility functions for working with XRC files."""
import wx

def attach_unknown_control(control_name, control, parent):
	"""This function is a wrapper around XMLResource.AttachUnknownControl.

	It will create the new control if necessary, then attach it to the given
	unknown control with the given name, and it will also store the created
	control in that attribute of the parent.

	control_name: The name of the control in the XRC file.
	control: Either the control to attach or a function to create it.
		If this is callable, then it will be called with its parent.
	parent: The parent window or dialog that the XRC file is for.
	"""
	if callable(control):
		actual_control = control(parent)
	else:
		actual_control = control
	wx.xrc.XmlResource.Get().AttachUnknownControl(
			control_name, actual_control, parent)
	parent.GetSizer().Fit(parent)
	setattr(parent, control_name, actual_control)
