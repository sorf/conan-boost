""" Builds with mingw (nuwen.net). """
from conan.packager import ConanMultiPackager

if __name__ == "__main__":
    gcc_version = "7.2"

    builder = ConanMultiPackager()
    # libcxx is always libstdc++11 for MingW
    builder.add(
        settings={"compiler": "gcc", "compiler.version": str(gcc_version),
                  "compiler.libcxx": "libstdc++11",
                  "arch": "x86_64", "build_type": "Release"},
        options={"Boost:shared": "True"})
    builder.add(
        settings={"compiler": "gcc", "compiler.version": str(gcc_version),
                  "compiler.libcxx": "libstdc++11",        
                  "arch": "x86_64", "build_type": "Debug"},
        options={"Boost:shared": "True"})
    builder.add(
        settings={"compiler": "gcc", "compiler.version": str(gcc_version),
                  "compiler.libcxx": "libstdc++11",
                  "arch": "x86_64", "build_type": "Release"},
        options={"Boost:shared": "False"})
    builder.add(
        settings={"compiler": "gcc", "compiler.version": str(gcc_version),
                  "compiler.libcxx": "libstdc++11",
                  "arch": "x86_64", "build_type": "Debug"},
        options={"Boost:shared": "False"})

    # The 32-bit builds fail to link.

    builder.run()
