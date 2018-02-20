from conans.model.conan_file import ConanFile
from conans import CMake
import os
import sys


class DefaultNameConan(ConanFile):
    name = "DefaultName"
    version = "0.1"
    settings = "os", "arch", "compiler", "build_type"
    generators = "cmake"

    def configure(self):
        if self.options["boost"].header_only:
            self.settings.clear()

    def build(self):
        cmake = CMake(self)
        if self.options["boost"].header_only:
            cmake.definitions["HEADER_ONLY"] = "TRUE"
        if not self.options["boost"].without_python:
            cmake.definitions["WITH_PYTHON"] = "TRUE"
            if self.settings.os == "Windows":
                python_folder = os.path.dirname(sys.executable)
                cmake.definitions["PYTHON_INCLUDE"] = os.path.join(
                    python_folder,
                    "include")
                python_lib_file_name = "python%s%s.lib" % (
                    sys.version_info.major, sys.version_info.minor)
                cmake.definitions["PYTHON_LIB"] = os.path.join(
                    python_folder,
                    "libs",
                    python_lib_file_name)
                for lib in self.deps_cpp_info.libs:
                    if "python" in lib:
                        cmake.definitions["BOOST_PYTHON_LIB"] = lib
                        break

        if not self.options["boost"].without_regex:
            cmake.definitions["WITH_REGEX"] = "TRUE"
            for lib in self.deps_cpp_info.libs:
                if "regex" in lib:
                    cmake.definitions["BOOST_REGEX_LIB"] = lib
                    break
        cmake.configure()
        cmake.build()

    def imports(self):
        self.copy(pattern="*.dll", dst="bin", src="bin")
        self.copy(pattern="*.dylib", dst="bin", src="lib")
        
    def test(self):        
        data_file = os.path.join(self.source_folder, "data.txt")
        self.output.info("Running: lambda")
        self.run("cd bin && .%slambda < %s" % (os.sep, data_file))
        if not self.options["boost"].header_only:
            if not self.options["boost"].without_regex:
                self.output.info("Running: regex_exe")
                self.run("cd bin && .%sregex_exe < %s" % (os.sep, data_file))
            if not self.options["boost"].without_python:
                os.chdir("bin")
                sys.path.append(".")
                import hello_ext
                self.output.info("Calling: Python hello_ext.greet: %s" % hello_ext.greet())
