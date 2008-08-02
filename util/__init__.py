"""Utility functions."""
import sys

def noop(*args, **kwargs):
	"""Do nothing."""

def is_py2exe():
	return hasattr(sys, "frozen")	
