""" Builds with Visual Studio 2017 (msvc 14.1). """
from conan.packager import ConanMultiPackager

if __name__ == "__main__":
    visual_studio_version = "15"

    builder_64 = ConanMultiPackager(
        visual_versions=[visual_studio_version],
        archs=["x86_64"])
    builder_64.add_common_builds(shared_option_name="Boost:shared", pure_c=False)
    #print(builder_64.builds)
    builder_64.run()

    builder_32_release = ConanMultiPackager(
        visual_versions=[visual_studio_version],
        archs=["x86"],
        build_types=["Release"])
    builder_32_release.add_common_builds(shared_option_name="Boost:shared", pure_c=False)
    #print(builder_32_release.builds)
    builder_32_release.run()
