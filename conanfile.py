import os
import platform
import re
import shutil
import subprocess
import sys
from conans import ConanFile
from conans import tools

if (sys.version_info.major, sys.version_info.minor) < (3, 5):
    raise RuntimeError("Python 3.5 is required")

boost_git = 'https://github.com/boostorg/boost.git'

# From from *1 (see below, b2 --show-libraries), also ordered following linkage order
# see https://github.com/Kitware/CMake/blob/master/Modules/FindBoost.cmake to know the order

lib_list = ['math', 'wave', 'container', 'exception', 'graph', 'iostreams', 'locale', 'log',
            'program_options', 'random', 'regex', 'mpi', 'serialization', 'signals',
            'coroutine', 'fiber', 'context', 'timer', 'thread', 'chrono', 'date_time',
            'atomic', 'filesystem', 'system', 'graph_parallel', 'python',
            'stacktrace', 'test', 'type_erasure']

class BoostConan(ConanFile):
    name = "boost"
    version = "1.66.0"
    settings = "os", "arch", "compiler", "build_type"
    bzip2_version = "1.0.6"
    bzip2_md5 = "00b516f4704d4a7cb50a1d97e6e8e15b"
    zlib_version = "1.2.11"
    zlib_sha256 = "c3e5e9fdd5004dcb542feda5ee4f0ff0744628baf8ed2dd5d66f8ca1197cb1a1"

    # The current python option requires the package to be built locally, to find default Python
    # implementation
    options = {
        "cppstd" : ["default", "11", "14", "17"],
        "shared": [True, False],
        "header_only": [True, False],
        "fPIC": [True, False],
        "layout" : ["versioned", "tagged", "system"]
    }
    options.update({"without_%s" % libname: [True, False] for libname in lib_list})

    default_options = ["shared=False", "cppstd=17", "header_only=False", "fPIC=True", "layout=system"]
    default_options.extend(["without_%s=False" % libname for libname in lib_list])

    url = "https://github.com/lasote/conan-boost"
    license = "Boost Software License - Version 1.0. http://www.boost.org/LICENSE_1_0.txt"
    short_paths = True
    no_copy_source = True

    def config_options(self):
        if self.settings.compiler == "Visual Studio":
            self.options.remove("fPIC")

    def configure(self):
        if self.options.header_only:
            self.options.remove("shared")
            self.options.remove("fPIC")
            self.options.remove("layout")

        if self.settings.compiler == "Visual Studio" and \
           self.options.shared and "MT" in str(self.settings.compiler.runtime):
            self.options.shared = False
            # The Python library is compiled with "MD", so we cannot link against it in "MT" builds
            self.options.without_python = True

        if self.settings.os == "Windows":
            # Disable Python build on Windows when:
            if self.settings.compiler == "gcc":
                # As for Mingw gcc we don't have (yet) the compiler_redirect infrastructure,
                # disabling the Boost.Python library to avoid hitting this problem:
                # https://github.com/Alexpux/MINGW-packages/issues/3224
                # https://stackoverflow.com/questions/10660524/error-building-boost-1-49-0-with-gcc-4-7-0/12124708#12124708
                self.options.without_python = True
            if (self.settings.arch == "x86_64" and platform.architecture()[0] != "64bit") or \
               (self.settings.arch == "x86" and platform.architecture()[0] != "32bit"):
               # Python architecture should match the build one (32 vs 64 bit)
                self.options.without_python = True
        else:
            # On other platforms Python build disabled by default
            self.options.without_python = True

        if self.settings.os == "Windows" and self.settings.compiler == "gcc":
            # Also we need to build with _GLIBCXX_USE_CXX11_ABI = 1 to avoid linker errors such as:
            #   libstdc++.a(cow-stdexcept.o):cow-stdexcept.cc:(.text$_ZNSt13runtime_errorC2ERKS_+0x0):
            #   multiple definition of `std::runtime_error::runtime_error(std::runtime_error const&)'
            # So, we set/overwrite the libcxx setting to libstdc++11
            if not self.settings.compiler.libcxx or self.settings.compiler.libcxx != "libstdc++11":
                self.output.warn('Forcing compiler.libcxx to be "libstdc++11"')
                self.settings.compiler.libcxx = "libstdc++11"

    def package_id(self):
        if self.options.header_only:
            self.info.header_only()

    def source(self):
        self.output.info("Downloading boost...")
        if not os.path.isdir("boost"):
            self.run('git clone -b boost-%s --recursive \
            --single-branch %s' % (self.version, boost_git))
        else:
            self.run("cd boost && git pull")

        if not self.options.without_iostreams:
            # bzip2
            self.output.info("Downloading bzip2...")
            bzip2_zip_name = "bzip2-%s.tar.gz" % self.bzip2_version
            if not os.path.isfile(bzip2_zip_name):
                tools.download("http://www.bzip.org/%s/%s" %
                               (self.bzip2_version, bzip2_zip_name), bzip2_zip_name)
            tools.check_md5(bzip2_zip_name, self.bzip2_md5)
            tools.unzip(bzip2_zip_name)

            # zlib
            self.output.info("Downloading zlib...")
            zlib_zip_name = "zlib-%s.tar.gz" % self.zlib_version
            if not os.path.isfile(zlib_zip_name):
                tools.download("http://downloads.sourceforge.net/project/libpng/zlib/%s/%s" %
                               (self.zlib_version, zlib_zip_name), zlib_zip_name)
            tools.check_sha256(zlib_zip_name, self.zlib_sha256)
            tools.unzip(zlib_zip_name)


    def build(self):
        if self.options.header_only:
            self.output.warn("Header only package, skipping build")
            return
        self._check_build_settings()

        abs_source_folder = os.path.abspath(self.source_folder)
        abs_build_folder = os.path.abspath(".")

        # Note: bootstrap and b2 headers change the source folder which may be shared between
        # build variants.
        # This should be safe as bootstrap builds from scratch each time and the result of
        # b2 headers is usable across build variants.
        self._bootstrap(abs_source_folder)
        self._b2_headers(abs_source_folder)

        args = self._get_build_args(abs_source_folder, abs_build_folder)
        b2_args = " ".join(args)

        # Note: See https://github.com/boostorg/build/issues/257
        # in case build fails after a MSVC upgrade.
        command_start = "cd %s && " % (os.path.join(abs_source_folder, "boost"))
        command_start += ".\\b2 " if self.settings.os == "Windows" else "./b2 "
        command_start += " --stagedir=%s " % os.path.join(abs_build_folder, "stage")
        command = command_start + b2_args

        if self.settings.os == "Windows" and self.settings.compiler == "Visual Studio":
            command = "%s && %s" % (tools.vcvars_command(self.settings), command)

        self.output.info("Running: %s" % command)
        self.run(command)

    def _check_build_settings(self):
        if self.settings.compiler == "gcc":
            self.output.info("Checking g++ version (expecting: %s)" %
                             self.settings.compiler.version)
            # the build will calling 'g++' without any version (the compiler_redirect support)
            result = subprocess.run(
                ["g++", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=True,
                universal_newlines=True)
            if not re.match(r"g\+\+ \(.*\) %s" % self.settings.compiler.version, result.stdout):
                self.output.error("Expected version %s was not found in:\n%s" % (
                    self.settings.compiler.version,
                    result.stdout))
                raise RuntimeError("Unexpected compiler version")

    def _remove_if_exists(self, file):
        if os.path.exists(file) and os.path.isfile(file):
            os.remove(file)

    def _bootstrap(self, abs_source_folder):
        with_toolset = {"apple-clang": "darwin"}.get(str(self.settings.compiler),
                                                     str(self.settings.compiler))

        boost_source_folder = os.path.join(abs_source_folder, "boost")
        tools_build_folder = os.path.join(boost_source_folder, "tools", "build")

        if self.settings.os == "Windows":
            # Deleting old b2 binaries
            self._remove_if_exists(tools_build_folder + "\\src\\engine\\bin.ntx86\\b2.exe")
            self._remove_if_exists(tools_build_folder + "\\src\\engine\\bin.ntx86\\bjam.exe")
            self._remove_if_exists(tools_build_folder + "\\src\\engine\\bin.ntx86_64\\bjam.exe")
            self._remove_if_exists(tools_build_folder + "\\src\\engine\\bin.ntx86_64\\bjam.exe")

        command = "cd %s && " % tools_build_folder
        command += ".\\bootstrap" if self.settings.os == "Windows" \
            else "./bootstrap.sh --with-toolset=%s" % with_toolset

        if self.settings.os == "Windows" and self.settings.compiler == "gcc":
            # bootstrap run for Mingw
            command += " gcc"

        if self.settings.os == "Windows" and self.settings.compiler == "Visual Studio":
            command = "%s && %s" % (tools.vcvars_command(self.settings), command)

        try:
            self.output.info("Running bootstrap: %s" % command)
            self.run(command)
        except:
            bootstrap_log = os.path.join(tools_build_folder, "bootstrap.log")
            if os.path.isfile(bootstrap_log):
                print("Error running bootstrap. bootstrap.log:\n----------")
                with open(bootstrap_log, 'r') as fin:
                    print(fin.read(), end="")
                print("\n----------")
            raise
        b2 = "b2.exe" if self.settings.os == "Windows" else "b2"
        shutil.copy(os.path.join(tools_build_folder, b2), boost_source_folder)

    def _b2_headers(self, abs_source_folder):
        command = "cd %s && " % (os.path.join(abs_source_folder, "boost"))
        command += ".\\b2 headers" if self.settings.os == "Windows" else "./b2 headers"
        self.output.info("Running: %s" % command)
        self.run(command)

    def _get_build_args(self, abs_source_folder, abs_build_folder):
        args = []

        # Options
        args.append("--build-dir=%s" % os.path.join(abs_build_folder, "tmp"))
        args.append("--layout=%s" % self.options.layout)
        args.append("--abbreviate-paths")
        args.append(" -j%s" % tools.cpu_count())
        args.append(" -d2") # to print more debug info and avoid travis timing out without output

        # Libraries
        args.extend(self._get_build_args_libraries())

        # Properties: Toolset
        if self.settings.compiler == "Visual Studio":
            args.append("toolset=msvc-%s" % self._msvc_version())
        elif str(self.settings.compiler) in ["clang", "gcc"]:
            # For clang / gcc we use the toolset as the compiler name (without any version).
            # (see linux_compiler_redirect)
            args.append("toolset=%s" % self.settings.compiler)
        elif str(self.settings.compiler) == "apple-clang":
            args.append("toolset=darwin")

        # Other properties:
        args.append("variant=%s" % str(self.settings.build_type).lower())
        args.append("address-model=%s" % ("32" if self.settings.arch == "x86" else "64"))
        args.append("link=%s" % ("static" if not self.options.shared else "shared"))
        if self.settings.compiler == "Visual Studio":
            args.append("runtime-link=%s" % (
                "static" if "MT" in str(self.settings.compiler.runtime) else "shared"))
        else:
            args.append("runtime-link=shared")

        # bzip and zlib
        args.append('-sBZIP2_SOURCE="%s"' %
                    os.path.join(abs_source_folder, "bzip2-%s" % self.bzip2_version))
        args.append('-sZLIB_SOURCE="%s"' %
                    os.path.join(abs_source_folder, "zlib-%s" % self.zlib_version))

        # The compiler and linker flags
        cppflags, linkflags, defines = self._get_build_cppflags_linkflags_defines()
        
        args.append('cxxflags="%s"' % " ".join(cppflags) if cppflags else "")
        args.append('linkflags="%s"' % " ".join(linkflags) if linkflags else "")
        for define in defines:
            args.append('define=%s' % define)
        return args

    def _get_build_args_libraries(self):
        args = []
        for libname in lib_list:
            if getattr(self.options, "without_%s" % libname):
                args.append("--without-%s" % libname)
        return args

    def _get_build_cppflags_linkflags_defines(self):
        """ C++ compiler flags, linker flags and defines.
            They are used both in build() and package_info(). """
        cppflags = []
        linkflags = []
        defines = []

        # C++ standard
        if self.options.cppstd != "default":
            if self.settings.compiler != "Visual Studio":
                cppflags.append("-std=c++%s" % self.options.cppstd)
            else:
                cppflags.append("/std:c++%s" % self.options.cppstd)
                defines.append("_HAS_AUTO_PTR_ETC=1")

        # FPIC
        if self.settings.compiler != "Visual Studio":
            if self.options.fPIC:
                cppflags.append("-fPIC")

        # The libcxx settings
        # Note: See https://gcc.gnu.org/onlinedocs/libstdc++/manual/using_dual_abi.html
        # the version of C++ is orthogonal to the stdc++ one.
        if self.settings.compiler == "gcc" or "clang" in str(self.settings.compiler):
            if str(self.settings.compiler.libcxx) == "libstdc++":
                defines.append("_GLIBCXX_USE_CXX11_ABI=0")
            elif str(self.settings.compiler.libcxx) == "libstdc++11":
                defines.append("_GLIBCXX_USE_CXX11_ABI=1")

        if "clang" in str(self.settings.compiler):
            if str(self.settings.compiler.libcxx) == "libc++":
                cppflags.append("-stdlib=libc++")
                linkflags.append("-stdlib=libc++")
            else:
                cppflags.append("-stdlib=libstdc++")
                linkflags.append("-stdlib=libstdc++")

        return cppflags, linkflags, defines

    def _msvc_version(self):
        if self.settings.compiler.version == "15":
            return "14.1"
        return "%s.0" % self.settings.compiler.version

    def package(self):
        # Note: When no_copy_source is True, the package() method will be called twice,
        # one copying from the source folder and the other copying from the build folder.
        self.output.info("Packaging files from: %s" % os.path.abspath("."))
        if os.path.abspath(".") == os.path.abspath(self.source_folder):
            self.copy(pattern="*", dst="include/boost", src="boost/boost")
        else:
            self.copy(pattern="*.a", dst="lib", src="stage/lib")
            self.copy(pattern="*.so", dst="lib", src="stage/lib")
            self.copy(pattern="*.so.*", dst="lib", src="stage/lib")
            self.copy(pattern="*.dylib*", dst="lib", src="stage/lib")
            self.copy(pattern="*.lib", dst="lib", src="stage/lib")
            self.copy(pattern="*.dll", dst="bin", src="stage/lib")

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        if self.options.without_test: # remove boost_unit_test_framework
            self.cpp_info.libs = [lib for lib in self.cpp_info.libs if "unit_test" not in lib]

        self.output.info("LIBRARIES: %s" % self.cpp_info.libs)

        if not self.options.header_only and self.options.shared:
            self.cpp_info.defines.append("BOOST_ALL_DYN_LINK")
        else:
            self.cpp_info.defines.append("BOOST_USE_STATIC_LIBS")

        if not self.options.header_only:
            if not self.options.without_python:
                if not self.options.shared:
                    self.cpp_info.defines.append("BOOST_PYTHON_STATIC_LIB")

            if self.settings.compiler == "Visual Studio":
                # DISABLES AUTO LINKING! NO SMART AND MAGIC DECISIONS THANKS!
                self.cpp_info.defines.extend(["BOOST_ALL_NO_LIB"])
