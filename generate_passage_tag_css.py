from gui import passage_tag

def main():
	file = open("css/passage_tag.css", "w")
	for colour in range(len(passage_tag.colours)):
		for look in range(len(passage_tag.looks)): 
			generate_passage_tag_css(file, colour, look)

	file.close()

def generate_passage_tag_css(file, colour, look):
	file.write("\n/* Colour = %d, Look = %d. */\n\n" % (colour, look))
	class_name = "passage_tag_%d_%d" % (colour, look)

	look_scheme, look_white_text, border = passage_tag.looks[look]
	colour_id, colour_white_text, default_look = passage_tag.colours[colour]
	white_text = look_white_text and colour_white_text
	_rgbSelectOuter,_rgbSelectInner,_rgbSelectTop, _rgbSelectBottom = passage_tag.get_colours(colour_id, look_scheme)
	border_radius_style = "-moz-border-radius: %dpx;\n" % border
	outer_border_style = "border: %%dpx solid rgb(%d, %d, %d);\n" % _rgbSelectOuter.Get() #((border,) + _rgbSelectOuter.Get())
	inner_border_style = "border: 1px solid rgb(%d, %d, %d);\n" % _rgbSelectInner.Get() #((border,) + _rgbSelectInner.Get())

	# Only use gradients if the colours are different.
	if _rgbSelectTop == _rgbSelectBottom:
		passage_tag_style = "background-color: rgb(%d, %d, %d);\n" % _rgbSelectTop.Get()
		# We get weird artefacts if all the divs are the same colour and we
		# apply rounded corners to them, so we only apply to the outmost one.
		outer_border_style = (outer_border_style % 2) + border_radius_style
		outer_border_style += "padding: 0;\n"
		inner_border_style = "padding: 0;\nborder: 0;\n"
		border_radius_style = ""
	else:
		passage_tag_style = "background-image: -moz-linear-gradient(top center, rgb(%d, %d, %d) 20%%, rgb(%d, %d, %d) 80%%);\n" % (_rgbSelectTop.Get() + _rgbSelectBottom.Get())
		outer_border_style = (outer_border_style % 1) + border_radius_style

	if white_text:
		passage_tag_style += "color: white;\n"

	passage_tag_style += border_radius_style
	outer_border_style += border_radius_style
	inner_border_style += border_radius_style

	file.write("a.passage_tag.%s {\n" % class_name)
	file.write(outer_border_style)
	file.write("}\n")

	file.write("a.passage_tag.%s:before {\n" % class_name)
	file.write(inner_border_style)
	file.write("}\n")

	file.write("a.passage_tag.%s div {\n" % class_name)
	file.write(passage_tag_style)
	file.write("}\n")

if __name__ == "__main__":
	main()
