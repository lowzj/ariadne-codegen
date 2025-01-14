import ast

from ariadne_codegen.client_generators.init_file import InitFileGenerator

from ..utils import filter_imports


def test_add_import_adds_correct_objects_to_list():
    from_ = "file_name"
    class_name = "TestClass"
    generator = InitFileGenerator()

    generator.add_import(names=[class_name], from_=from_, level=1)

    import_ = generator.imports[0]
    assert len(generator.imports) == 1
    assert isinstance(import_, ast.ImportFrom)
    assert import_.module == from_
    assert [alias.name for alias in import_.names] == [class_name]
    assert import_.level == 1


def test_add_import_triggers_generate_init_import_hook_method(mocker):
    mocked_plugin_manager = mocker.MagicMock()
    generator = InitFileGenerator(plugin_manager=mocked_plugin_manager)

    generator.add_import(names=["TestClass"], from_="test", level=1)

    assert mocked_plugin_manager.generate_init_import.called


def test_add_import_with_empty_names_list_doesnt_add_invalid_import():
    generator = InitFileGenerator()

    generator.add_import(names=[], from_="abcd", level=1)
    module = generator.generate()

    imports = filter_imports(module)
    assert not imports


def test_generate_without_imports_returns_empty_module():
    generator = InitFileGenerator()

    module = generator.generate()

    assert isinstance(module, ast.Module)
    assert not module.body


def test_generate_with_added_imports_returns_module():
    generator = InitFileGenerator()
    name1, name2 = "Abcd", "Xyz"
    generator.add_import([name1], "abcd", 1)
    generator.add_import([name2], "xyz", 1)

    module = generator.generate()

    assign_stmt = module.body[2]
    assert len(module.body) == 3
    assert isinstance(assign_stmt, ast.Assign)
    assert [n.id for n in assign_stmt.targets] == ["__all__"]
    assert isinstance(assign_stmt.value, ast.List)
    assert [c.value for c in assign_stmt.value.elts] == [name1, name2]


def test_generate_triggers_generate_init_module_from_plugin_manager(mocker):
    mocked_plugin_manager = mocker.MagicMock()
    generator = InitFileGenerator(plugin_manager=mocked_plugin_manager)

    generator.generate()

    assert mocked_plugin_manager.generate_init_module.called
