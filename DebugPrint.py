#!/usr/bin/env python
# -*- coding: utf-8 -*-
# file name : DebugPrint.py
#   created : 01/19/2024
#    author : Greg Scaffidi
#           . email : sgscaffidi3@gmail.com
# copyright : All Rights Reserved. Pariah Software Solutions Inc.
#           : 2024
# ---------------------------------
# A way to manage debug prints
#

DEBUG=1 # only print when debugging
import datetime
import inspect
import os
import platform

def nothing():
    return

class TestClass:
    Initialized = False
    def __init__(self):
        super().__init__()
        self.Initialized = True

    def test_print(self):
        print("Hello World!")


class DebugPrint:
    Initialized = False
    debug_debug_print = False
    _print = nothing
    def __init__(self):
        super().__init__()
        if self.debug_debug_print:
            print("DebugPrint __init__ : self.Initialized == " + str(self.Initialized))
        self.Initialized = True
        self._initialized = False
        self.line_ending = ""
        self.default_prefix_space = "    "
        self.prefix_space = self.default_prefix_space
        self.cts_call_recursion_depth = -1
        self.add_line_nos = False
        self.add_main_sf = False
        self.plat_os = str(platform.system())
        self.debug_enabled = False
        self.max_packs = 0
        self.do_debug = True
        if self.debug_debug_print:
            print("DebugPrint __init__ : self.Initialized == " + str(self.Initialized))

    def print_self(self):
        if(self._initialized == True):
            print(self.class_to_str(self))

    def print_vars(self):
        if(self._initialized == True):
            vars = inspect.getmembers(self)
            for thing in vars:
                if thing[0] == '__dict__':
                    d = thing[1]
                    for key in d.keys():
                        if key == "df":
                            print("self." + str(key) + " : \n" + str(d[key]))
                        elif (("sys_info" in key or "pers_db" in key) and "my_" not in key):
                            print("self." + str(key) + " : " + "{")
                            comma_count  = 0
                            for stuff in d[key]:
                                if(comma_count + 1 < len(d[key])):
                                    comma = ","
                                else:
                                    comma = ""
                                print("    \'" + stuff + "\': " + "\'" + str(d[key][stuff]) + "\'" + comma)
                                comma_count += 1
                            print("}")
                        else:
                            print("self." + str(key) + " : " + str(d[key]))

    def update_prefix_space(self):
        if(self._initialized == True):
            ps = self.default_prefix_space
            total_ps = ps
            for i in range(0,self.cts_call_recursion_depth):
                total_ps += ps
                i += 1
            self.prefix_space = total_ps

    # To-do: detect the jloads and jdumps and pull in some, "required" comments # https://stackoverflow/UID.static.html
    def class_to_str(self, in_class):
        ret_val = "" + self.line_ending
        if(self._initialized == True):
            self.cts_call_recursion_depth += 1
            self.update_prefix_space()
            #inspect.
            vars = inspect.getmembers(in_class)
            yourself = str(inspect.getmodulename(inspect.getsourcefile(in_class.__class__))) + "."
            #print("len(vars) : " + str(len(vars)))
            for thing in vars:
                if thing[0] == '__dict__':
                    d = thing[1]
                    for key in d.keys():
                        if "my_" in key:
                            it = d[key]
                            print_it = ""
                            if(type(it) == list) and "object" not in (str(it)):
                                print_it += str(it)
                            #elif("class" in str(type(it)) or "object" in str(type(it))):
                            elif("class" in str(type(it))):
                                if(type(it) != list):
                                    #print("it : " + str(it))
                                    try:
                                        print_it += self.class_to_str(it)
                                    except TypeError as te:
                                        if("is a built-in class" in str(te)):
                                            if (type(it) == float):
                                                print_it += str("{:.7f}").format(it)
                                            else:
                                                print_it += str(it)
                                        else:
                                            print("Error : " + str(te))
                                else:
                                    for li in it:
                                        print_it += self.class_to_str(li)
                            ret_val += self.prefix_space + yourself + str(key) + " : " + print_it + self.line_ending
                        else:
                            if key == "df":
                                ret_val += self.prefix_space + (yourself + str(key) + " : \n" + str(d[key]) + self.line_ending)
                            elif (("sys_info" in key or "pers_db" in key) and "my_" not in key): # my_ not in key!
                                ret_val += self.prefix_space + (yourself + str(key) + " : " + "{" + self.line_ending)
                                comma_count  = 0
                                for stuff in d[key]:
                                    print_it = ""
                                    # we're in sys_into or pers_db
                                    if(("my_" in stuff) ): # my_ in stuff!
                                        if(type(d[key][stuff]) == list):
                                            cnt = -1
                                            packs = 0
                                            # how long is this list of stuff?
                                            for thing in d[key][stuff]:
                                                if ("class" in str(type(thing))):
                                                    packs += 1
                                            # print how long the list is
                                            ret_val += self.prefix_space + ("    \'" + stuff + "[" + str(packs) + "]\':")
                                            for thing in d[key][stuff]:
                                                if ("class" in str(type(thing))):
                                                    cnt += 1
                                                    if(cnt <= self.max_packs): # To-do: add option to print just a few details of the class (prints too much with 500+ Apt packages.)
                                                        #print("thing : " + str(thing))
                                                        #ret_val += self.prefix_space + (yourself + str(key) + " : " + "{" + self.line_ending)
                                                        self.cts_call_recursion_depth += 1
                                                        self.update_prefix_space()
                                                        # print this item's position in the list...
                                                        print_it += self.line_ending + self.prefix_space + "[" + str(cnt) + "]"
                                                        tp = self.class_to_str(thing)
                                                        self.cts_call_recursion_depth -= 1
                                                        self.update_prefix_space()
                                                        print_it += tp
                                                        if(comma_count + 1 < len(d[key])):
                                                            comma = ","
                                                        else:
                                                            comma = ""
                                                        comma_count += 1
                                            ret_val += print_it + comma + self.line_ending
                                    else:
                                        if(comma_count + 1 < len(d[key])):
                                            comma = ","
                                        else:
                                            comma = ""
                                        print_it += str(d[key][stuff])
                                        comma_count += 1
                                        ret_val += self.prefix_space + ("    \'" + stuff + "\': " + "\'" + print_it + "\'" + comma + self.line_ending)
                                ret_val += self.prefix_space + ("}" + self.line_ending)
                            elif "line_ending" in key:
                                le = str(d[key])
                                lep = ""
                                if (le == "\n"):
                                    lep = "\\n"
                                elif (le == "\r\n"):
                                    lep = "\\r\\n"
                                ret_val += self.prefix_space + (yourself + str(key) + " : " + lep + self.line_ending)
                            elif "prefix_space" in key:
                                ps = str(d[key])
                                psp = '\''+ ps + '\''
                                ret_val += self.prefix_space + (yourself + str(key) + " : " + psp + self.line_ending)
                            else:
                                ret_val += self.prefix_space + (yourself + str(key) + " : " + str(d[key]) + self.line_ending)
        self.cts_call_recursion_depth -= 1
        self.update_prefix_space()
        return ret_val

    def print_class(self, in_class):
        ret_val = "Failure"
        if(self._initialized == True):
            print(self.class_to_str(in_class=in_class))
            ret_val = "Success"
        return ret_val

    def print(self, *args, **kwargs):
        ret_val = "Failure"
        if(self._initialized == True):
            if(self.debug_enabled):
                aa = args
                kk = kwargs
                #print("args : " + str(args) + " kwargs : " + str(kwargs))
                if self.do_debug:
                    line_no = -1
                    if self.add_line_nos == True or self.add_main_sf == True:
                        callerframerecord = inspect.stack()[1]    # 0 represents this line
                                                                  # 1 represents line at caller
                        frame = callerframerecord[0]
                        #self._print("callerframerecord : " + str(callerframerecord))
                        info = inspect.getframeinfo(frame)
                        #self._print("info.fnm : " + info.filename, end='')                      # __FILE__     -> DebugPrint.py
                        #self._print("info.fnc : " + info.function, end='')                      # __FUNCTION__ -> test_print
                        #self._print("info.lno : " + str(info.lineno), end='')                   # __LINE__     -> 18
                        #self._print("info.ctx : " + str(info.code_context), end='')                   # __LINE__     -> 18
                        #self._print("str(info) : " + str(info) + " :\n", end='')
                        last_fun = str(info.code_context).replace(' ','')
                        line_no = info.lineno
                    stack = inspect.stack()
                    keys = stack[1][0].f_locals.keys()
                    #self._print(str(keys))
                    #the_class = os.path.basename(stack[1][0].f_locals.get("__file__")).strip(".py")
                    the_file = os.path.basename(stack[1][0].f_code.co_filename)
                    the_class = ""
                    #yourself = str(inspect.getmodulename(inspect.getsourcefile(in_class.__class__))) + "."
                    try:
                        the_class = str(os.path.basename(stack[1][0].f_code.co_qualname.split('.')[0]))
                    except AttributeError as ae:
                        try:
                            the_class = os.path.basename(stack[1][0].f_locals.get("__file__")).strip(".py")
                        except TypeError as te:
                            try:
                                the_class = os.path.basename(stack[1][0].f_code.co_filename).strip(".py")
                            except:
                                the_class = str(self)
                                self._print("ERROR ! TypeError : " + str(te))
                                self._print("ERROR ! AttributeError : " + str(ae))
                        #self._print("...ERROR ! NativeCommandError : " + str(stack))
                    the_method = ""
                    if("__name__" in keys):
                        the_method = stack[1][0].f_locals["__name__"]
                    else:
                        the_method = stack[1][0].f_code.co_name
                    self._print(f"{datetime.datetime.now()} ", end='')
                    if (self.add_line_nos == True):
                        self._print("{}:{}.{}()[{}".format(the_file, the_class, the_method, str(line_no)) + "] ", end='')
                    else:
                        self._print("{}:{}.{}()".format(the_file, the_class, the_method) + " ", end='')
                    orig_args = None
                    if self.add_main_sf == True and (len(args) == 1 and (args[0] == "Success" or args[0] == "Failure")):
                        orig_args = {}
                        new_args = last_fun.strip().replace('\\n','')
                        new_args = new_args.replace('\\','')
                        new_args = new_args.replace('[','')
                        new_args = new_args.replace(']','')
                        orig_args = {new_args + " : " + args[0]}
                    if orig_args == None:
                        orig_args = args
                    self._print(*orig_args, **kwargs)
                else:
                    self._print(*args, **kwargs)
                    pass
            else:
                self._print(*args, **kwargs)
            ret_val = "Success"
        return ret_val

    def control_debug(self, debug: bool=True, line_nos: bool=None):
        ret_val = "Failure"
        if(self._initialized == True):
            self.debug_enabled = debug
            if(line_nos != None):
                self.add_line_nos = line_nos
            ret_val = "Success"
        return ret_val

    def initialize(self, debug: bool=True, prefix_space: str="    ", line_nos: bool=None, add_main_sf: bool= True, max_packs: int=5):
        ret_val = "Failure"
        if(self.Initialized == True):
            if(self._initialized == False):
                self.prefix_space = prefix_space
                if(self.plat_os == "Windows"):
                    self.line_ending = "\r\n"
                elif(self.plat_os == "Linux"):
                    self.line_ending = "\n"
                if(line_nos != None):
                    self.add_line_nos = line_nos
                if(add_main_sf != None):
                    self.add_main_sf = add_main_sf
                self._print = print  # preserve original
                self.debug_enabled = debug
                self.max_packs = max_packs
                ret_val = "Success"       # which of 
                self._initialized = True  # these 2 lines should come first?
        return ret_val

if __name__ == "__main__":
    my_debug_print = DebugPrint()
    status = my_debug_print.initialize(line_nos=True, add_main_sf=False)
    print = my_debug_print.print
    print(str(type(my_debug_print).__name__) + " Initialization Status : " + status)
    my_debug_print.print_vars()
    my_debug_print.print_self()
    my_debug_print.print_class(my_debug_print)
    test1 = TestClass()
    test1.test_print()
    