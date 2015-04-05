#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re, sys, string
import config
import unittest

from parse import parseTagAttributes, parseOption, parseLineEntry
from msgs import dprint, fatal, cprint

# The Template class represents a single template.
# The TemplatesOneType class represents a set of named templates of a given type
# There are currently two types of template, "chapter" and "macro"
# The Templates class handles all the templates, it maintains a set of sets of
# templates, i.e. a set of types of templates (or a set of named TemplatesOneType objects)
class Template(object):
  def __init__(self, source):
    self.source = source
    self.globals = None

  def setGlobals(self, globals):
    self.globals = globals

  def expand(self, keys):
    lines = self.source[:]
    self.expandConditions(keys, lines)
    self.expandExpand(keys, lines)

    return lines

  def expandConditions(self, keys, lines):
    regExpand = re.compile("<expand-if\s+(.*?)>(.*?)</expand-if>")
    for i, l in enumerate(lines):
      while True:
        m = regExpand.search(l)
        if not m:
          break
        keyword = m.group(1)
        if keyword in keys:
          # Yes, defined, include
          code = m.group(2)
        else:
          code = ''
        l = l[0:m.start(0)] + code + l[m.end(0):]
        lines[i] = l

  def expandExpand(self, keys, lines):
    regExpand = re.compile("<expand\s+(.*?)/?>")
    for i, l in enumerate(lines):
      while True:
        m = regExpand.search(l)
        if not m:
          break
        keyword = m.group(1)
        if keyword in keys:
          value = keys[keyword]
        else:
          if self.globals is None or not keyword in self.globals:
            msg = "  Keywords: "
            for i, k in enumerate(keys):
              if i != 0:
                msg += ", "
              msg += k
            if not self.globals is None:
              msg += "\n  Global Keywords: "
              for i, k in enumerate(self.globals):
                if i != 0:
                  msg += ", "
                msg += k
            raise Exception("Template <expand> unknown variable " + keyword + \
                ".  Line: " + l + "\nLegal keywords at this point are:\n" +
                msg)
          value = self.globals[keyword]

        l = l[0:m.start(0)] + value + l[m.end(0):]
        lines[i] = l

class TemplatesOneType(object):
  def __init__(self):
    self.templates = {}

  def __iter__(self):
    return self.templates.__iter__()

  def add(self, name, template):
    self.templates[name] = template

  def get(self, name):
    if not name in self.templates:
      raise Exception("Template " + name + " not found")
    return self.templates[name]

class Templates(object):
  def __init__(self):
    self.byType = {}
    for type in templateTypes:
      self.byType[type] = TemplatesOneType()

  def createTemplate(self, source):
    return Template(source)

  def add(self, type, name, source):
    if not type in self.byType:
      raise Exception("Adding template of unknown type: " + type)
    template = self.createTemplate(source)
    s = self.byType[type]
    s.add(name, template)

  def get(self, types, name):
    for i, type in enumerate(types):
      if not type in self.byType:
        raise Exception("Unknown template type: " + type)
      t = self.byType[type]
      if not name in t:
        if i+1 < len(type):
          continue
        raise Exception("No template of type " + type + " with name " + name)
      template = t.get(name)
      template.setGlobals(self.globals)
      return template
    raise Exception("No template of types " + str(types) + " with name " + name)

  def setGlobals(self, dict):
    self.globals = dict

  # Called from parseStandaloneTagBlock with a template definition
  def defineTemplate(self, opts, block):
    attributes = parseTagAttributes("template", opts, [ "name", "type" ])
    if not "name" in attributes or not "type" in attributes:
      fatal("Template definition requires both name and type attributes: " + opts)
    name = attributes["name"]
    type = attributes["type"]
    dprint(1, "defining template name " + name + " of type " + type + ": " + str(block))
    self.add(type, name, block)
    return []

  # Apply our chapter templates to the given list of lines.
  # The list is modified in-place.
  # Use properties to decide which template to use.
  # Use meta as global variables.
  def chapterTemplates(self, lines, properties, meta):

    # Figure out what template name to use.
    if "template-chapter" in properties:
      chapterTemplateName = properties["template-chapter"]
    else:
      chapterTemplateName = "default"
    if "template-chapter-first" in properties:
      chapterTemplateNameFirst = properties["template-chapter-first"]
    else:
      chapterTemplateNameFirst = "default-first"

    dprint(1, "Chapter Template: Using first: " + chapterTemplateNameFirst + \
        ", subsequent: " + chapterTemplateName)

    # Now we can set the globals, since we have now extracted all the metadata
    self.setGlobals(meta)

    # Figure out which templates we are going to use.
    tFirst = self.get([ "chapter" ], chapterTemplateNameFirst)
    t = self.get([ "chapter" ], chapterTemplateName)

    regexMacro = re.compile("<expand-macro\s+(.*?)/?>")
    i = 0
    first = True
    while i < len(lines):
      line = lines[i]
      if line.startswith("<chap-head"):
        keys = {}
        opts, keys["chap-head"] = parseLineEntry("chap-head", line)
        j = i+1
        while j < len(lines) and re.match(lines[j], "^\s*$"):
          j += 1
        if j == len(lines):
          fatal("End of file after <chap-head>")
        if opts !=  "":
          attributes = parseTagAttributes("chap-head", opts, [ "vars" ])
          dprint(1, "<chap-head> attributes: " + str(attributes))
          if "vars" in attributes:
            vars = parseOption("chap-head", attributes["vars"])
            dprint(1, "<chap-head> vars: " + str(vars))
            keys.update(vars)

        line = lines[j]
        if line.startswith("<sub-head"):
          opts, keys["sub-head"] = parseLineEntry("sub-head", line)
        else:
          # Do not eat this line!
          j -= 1

        # If the first we've seen, it starts the book
        if first:
          templ = tFirst
          first = False
        else:
          templ = t

        dprint(1, "expand keys: " + str(keys))
        replacement = templ.expand(keys)
        dprint(2, "replace " + str(lines[i:j+1]) + " with " + str(replacement))
        lines[i:j+1] = replacement
        i += len(replacement)
        continue

      if line.startswith("<sub-head>"):
        fatal("Found <sub-head> not after a <chap-head>: " + line)

      # What about multiple macro expansions on a line?  Or recursion?
      # Make it simpler for now by just punting: if you expand, then we move on
      # to the next line.
      m = regexMacro.search(line)
      if m:
        opts = m.group(1)
        attributes = parseTagAttributes("expand-macro", opts, [ "name", "vars" ])
        if not "name" in attributes:
          fatal("expand-macro: No macro name given: " + line)
        template = self.get([ "macro" ], attributes["name"])
        if "vars" in attributes:
          keys = parseOption("expand-macro", attributes["vars"])
        else:
          keys = {}
        replacement = template.expand(keys)
        prefix = line[:m.start(0)]
        suffix = line[m.end(0):]

        if len(replacement) == 0:
          # If the template returns nothing, then you end up with a single line of
          # the prefix and suffix around the <expand-macro>
          replacement = [ prefix + suffix ]
        else:
          # Otherwise the prefix goes on the first line; and the suffix at the end of
          # the last; which might be the same single line.
          replacement[0] = prefix + replacement[0]
          replacement[-1] = replacement[-1] + suffix
        lines[i:i+1] = replacement
        i += len(replacement)
        continue

      i += 1

templateTypes = [ "chapter", "macro" ]

builtinText = {
    "default-first": [
      "<l rend='center mt:3em mb:2em fs:2.5em'><expand DC.Title/></l>",
      "<heading level='1'><expand chap-head><expand-if sub-head><br/><expand sub-head></expand-if></heading>",
    ],
    "default": [
      "<heading level='1'><expand chap-head><expand-if sub-head><br/><expand sub-head></expand-if></heading>",
    ],
}

builtinHTML = {
    "default-first": [
      "<l rend='center mt:3em mb:2em fs:2.5em'><expand DC.Title/></l>",
      "<heading nobreak <expand-if id>id='<expand id>' </expand-if><expand-if pn>pn='<expand pn>' </expand-if>level='1'><expand chap-head><expand-if sub-head><br/> <fs:s><expand sub-head></fs></expand-if></heading>"
    ],
    "default": [
      "<heading <expand-if id>id='<expand id>' </expand-if><expand-if pn>pn='<expand pn>' </expand-if>level='1'><expand chap-head><expand-if sub-head><br/> <fs:s><expand sub-head></fs></expand-if></heading>",
    ],
}

def createTemplates(format):
  templates = Templates()

  if format == 't':
    builtin = builtinText
  else:
    builtin = builtinHTML
  for name in builtin:
    templates.add("chapter", name, builtin[name])

  return templates

class TestTemplate(unittest.TestCase):
  def test_e1(self):
    result = Template([ "<expand head>" ]).expand({"head":"xxxyyy"})
    self.assertEqual(result, [ "xxxyyy"])

  def test_e2(self):
    result = Template([ "abc<expand head>def" ]).expand({"head":"xxxyyy"})
    self.assertEqual(result, [ "abcxxxyyydef"])

  def test_e_undef(self):
    with self.assertRaises(Exception):
      Template([ "abc<expand head>def" ]).expand({"xx":"xxxyyy"})

  def test_e_no_key(self):
    with self.assertRaises(Exception):
      Template([ "abc<expand >def" ]).expand({"xx":"xxxyyy"})

  def test_e_global(self):
    t = Template([ "abc<expand xxx>def"])
    t.setGlobals({"xxx":"test"})
    result = t.expand({"def":"xxx"})
    self.assertEqual(result, [ "abctestdef" ])

  def test_e_both(self):
    t = Template([ "abc<expand xxx><expand def>def"])
    t.setGlobals({"xxx":"test"})
    result = t.expand({"def":"xxx"})
    self.assertEqual(result, [ "abctestxxxdef" ])

  def test_e_both1(self):
    t = Template([ "<expand xxx>a<expand def>def"])
    t.setGlobals({"xxx":"test"})
    result = t.expand({"def":"xxx"})
    self.assertEqual(result, [ "testaxxxdef" ])

  def test_if1(self):
    result = Template([ "abc<expand-if xx><expand xx></expand-if>def" ]).expand({"xx":"xxxyyy"})
    self.assertEqual(result, [ "abcxxxyyydef"])

  def test_if2(self):
    result = Template([ "abc<expand-if yy><expand xx></expand-if>def" ]).expand({"xx":"xxxyyy"})
    self.assertEqual(result, [ "abcdef"])

  def test_if_twice(self):
    result = Template([
      "abc<expand-if yy>abc<expand xx></expand-if><expand-if zz><expand zz></expand-if>def"
    ]).expand({"xx":"xxxyyy"})
    self.assertEqual(result, [ "abcdef"])

  def test_if_twice2(self):
    result = Template([
      "abc<expand-if xx>abc<expand xx></expand-if><expand-if zz><expand zz></expand-if>def"
    ]).expand({"xx":"xxxyyy", "zz":"ZedZed"})
    self.assertEqual(result, [ "abcabcxxxyyyZedZeddef"])

  def test_t(self):
    templates = Templates()
    templates.setGlobals({})
    source = [ "l1", "l2" ]
    templates.add("chapter", "thename", source)
    self.assertEqual(templates.get([ "chapter" ], "thename").source, source)

  def test_t_badtype(self):
    templates = Templates()
    templates.setGlobals({})
    source = [ "l1", "l2" ]
    templates.add("chapter", "thename", source)
    with self.assertRaises(Exception):
      templates.get([ "ch" ], "thename")

  def test_t_notfound(self):
    templates = Templates()
    templates.setGlobals({})
    source = [ "l1", "l2" ]
    templates.add("chapter", "thename", source)
    with self.assertRaises(Exception):
      templates.get([ "chapter", "xxx" ])

  def createTemplates(self, source):
    templates = Templates()
    templates.setGlobals({})
    templates.add("chapter", "default-first", source)
    templates.add("chapter", "default", source)
    return templates

  def test_apply(self):
    templates = self.createTemplates([ "t1", "t2", "t3" ])
    lines = [ "l1", "<chap-head>ch</chap-head>", "", "<sub-head>sub</sub-head>", "l2" ]
    templates.chapterTemplates(lines, {}, {})
    self.assertEqual(lines, [ "l1", "t1", "t2", "t3", "l2" ])

  def test_apply_no_sub(self):
    templates = self.createTemplates([ "t1", "t2", "t3" ])
    lines = [ "l1", "<chap-head>ch</chap-head>", "l2" ]
    templates.chapterTemplates(lines, {}, {})
    self.assertEqual(lines, [ "l1", "t1", "t2", "t3", "l2" ])

  def test_apply_ex(self):
    templates = self.createTemplates(["t1", "<expand chap-head>", "<expand sub-head>", "t3"])
    lines = [ "l1", "<chap-head>ch</chap-head>", "", "<sub-head>sub</sub-head>", "l2" ]
    templates.chapterTemplates(lines, {}, {})
    self.assertEqual(lines, [ "l1", "t1", "ch", "sub", "t3", "l2" ])

  def test_apply_ex_global(self):
    templates = self.createTemplates(["t1", "<expand DC.Title>", "<expand sub-head>", "t3"])
    lines = [ "l1", "<chap-head>ch</chap-head>", "", "<sub-head>sub</sub-head>", "l2" ]
    templates.chapterTemplates(lines, {}, {"DC.Title":"title"})
    self.assertEqual(lines, [ "l1", "t1", "title", "sub", "t3", "l2" ])

  def test_apply_no_sub(self):
    templates = self.createTemplates(["t1", "<expand sub-head>", "t3"])
    lines = [ "l1", "<sub-head>sub</sub-head>", "l2" ]
    with self.assertRaises(SystemExit):
      # Found <sub-head> not after <chap-head>
      templates.chapterTemplates(lines, {}, {})

  def test_apply_bad_head(self):
    templates = self.createTemplates(["t1", "<expand chap-head>", "<expand sub-head>", "t3"])
    lines = [ "l1", "<chap-head>ch</chap-head", "", "<sub-head>sub</sub-head>", "l2" ]
    with self.assertRaises(SystemExit):
      # Incorrect line
      templates.chapterTemplates(lines, {}, {})

  def test_apply_vars(self):
    templates = self.createTemplates([
      "t1", "<expand chap-head><expand v1>", "<expand v2><expand sub-head>", "t3"
    ])
    lines = [
      "l1",
      "<chap-head vars='v1:a v2:b'>ch</chap-head>",
      "",
      "<sub-head>sub</sub-head>",
      "l2"
    ]
    templates.chapterTemplates(lines, {}, {})
    self.assertEqual(lines, [ "l1", "t1", "cha", "bsub", "t3", "l2" ])

  def test_define(self):
    templates = self.createTemplates([])
    templates.defineTemplate("name='default-first' type='chapter'", [ "template1", "template2" ])
    lines = [ "l1", "<chap-head>ch</chap-head>", "", "<sub-head>sub</sub-head>", "l2" ]
    templates.chapterTemplates(lines, {}, {})
    self.assertEqual(lines, [ "l1", "template1", "template2", "l2" ])

  def test_define_bad(self):
    templates = self.createTemplates([])
    with self.assertRaises(SystemExit):
      # Keyword XXXname: Unknown keyword...
      templates.defineTemplate("XXXname='default-first' type='chapter'", [ "template1" ])

  def test_define_bad2(self):
    templates = self.createTemplates([])
    with self.assertRaises(SystemExit):
      # Template definition requires both name and type attributes
      templates.defineTemplate("type='chapter'", [ "template1" ])

  def test_define_bad3(self):
    templates = self.createTemplates([])
    with self.assertRaises(SystemExit):
      # Template definition requires both name and type attributes
      templates.defineTemplate("name='default-first'", [ "template1" ])

  def test_define_macro_bad1(self):
    templates = self.createTemplates([])
    with self.assertRaises(SystemExit):
      # No macro name given
      templates.chapterTemplates([ "<expand-macro >" ], {}, {})

  def test_define_macro_bad2(self):
    templates = self.createTemplates([])
    with self.assertRaises(Exception):
      # No template of types ['macro'] with name abc
      templates.chapterTemplates([ "<expand-macro name='abc'>" ], {}, {})

  def test_define_macro_1(self):
    templates = self.createTemplates([])
    templates.defineTemplate("name='m1' type='macro'", [ "template1", "template2" ])
    lines = [ "l1", "<expand-macro name='m1'>", "l2" ]
    templates.chapterTemplates(lines, {}, {})
    self.assertEqual(lines, [ "l1", "template1", "template2", "l2" ])

  def test_define_macro_prefix(self):
    templates = self.createTemplates([])
    templates.defineTemplate("name='m1' type='macro'", [ "template1", "template2" ])
    lines = [ "l1", "prefix<expand-macro name='m1'>", "l2" ]
    templates.chapterTemplates(lines, {}, {})
    self.assertEqual(lines, [ "l1", "prefixtemplate1", "template2", "l2" ])

  def test_define_macro_suffix(self):
    templates = self.createTemplates([])
    templates.defineTemplate("name='m1' type='macro'", [ "template1", "template2" ])
    lines = [ "l1", "<expand-macro name='m1'>suffix", "l2" ]
    templates.chapterTemplates(lines, {}, {})
    self.assertEqual(lines, [ "l1", "template1", "template2suffix", "l2" ])

  def test_define_macro_both(self):
    templates = self.createTemplates([])
    templates.defineTemplate("name='m1' type='macro'", [ "template1", "template2" ])
    lines = [ "l1", "prefix<expand-macro name='m1'>suffix", "l2" ]
    templates.chapterTemplates(lines, {}, {})
    self.assertEqual(lines, [ "l1", "prefixtemplate1", "template2suffix", "l2" ])

  def test_define_macro_empty(self):
    templates = self.createTemplates([])
    templates.defineTemplate("name='m1' type='macro'", [ ])
    lines = [ "l1", "prefix<expand-macro name='m1'>suffix", "l2" ]
    templates.chapterTemplates(lines, {}, {})
    self.assertEqual(lines, [ "l1", "prefixsuffix", "l2" ])

  def test_define_macro_vars(self):
    templates = self.createTemplates([])
    templates.defineTemplate("name='m1' type='macro'", [ "temp<expand v1>", "template2" ])
    lines = [ "l1", "<expand-macro name='m1' vars='v1:vee-one'>", "l2" ]
    templates.chapterTemplates(lines, {}, {})
    self.assertEqual(lines, [ "l1", "tempvee-one", "template2", "l2" ])

  def test_define_macro_vars_if(self):
    templates = self.createTemplates([])
    templates.defineTemplate("name='m1' type='macro'", [ "temp<expand-if v1><expand v1></expand-if>", "tem<expand-if v2>vee-two</expand-if>plate2" ])
    lines = [ "l1", "<expand-macro name='m1' vars='v1:vee-one'>", "l2" ]
    templates.chapterTemplates(lines, {}, {})
    self.assertEqual(lines, [ "l1", "tempvee-one", "template2", "l2" ])
