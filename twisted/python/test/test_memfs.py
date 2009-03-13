
"""
This module contains tests for L{twisted.python.memfs}.

Since the filesystem in L{twisted.python.memfs} is designed to replicate the
behavior of the 'real' filesystem, many of these tests are written in a style
where they verify the same behavior on both interfaces, and run against both
interfaces, to make it easy to verify that the in-memory implementation is
behaving the same as the real implementation.
"""

import sys
import os

from twisted.trial.unittest import TestCase

from twisted.python.memfs import SEEK_SET, SEEK_CUR, SEEK_END, POSIXFilesystem


class FileTestsMixin:
    """
    Tests for an object like L{file}.
    """

    def open(self, name, mode):
        """
        Return a file-like object to be tested.
        """
        raise NotImplementedError("%s did not implement open" % (self,))


    def fsync(self, fd):
        """
        Call the appropriate fsync implementation on the given file descriptor.
        """
        raise NotImplementedError("%s did not implement fsync" % (self,))


    def rename(self, oldname, newname):
        """
        Call the appropriate rename implementation with the given parameters.
        """
        raise NotImplementedError("%s did not implement rename" % (self,))


    def test_fileno(self):
        """
        C{fileno} returns an integer value unique among open files.
        """
        first = self.open("foo", "w")
        self.addCleanup(first.close)

        self.assertTrue(isinstance(first.fileno(), int))
        second = self.open("bar", "w")
        self.addCleanup(second.close)

        self.assertTrue(isinstance(first.fileno(), int))
        self.assertNotEqual(first.fileno(), second.fileno())


    def test_closed(self):
        """
        C{fileno}, C{write}, C{read}, C{tell}, and C{flush} raise L{ValueError}
        when called on a closed file.  C{fsync} raises L{OSerror}.  C{close}
        does nothing.
        """
        fObj = self.open("foo", "w")
        fd = fObj.fileno()
        fObj.close()
        self.assertRaises(ValueError, fObj.fileno)
        self.assertRaises(ValueError, fObj.write, '')
        self.assertRaises(ValueError, fObj.read)
        self.assertRaises(ValueError, fObj.flush)
        self.assertRaises(ValueError, fObj.tell)
        self.assertRaises(OSError, self.fsync, fd)
        fObj.close()


    def test_closedFlag(self):
        """
        The L{closed} attribute on an open file is L{False}; on a closed file
        it is L{True}.
        """
        fObj = self.open("foo", "w")
        self.assertEqual(fObj.closed, False)
        fObj.close()
        self.assertEqual(fObj.closed, True)


    def test_write(self):
        """
        C{write} adds bytes to a file.
        """
        outfile = self.open("foo", "w")
        self.addCleanup(outfile.close)

        infile = self.open("foo", "r")
        self.addCleanup(infile.close)

        # A boring write at the beginning of the file puts the bytes at the
        # beginning of the file.
        outfile.write("hello")
        outfile.flush()
        self.assertEqual(infile.read(), "hello")

        # A write somewhere in the middle of the file overwrites some of the
        # file.
        outfile.seek(3)
        outfile.write("world")
        outfile.flush()
        infile.seek(0)
        self.assertEqual(infile.read(), "helworld")

        # A write exactly at the end of the file appends the given bytes to the
        # file.
        outfile.seek(8)
        outfile.write(".")
        outfile.flush()
        infile.seek(0)
        self.assertEqual(infile.read(), "helworld.")

        # A write past the end of the file inserts 0s to fill the gap and
        # appends the given bytes.
        outfile.seek(11)
        outfile.write("zoop")
        outfile.flush()
        infile.seek(0)
        self.assertEqual(infile.read(), "helworld.\0\0zoop")


    def test_writeSeekRead(self):
        """
        If you write some bytes, then seek back to their beginning, then read
        them, you will get them back.
        """
        outfile = self.open("out", "w+")
        outfile.write("foobar")
        outfile.seek(3)
        self.assertEqual(outfile.read(), "bar")


    def test_read(self):
        """
        C{read} with no arguments returns the entire current contents of a
        file.
        """
        bytes = "bytes"
        outfile = self.open("out", "w")
        outfile.write(bytes)
        outfile.close()

        infile = self.open("out", "r")
        self.addCleanup(infile.close)

        self.assertEqual(infile.read(), bytes)

        infile.seek(1)
        self.assertEqual(infile.read(), bytes[1:])

        infile.seek(1)
        self.assertEqual(infile.read(1), bytes[1])

        infile.seek(1)
        self.assertEqual(infile.read(-3), bytes[1:])

        infile.seek(1)
        self.assertEqual(infile.read(0), '')


    def test_consecutiveReads(self):
        """
        Consecutive limited-length reads from a file should result in portions
        of its contents being returned, and advance the file position.
        """
        f = self.open("out", "w")
        f.write("abcdefg")
        f.close()
        f2 = self.open("out", "r")
        self.assertEqual(f2.read(2), "ab")
        self.assertEqual(f2.tell(), 2)
        self.assertEqual(f2.read(2), "cd")
        self.assertEqual(f2.tell(), 4)
        self.assertEqual(f2.read(2), "ef")
        self.assertEqual(f2.tell(), 6)
        self.assertEqual(f2.read(2), "g")
        self.assertEqual(f2.tell(), 7)
        self.assertEqual(f2.read(2), "")


    def test_flush(self):
        """
        Data written to a file before a call to C{flush} is visible to another
        file object which refers to the same file.
        """
        bytes = "bytes"
        outfile = self.open("out", "w")
        self.addCleanup(outfile.close)

        outfile.write(bytes)
        outfile.flush()
        infile = self.open("out", "r")
        self.addCleanup(infile.close)
        self.assertEqual(bytes, infile.read())


    def test_tell(self):
        """
        The C{tell} method returns the current file position.
        """
        fObj = self.open("foo", "w")
        fObj.write("hello")
        self.assertEqual(fObj.tell(), 5)
        fObj.write("world")
        self.assertEqual(fObj.tell(), 10)


    def test_seek(self):
        """
        The C{seek} method changes the current file position to the specified
        value.
        """
        fObj = self.open("foo", "w")
        fObj.write("hello")
        fObj.seek(1)
        self.assertEqual(fObj.tell(), 1)
        fObj.seek(2)
        self.assertEqual(fObj.tell(), 2)
        fObj.seek(3, SEEK_SET)
        self.assertEqual(fObj.tell(), 3)
        fObj.seek(1, SEEK_CUR)
        self.assertEqual(fObj.tell(), 4)
        fObj.seek(1, SEEK_END)
        self.assertEqual(fObj.tell(), 6)


    def test_seekFlushes(self):
        """
        Using the C{seek} method also flushes the contents of the application
        buffer.
        """
        writer = self.open("foo", "w")
        self.addCleanup(writer.close)

        reader = self.open("foo", "r")
        self.addCleanup(reader.close)

        writer.write("foo")

        # Sanity check
        self.assertEqual(reader.read(), "")

        # Seek, causing a flush, causing the bytes to be visible elsewhere.
        writer.seek(0)
        self.assertEqual(reader.read(), "foo")


    def test_rename(self):
        """
        The C{rename} method changes the name by which a file is accessible.
        """
        fObj = self.open("foo", "w")
        fObj.write("bytes")
        fObj.close()
        self.rename("foo", "bar")
        fObj = self.open("bar", "r")
        self.addCleanup(fObj.close)
        self.assertEqual(fObj.read(), "bytes")



class RealFileTests(TestCase, FileTestsMixin):
    """
    This implements FileTestsMixin to test Python's built-in implementation of
    the 'file' type, so that we can verify the behavior of alternate
    implementations is similar.
    """

    def setUp(self):
        """
        Create a temporary directory to house this test's files.
        """
        self.base = self.mktemp()
        os.makedirs(self.base)


    def localFilename(self, name):
        """
        Make a given file-name relative to the base temporary location for this
        test, so that we can test the real filesystem without going outside our
        directory.
        """
        return os.path.join(self.base, name)


    def open(self, name, mode):
        """
        Implement L{FileTestsMixin.open} to open a real file with L{file}.
        """
        return file(self.localFilename(name), mode)


    def fsync(self, fd):
        """
        Implement L{FileTestsMixin.fsync} to call L{os.fsync} and thereby
        really sync data to disk.
        """
        return os.fsync(fd)


    def rename(self, oldname, newname):
        """
        Implement L{FileTestsMixin.rename} to call L{os.rename} on C{oldname}
        and C{newname}, as relative to this test's temporary path.
        """
        return os.rename(
            self.localFilename(oldname), self.localFilename(newname))


    def test_seekFlushes(self):
        """
        Override to set custom attributes.
        """
        # See below.
        FileTestsMixin.test_seekFlushes(self)


    if sys.platform == 'darwin':
        test_seekFlushes.todo = (
            "OS X appears to violate POSIX: seek() does not imply flush()")



class MemoryFilesystemTests(TestCase, FileTestsMixin):
    """
    Test L{POSIXFilesystem} with the tests defined in L{FileTestsMixin}, to
    make sure that it provides parity with Python's built-in filesystem
    operations.
    """

    def setUp(self):
        """
        Set up a L{POSIXFilesystem} to test.
        """
        self.fs = POSIXFilesystem()


    def open(self, name, mode):
        """
        Implement L{FileTestsMixin} with L{POSIXFilesystem.open}, returning a
        L{MemoryFile}.
        """
        return self.fs.open(name, mode)


    def fsync(self, fd):
        """
        Implement L{FileTestsMixin.fsync} with L{POSIXFilesystem.fsync}.
        """
        return self.fs.fsync(fd)


    def rename(self, oldname, newname):
        """
        Implement L{FileTestsMixin.rename} with L{POSIXFilesystem.rename}.
        """
        return self.fs.rename(oldname, newname)


    def test_writeConsistency(self):
        """
        L{POSIXFilesystem.willLoseData} will return True if there is any data
        stored in either stream buffers or filesystem buffers.
        """
        f = self.open("test.txt", "w")
        f.write("some data")
        self.assertEqual(self.fs.willLoseData(), True)
        f.flush()
        self.assertEqual(self.fs.willLoseData(), True)
        self.fsync(f.fileno())
        self.assertEqual(self.fs.willLoseData(), False)
        f.close()
        self.assertEqual(self.fs.willLoseData(), False)


    def test_closeStillInconsistent(self):
        """
        Since C{close} does not imply C{fsync}, closing a file without syncing
        it first will cause L{POSIXFilesystem.willLoseData} to return True.
        """
        f = self.open("test.txt", "w")
        f.write("some data")
        f.close()
        self.assertEqual(self.fs.willLoseData(), True)