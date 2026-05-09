add_rules("mode.debug", "mode.release")

add_requires("ixwebsocket")
add_requires("nlohmann_json")
add_requires("doctest")
add_requires("spdlog")
add_requires("cxxopts")

target("agent")
    set_kind("binary")
    add_files("src/**.cpp")
    add_packages("ixwebsocket", "nlohmann_json", "spdlog", "cxxopts")
    set_languages("cxx23")
    set_exceptions("cxx")
    set_warnings("allextra")

    after_build(function (target)
        os.cp(
            target:targetfile(),
            path.join(os.projectdir(), "bin", path.filename(target:targetfile()))
        )
    end)

target("tests")
    set_kind("binary")
    set_default(false)
    set_languages("cxx23")
    set_exceptions("cxx")
    set_warnings("allextra")
    add_files("tests/**.cpp")
    add_includedirs("src")
    add_packages("doctest", "nlohmann_json")
