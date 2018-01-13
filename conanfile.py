import os
import shutil
from conans import ConanFile
from conans import tools


class BoostConan(ConanFile):
    name = "Boost"
    version = "1.66.0"
    settings = "os", "compiler", "build_type", "arch", "os_build", "arch_build"
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
        "layout" : ["versioned", "tagged", "system"],
        "without_atomic": [True, False],
        "without_chrono": [True, False],
        "without_container": [True, False],
        "without_context": [True, False],
        "without_coroutine": [True, False],
        "without_coroutine2": [True, False],
        "without_date_time": [True, False],
        "without_exception": [True, False],
        "without_fiber": [True, False],
        "without_filesystem": [True, False],
        "without_graph": [True, False],
        "without_graph_parallel": [True, False],
        "without_iostreams": [True, False],
        "without_locale": [True, False],
        "without_log": [True, False],
        "without_math": [True, False],
        "without_metaparse": [True, False],
        "without_mpi": [True, False],
        "without_poly_collection": [True, False],
        "without_program_options": [True, False],
        "without_python": [True, False],
        "without_random": [True, False],
        "without_regex": [True, False],
        "without_serialization": [True, False],
        "without_signals": [True, False],
        "without_stacktrace": [True, False],
        "without_system": [True, False],
        "without_test": [True, False],
        "without_thread": [True, False],
        "without_timer": [True, False],
        "without_type_erasure": [True, False],
        "without_wave": [True, False]
    }

    default_options = "shared=False", \
        "cppstd=17", \
        "header_only=False", \
        "fPIC=True", \
        "layout=system", \
        "without_atomic=False", \
        "without_chrono=False", \
        "without_container=False", \
        "without_context=False", \
        "without_coroutine=False", \
        "without_coroutine2=False", \
        "without_date_time=False", \
        "without_exception=False", \
        "without_fiber=False", \
        "without_filesystem=False", \
        "without_graph=False", \
        "without_graph_parallel=False", \
        "without_iostreams=False", \
        "without_locale=False", \
        "without_log=False", \
        "without_math=False", \
        "without_metaparse=False", \
        "without_mpi=False", \
        "without_poly_collection=False", \
        "without_program_options=False", \
        "without_python=False", \
        "without_random=False", \
        "without_regex=False", \
        "without_serialization=False", \
        "without_signals=False", \
        "without_stacktrace=False", \
        "without_system=False", \
        "without_test=False", \
        "without_thread=False", \
        "without_timer=False", \
        "without_type_erasure=False", \
        "without_wave=False"

    url = "https://github.com/lasote/conan-boost"
    exports = ["FindBoost.cmake", "OriginalFindBoost*"]
    license = "Boost Software License - Version 1.0. http://www.boost.org/LICENSE_1_0.txt"
    short_paths = True
    no_copy_source = True

    def config_options(self):
        """ First configuration step. Only settings are defined. Options can be removed
        according to these settings
        """
        if self.settings.compiler == "Visual Studio":
            self.options.remove("fPIC")

    def configure(self):
        """ Second configuration step. Both settings and options have values, in this case
        we can force static library if MT was specified as runtime
        """
        if self.settings.compiler == "Visual Studio" and \
           self.options.shared and "MT" in str(self.settings.compiler.runtime):
            self.options.shared = False

        if self.options.header_only:
            # Should be doable in conan_info() but the UX is not ready
            self.options.remove("shared")
            self.options.remove("fPIC")
            self.options.remove("layout")

        if self.settings.os == "Windows" and self.settings.compiler == "gcc":
            # As for Mingw gcc we don't have (yet) the compiler_redirect infrastructure,
            # disabling the Boost.Python library to avoid hitting this problem:
            # https://github.com/Alexpux/MINGW-packages/issues/3224
            # https://stackoverflow.com/questions/10660524/error-building-boost-1-49-0-with-gcc-4-7-0/12124708#12124708
            self.options.without_python = True
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
            --single-branch https://github.com/boostorg/boost.git' % self.version)
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

        abs_source_folder = os.path.abspath(self.source_folder)
        abs_build_folder = os.path.abspath(".")

        # Note: bootstrap and b2 headers change the source folder which may be shared between
        # build variants.
        # This should be safe as bootstrap buils from scratch each time and the result of
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

    def _bootstrap(self, abs_source_folder):
        with_toolset = {"apple-clang": "darwin"}.get(str(self.settings.compiler),
                                                     str(self.settings.compiler))

        boost_source_folder = os.path.join(abs_source_folder, "boost")
        tools_build_folder = os.path.join(boost_source_folder, "tools", "build")
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

        # Other properties:
        args.append("variant=%s" % str(self.settings.build_type).lower())
        args.append("address-model=%s" % ("32" if self.settings.arch == "x86" else "64"))
        args.append("link=%s" % ("static" if not self.options.shared else "shared"))
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
        option_names = {
            "--without-atomic": self.options.without_atomic,
            "--without-chrono": self.options.without_chrono,
            "--without-container": self.options.without_container,
            "--without-context": self.options.without_context,
            "--without-coroutine": self.options.without_coroutine,
            "--without-coroutine2": self.options.without_coroutine2,
            "--without-date_time": self.options.without_date_time,
            "--without-exception": self.options.without_exception,
            "--without-fiber": self.options.without_fiber,
            "--without-filesystem": self.options.without_filesystem,
            "--without-graph": self.options.without_graph,
            "--without-graph_parallel": self.options.without_graph_parallel,
            "--without-iostreams": self.options.without_iostreams,
            "--without-locale": self.options.without_locale,
            "--without-log": self.options.without_log,
            "--without-math": self.options.without_math,
            "--without-metaparse": self.options.without_metaparse,
            "--without-mpi": self.options.without_mpi,
            "--without-program_options": self.options.without_program_options,
            "--without-python": self.options.without_python,
            "--without-random": self.options.without_random,
            "--without-regex": self.options.without_regex,
            "--without-serialization": self.options.without_serialization,
            "--without-signals": self.options.without_signals,
            "--without-system": self.options.without_system,
            "--without-test": self.options.without_test,
            "--without-thread": self.options.without_thread,
            "--without-timer": self.options.without_timer,
            "--without-type_erasure": self.options.without_type_erasure,
            "--without-wave": self.options.without_wave
        }

        for option_name, activated in option_names.items():
            if activated:
                args.append(option_name)
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
            cppflags, linkflags, defines = self._get_build_cppflags_linkflags_defines()

            self.cpp_info.cppflags.extend(cppflags)
            self.cpp_info.sharedlinkflags.extend(linkflags)
            self.cpp_info.exelinkflags.extend(linkflags)
            self.cpp_info.defines.extend(defines)

            if not self.options.without_python:
                if not self.options.shared:
                    self.cpp_info.defines.append("BOOST_PYTHON_STATIC_LIB")

            if self.settings.compiler == "Visual Studio":
                # DISABLES AUTO LINKING! NO SMART AND MAGIC DECISIONS THANKS!
                self.cpp_info.defines.extend(["BOOST_ALL_NO_LIB"])
