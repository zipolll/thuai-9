add_rules("mode.debug", "mode.release")
add_requires("ixwebsocket")
add_requires("nlohmann_json")
add_requires("doctest")


target("agent")
    set_kind("binary")
    set_languages("c++17")

    add_files("src/*.cpp")
    add_packages("ixwebsocket", "nlohmann_json")

    after_build(function (target)
        os.cp(
            target:targetfile(),
            path.join(os.projectdir(), "bin", path.filename(target:targetfile()))
        )
    end)

target("protocol_tests")
    set_kind("binary")
    set_default(false)
    set_languages("c++17")
    add_files("tests/protocol_tests.cpp")
    add_includedirs("src")
    add_packages("doctest", "nlohmann_json")
