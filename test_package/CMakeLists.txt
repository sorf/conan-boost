PROJECT(MyHello)
cmake_minimum_required(VERSION 2.8)

set(Boost_DEBUG 1)
include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)

CONAN_BASIC_SETUP()

# cmake FindBoost assumes a versioned layout on Windows, so we cannot use it for the other layouts
# (e.g. system).
# So, using the include and lib variables coming directly from conanbuildinfo.cmake (package_info)

include_directories(${CONAN_INCLUDE_DIRS})

ADD_EXECUTABLE(lambda lambda.cpp)
IF(NOT HEADER_ONLY)
    IF(WITH_PYTHON)
        add_library(hello_ext SHARED python.cpp)
            if(WIN32)
                set_target_properties(hello_ext PROPERTIES SUFFIX ".pyd")
                target_include_directories(hello_ext PRIVATE ${PYTHON_INCLUDE})
                target_link_libraries(hello_ext ${PYTHON_LIB} ${CONAN_LIBS})
            ENDIF()
    ENDIF()
    IF(WITH_REGEX)
        ADD_EXECUTABLE(regex_exe regex.cpp)
        TARGET_LINK_LIBRARIES(regex_exe ${CONAN_LIBS})
    ENDIF()
ENDIF()
