import unittest

import config
from fpgen import Book
from fpgen import userOptions

class TestBookVarious(unittest.TestCase):
  def setUp(self):
    self.book = Book(None, None, 0, 't')

  def tearDown(self):
    config.uopt = userOptions()

  # Test the method Book.parseVersion
  def test_book_version(self):
    major, minor, letter = Book.parseVersion("4.55d")
    self.assertEqual(major, "4")
    self.assertEqual(minor, "55")
    self.assertEqual(letter, "d")

  def test_book_version_noletter(self):
    major, minor, letter = Book.parseVersion("4.55")
    self.assertEqual(major, "4")
    self.assertEqual(minor, "55")
    self.assertEqual(letter, "")

  def test_book_version_check_equal(self):
    self.book.umeta.add("generator", "4.55a")
    config.VERSION = "4.55a"
    self.book.versionCheck()

  def test_book_version_check_more_letter(self):
    self.book.umeta.add("generator", "4.55a")
    config.VERSION = "4.55f"
    self.book.versionCheck()

  def test_book_version_check_less_letter(self):
    self.book.umeta.add("generator", "4.55f")
    config.VERSION = "4.55a"
    with self.assertRaises(SystemExit) as cm:
      self.book.versionCheck()
    self.assertEqual(cm.exception.code, 1)

  def test_book_version_check_more_minor(self):
    self.book.umeta.add("generator", "4.54")
    config.VERSION = "4.56"
    self.book.versionCheck()

  def test_book_version_check_less_minor(self):
    self.book.umeta.add("generator", "4.55")
    config.VERSION = "4.54a"
    with self.assertRaises(SystemExit) as cm:
      self.book.versionCheck()
    self.assertEqual(cm.exception.code, 1)
