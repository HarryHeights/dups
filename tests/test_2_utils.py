import context  # noqa: F401, isort:skip

import os
import shutil
from datetime import datetime, timedelta

from dups import utils

import pytest


class Test_gffs:
    def test_rotate_gffs(self):
        start = datetime(2017, 12, 31)

        datetimes = []
        for i in range(1095):
            datetimes.append(start - timedelta(days=i))

        gffs = utils.rotate_gffs(datetimes, start=start)

        assert gffs[0] == [
            datetime(2017, 12, 31),
            datetime(2017, 12, 30),
            datetime(2017, 12, 29),
            datetime(2017, 12, 28),
            datetime(2017, 12, 27),
            datetime(2017, 12, 26),
            datetime(2017, 12, 25),
        ]

        assert gffs[1] == [
            datetime(2017, 12, 24),
            datetime(2017, 12, 17),
            datetime(2017, 12, 10),
            datetime(2017, 12, 3),
        ]

        assert gffs[2] == [
            datetime(2017, 11, 30),
            datetime(2017, 10, 31),
            datetime(2017, 9, 30),
            datetime(2017, 8, 31),
            datetime(2017, 7, 31),
            datetime(2017, 6, 30),
            datetime(2017, 5, 31),
            datetime(2017, 4, 30),
            datetime(2017, 3, 31),
            datetime(2017, 2, 28),
            datetime(2017, 1, 31),
            datetime(2016, 12, 31),
        ]

        assert gffs[3] == [
            datetime(2015, 12, 31),
        ]


class Test_IO:
    def teardown_method(self, method):
        if os.path.exists(context.TMP_DIR):
            shutil.rmtree(context.TMP_DIR)

        if os.path.exists(context.TMP_FILE):
            os.remove(context.TMP_FILE)

    def get_io(self, target):
        if target is 'local':
            return utils.IO.get()
        elif target == 'remote':
            return utils.IO.get(context.SSH_HOST)
        return None

    @pytest.mark.parametrize('target', ['local', 'remote'])
    def test_is_local(self, target):
        io = self.get_io(target)

        if target is 'local':
            assert io.is_local
        elif target is 'remote':
            assert not io.is_local

        io.close()

    def test_validate_absolute(self):
        @utils.validate_absolute
        def test(path):
            pass

        with pytest.raises(ValueError):
            test('.')

    @pytest.mark.parametrize('target', ['local', 'remote'])
    def test_isfile(self, target):
        io = self.get_io(target)

        assert not io.isfile(context.TEST_DIR)
        assert io.isfile(context.TEST_FILE)

        io.close()

    @pytest.mark.parametrize('target', ['local', 'remote'])
    def test_isdir(self, target):
        io = self.get_io(target)

        assert io.isdir(context.TEST_DIR)
        assert not io.isdir(context.TEST_FILE)

        io.close()

    @pytest.mark.parametrize('target', ['local', 'remote'])
    def test_listdir(self, target):
        io = self.get_io(target)

        files = ['dir1', 'dir2', 'file1', 'file2']
        assert len(files) == len(io.listdir(context.TEST_DIR))

        io.close()

    @pytest.mark.parametrize('target', ['local', 'remote'])
    def test_mkdir(self, target):
        io = self.get_io(target)

        io.mkdir(context.TMP_DIR)
        assert os.path.isdir(context.TMP_DIR)

        io.close()

    @pytest.mark.parametrize('target', ['local', 'remote'])
    def test_makedirs(self, target):
        io = self.get_io(target)

        nested = os.path.join(context.TMP_DIR, 'nested', 'dir')

        io.makedirs(nested)
        assert os.path.isdir(nested)

        io.close()

    @pytest.mark.parametrize('target', ['local', 'remote'])
    def test_touch(self, target):
        io = self.get_io(target)

        io.touch(context.TMP_FILE)
        assert os.path.isfile(context.TMP_FILE)

        io.close()

    @pytest.mark.parametrize('target', ['local', 'remote'])
    def test_exists(self, target):
        io = self.get_io(target)

        assert io.exists(context.TEST_FILE)
        assert not io.exists(context.TMP_FILE)

        io.close()

    @pytest.mark.parametrize('target', ['local', 'remote'])
    def test_remove(self, target):
        io = self.get_io(target)

        open(context.TMP_FILE, 'a').close()
        assert os.path.exists(context.TMP_FILE)
        io.remove(context.TMP_FILE)
        assert not os.path.exists(context.TMP_FILE)

        io.close()

    @pytest.mark.parametrize('target', ['local', 'remote'])
    def test_rmdir(self, target):
        io = self.get_io(target)

        os.makedirs(context.TMP_DIR)
        assert os.path.exists(context.TMP_DIR)
        io.rmdir(context.TMP_DIR)
        assert not os.path.exists(context.TMP_DIR)

        io.close()

    @pytest.mark.parametrize('target', ['local', 'remote'])
    def test_rrmdir(self, target):
        io = self.get_io(target)

        nested = os.path.join(context.TMP_DIR, 'nested', 'dir')
        os.makedirs(nested)

        assert os.path.exists(nested)
        io.rrmdir(context.TMP_DIR)
        assert not os.path.exists(context.TMP_DIR)

        io.close()

    @pytest.mark.parametrize('target', ['local', 'remote'])
    def test_open(self, target):
        io = self.get_io(target)

        msg = 'Hello dups!'
        with io.open(context.TMP_FILE, 'w') as f:
            f.write(msg)

        with open(context.TMP_FILE) as f:
            assert msg == f.read()
