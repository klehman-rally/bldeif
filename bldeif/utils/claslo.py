# Copyright 2011-2012 Rally Software Development Corp. All Rights Reserved.

import sys, os
import re

class ClassLoader(object):
    """
        An instance of this class is used to locate a specific class definition from
        a module in a pkgdir subdirectory.  If no such pkgdir exists, go though the 
        items in sys.path, appending the pkgdir value to each item in sys.path and
        searching for the specific class definition for each file living in the 
        resultant path directory.  If no such class definition is found, raise an Exception.
        Otherwise, import the module implmented in the file containing the specific 
        class name and then pull out a reference to the class and return it.
    """

    def loadConnectionClass(self, class_name, pkgdir=None):
##
##        print "ClassLoader.loadConnectionClass ... entry point"
##

        def qualified(subdir, item):
            return item.endswith('.py') and os.path.isfile('%s/%s' % (subdir, item))

        pyfiles = [fn for fn in os.listdir(pkgdir) if qualified(pkgdir, fn)]
        module_names = [os.path.splitext(fn)[0] for fn in pyfiles]
##
##        print "ClassLoader.loadConnectionClass ..  module_names: %s" % repr(module_names)
##
        target_classes_found = 0
        tc_module = {}  # target class module lookup dict
        # look in all modules, record the module name if the class_name is defined in there
        for module_name in module_names:
            module_file = '%s/%s.py' % (pkgdir, module_name)
    
            with open(module_file, 'r') as mf:
                target_class_def = [line for line in mf if re.search(r'^class %s\s*\(' % class_name, line)]

                if target_class_def:
                    tc_module[class_name] = module_name
                    target_classes_found += 1
        if not target_classes_found:
            problem = "No class: '' defined in any module located in the '%s' pkgdir"
            raise Exception(problem % (class_name, pkgdir))
        if target_classes_found > 1:
            problem = "class: '%s' defined in more than one module located in the '%s' pkgdir"
            raise Exception(problem % (class_name, pkgdir))
##
##        print "found likely module: %s containing %s" % (tc_module[class_name], class_name)
##

        pkgmod = '%s.%s' % (pkgdir, tc_module[class_name])
        pymod = __import__(pkgmod, globals(), None, ['*'], 0)
##
##        print "ClassLoader.loadConnectionClass ... %s module imported" % pkgmod
##
        conn_class = getattr(pymod, class_name, None)
        if not conn_class:
##
##            print "ClassLoader.loadConnectionClass ... %s class not found, to raise an Exception" % class_name
##
            raise Exception('Unable to locate class %s in any module in the %s pkgdir' % \
                            (class_name, pkgdir))
##
##        print "ClassLoader.loadConnectionClass ... class %s FOUND" % conn_class.__name__
##
        return conn_class

################################################################################
       
