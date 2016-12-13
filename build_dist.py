#!/usr/bin/env python

#############################################################################
#
# build_dist.py -- Build the pyral distribution package for shipment
#
#############################################################################

import sys, os
import tarfile
import zipfile
import shutil
import re

PACKAGE_NAME = "bldeif"
VERSION = "0.9.1"

BASE_FILES = ['LICENSE',
             'README.txt',
             'config/sample.yml',
             'bldeif_connector'
             ]

TEST_FILES = ['test/test_*.py']


################################################################################

def main(args):

    zipped = make_zipfile(PACKAGE_NAME, VERSION, BASE_FILES)
    print
    zipped

    zf = zipfile.ZipFile(zipped, 'r')
    for info in zf.infolist():
        # print(info.filename, info.date_time, info.file_size, info.compress_size)
        if info.file_size:
            reduction_fraction = float(info.compress_size) / float(info.file_size)
        else:
            reduction_fraction = 0.0
        reduction_pct = int(reduction_fraction * 100)
        print("%-52.52s   %6d (%2d%%)" % (info.filename, info.compress_size, reduction_pct))

    store_packages('dist', [zipped])

################################################################################

def store_packages(subdir, files):
    for file in files:
        if os.path.exists(file):
            shutil.copy(file, '%s/%s' % (subdir, file))
        else:
            problem = "No such file found: {0} to copy into {1}".format(file, subdir)
            sys.stderr.write(problem)

################################################################################

def make_zipfile(pkg_name, pkg_version, base_files):
    base_dir = '%s-%s' % (pkg_name, pkg_version)

    zf_name = '%s.zip' % base_dir

    zf = zipfile.ZipFile(zf_name, 'w')

    for fn in base_files:
        zf.write(fn, '%s/%s' % (base_dir, fn), zipfile.ZIP_DEFLATED)

    for fn in (pf for pf in os.listdir(pkg_name) if pf.endswith('.py')):
        pkg_file = '%s/%s' % (pkg_name, fn)
        zf.write(pkg_file, '%s/%s/%s' % (base_dir, pkg_name, fn), zipfile.ZIP_DEFLATED)

    for fn in (utf for utf in os.listdir('bldeif/utils') if utf.endswith('.py')):
        pkg_file = '%s/utils/%s' % (pkg_name, fn)
        zf.write(pkg_file, '%s/%s/utils/%s' % (base_dir, pkg_name, fn), zipfile.ZIP_DEFLATED)

    zf.close()

    return zf_name




################################################################################
################################################################################

if __name__ == "__main__":
    main(sys.argv[1:])
