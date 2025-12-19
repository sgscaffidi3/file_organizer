##!/usr/bin/env python
# -*- coding: utf-8 -*-
# file name : CodeStats.py
#      date : 1/30/2024
#    author : Greg Scaffidi
#           . email : sgscaffidi3@gmail.com
# copyright : All Rights Reserved. Pariah Software Solutions Inc.
#           : 2024, 
# ---------------------------------
# Get stats for our code
# To-do: cleanup/reconcile with other copy of this file in other projects/repos
#
import collections
import os
import ast
import pipreqs as pr
from DebugPrint import DebugPrint 
my_debug_print = DebugPrint()
my_debug_print.initialize()
print = my_debug_print.print

class ClassAST:
    Initialized = False

    def __init__(self):
        super().__init__()
        #print(": self.Initialized == " + str(self.Initialized))
        self.Initialized = True
        self.class_name = ""
        self.class_length = 0
        self.lineno = 0
        self.end_lineno = 0
        self.function_list = []
        self.num_functions = 0
        #print(": self.Initialized == " + str(self.Initialized))

    def compile_stats(self):
        self.class_length = self.end_lineno - self.lineno
        self.num_functions = len(self.function_list)

    def print_class(self, full: bool=False):
        #self.compile_stats()
        print("self.class_name = " + str(self.class_name))
        print("self.class_length = " + str(self.class_length))
        if(full):
            print("self.Initialized = " + str(self.Initialized))
            print("self.lineno = " + str(self.lineno))
            print("self.end_lineno = " + str(self.end_lineno))
            i = 0
            for fl in self.function_list:
                i += 1
                print("self.function_list[" + str(i) + "] = " + fl)

class FileAST:
    Initialized = False

    def __init__(self):
        super().__init__()
        #print(": self.Initialized == " + str(self.Initialized))
        self.Initialized = True
        self.file_name = ""
        self.file_code_length = 0
        self.num_classes = 0
        self.num_functions = 0
        self.class_list = []
        self.file_stats = collections.defaultdict(int)
        #print(": self.Initialized == " + str(self.Initialized))

    def compile_stats(self):
        for cl in self.class_list:
            cl.compile_stats()
        file_len = 0
        num_classes = 0
        num_functions = 0
        for cl in self.class_list:
            file_len += cl.class_length
            num_classes += 1
            num_functions += cl.num_functions
        self.num_functions = num_functions
        self.num_classes = num_classes
        self.file_code_length = file_len

    def print_file(self, full: bool=False):
        self.compile_stats()
        print("self.file_name = " + str(self.file_name))
        print("self.file_code_length = " + str(self.file_code_length))
        print("self.num_classes = " + str(self.num_classes))
        print("self.num_functions = " + str(self.num_functions))
        if full:
            print("self.Initialized = " + str(self.Initialized))
            i = 0
            for cl in self.class_list:
                i += 1
                print("self.class_list[" + str(i) + "] = " + cl.class_name)
                cl.print_class()
            print("self.file_stats = " + str(self.file_stats))

class CodeStats:
    Initialized = False

    def __init__(self):
        super().__init__()
        print(": self.Initialized == " + str(self.Initialized))
        self.Initialized = True
        self.num_py_files = 0
        self.num_loc = 0
        self.num_defs = 0
        self.num_class = 0
        self.ast_files = []
        print(": self.Initialized == " + str(self.Initialized))

    def analyze(self, packagedir):
        stats = collections.defaultdict(int)
        self.ast_files.clear()
        self.num_loc = 0
        self.num_py_files = 0
        for (dirpath, dirnames, filenames) in os.walk(packagedir):
            if 'venv' in dirpath.split(os.sep) or '.venv' in dirpath.split(os.sep):
                continue
            for filename in filenames:
                if not filename.endswith('.py'):
                    continue
                self.num_py_files += 1
                file_name = os.path.join(dirpath, filename)
                # Open with utf-8 and ignore errors for characters that aren't valid UTF-8
                with open(file_name, 'r', encoding='utf-8', errors='ignore') as f:
                    syntax_tree = ast.parse(f.read(), file_name)
                ast_file = FileAST()
                ast_file.file_name = filename
                for item in syntax_tree.body:
                    name_found = 0
                    last_name_found = ""
                    a_class = ClassAST()
                    lineno = 0
                    end_lineno = 0
                    for key in item.__dict__.keys():
                        if name_found >= 1:
                            if last_name_found == "":
                                last_name_found = a_class.class_name
                            if last_name_found == a_class.class_name:
                                #print(str(key) + " : " + str(item.__dict__[key]))
                                if key == "lineno":
                                    lineno = lineno
                                    a_class.lineno = item.__dict__[key]
                                    #print(str(key) + " : " + str(item.__dict__[key]))
                                if key == "end_lineno":
                                    end_lineno = end_lineno
                                    a_class.end_lineno = item.__dict__[key]
                                    #print(str(key) + " : " + str(item.__dict__[key]))
                                if key == "body":
                                    a_class.function_list.clear()
                                    #print(str(key) + " : " + str(item.__dict__[key]))
                                    for body_item in item.__dict__[key]:
                                        if "ast.FunctionDef" in str(body_item):
                                            #print(str(type(body_item)))
                                            #print((body_item.name))
                                            a_class.function_list.append(body_item.name)
                                    ast_file.class_list.append(a_class)

                        if key == "name":
                            lineno = 0
                            end_lineno = 0
                            last_name_found = a_class.class_name
                            #print(str(key) + " : " + str(item.__dict__[key]))
                            a_class = ClassAST()
                            a_class.class_name = str(item.__dict__[key])
                            last_name_found = a_class.class_name
                            
                            name_found += 1
                for node in ast.walk(syntax_tree):
                    stats[type(node)] += 1
                    ast_file.file_stats[type(node)] += 1
                self.ast_files.append(ast_file)
        
        return stats
    
    def print_asts(self):
        for item in self.ast_files:
            item.print_file()
    
    def compile_stats(self):
        tloc = 0
        tclass = 0
        tdef = 0
        for item in self.ast_files:
            item.compile_stats()
            tloc += item.file_code_length
            tclass += item.file_stats[ast.ClassDef]
            tdef += item.file_stats[ast.FunctionDef]
        self.num_loc = tloc
        self.num_class = tclass
        self.num_defs = tdef
    
    def initialize(self):
        status = "Failure"
        if(self.Initialized == True):
            status = "Success"
        return status

if __name__ == "__main__":
    my_code_stats = CodeStats()
    status = my_code_stats.initialize()
    print(str(type(my_code_stats).__name__) + " Initialization Status : " + status)
    results = my_code_stats.analyze('.')
    my_code_stats.compile_stats()
    print("Number of Python files:", str(my_code_stats.num_py_files))
    #print("Number of class statements:", results[ast.ClassDef])
    #print("Number of def statements:", results[ast.FunctionDef])
    print("Number of class statements:", str(my_code_stats.num_class))
    print("Number of def statements:", str(my_code_stats.num_defs))
    print("Number of lines of code:", str(my_code_stats.num_loc))
    print("Avg function size (loc):", str(my_code_stats.num_loc / my_code_stats.num_defs))
    print("Avg class size (loc):", str(my_code_stats.num_loc / my_code_stats.num_class))
    print("Avg class size (defs):", str(my_code_stats.num_defs / my_code_stats.num_class))


    # references
    '''
    https://stackoverflow.com/questions/5764437/python-code-statistics
    '''
