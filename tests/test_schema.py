import httpx
import pytest
from graphql import GraphQLSchema, OperationDefinitionNode

from ariadne_codegen.exceptions import IntrospectionError, InvalidGraphqlSyntax
from ariadne_codegen.schema import (
    get_graphql_queries,
    get_graphql_schema_from_path,
    introspect_remote_schema,
    load_graphql_files_from_path,
    read_graphql_file,
    walk_graphql_files,
)

FIRST_SCHEMA = """
    type Query {
        test: Custom
    }

    type Custom {
        node: String
        default: String
    }
"""

SECOND_SCHEMA = """
    type User {
        name: String
    }
"""

INCORRECT_SCHEMA = """
    type Query {
        test: Custom

    type Custom {
        node: String
        default: String
    }
"""

FIRST_FILENAME = "base.graphql"
SECOND_FILENAME = "user.graphql"

FIRST_QUERY = """
    query getUsers {
        users(first: 10) {
            edges {
                node {
                    id
                    username
                }
            }
        }
    }
"""

SECOND_QUERY = """
    query getUsers2 {
        users(first: 10) {
            edges {
                node {
                    id
                    username
                }
            }
        }
    }
"""

INCORRECT_QUERY = """
    query getUsers
        users(first: 10) {
            edges {
                node {
                    id
                    username
                }
            }
        }
    }
"""

FIRST_QUERY_FILENAME = "query1.graphql"
SECOND_QUERY_FILENAME = "query2.graphql"


@pytest.fixture
def single_file_schema(tmp_path_factory):
    file_ = tmp_path_factory.mktemp("schema").joinpath("schema.graphql")
    file_.write_text(FIRST_SCHEMA, encoding="utf-8")
    return file_


@pytest.fixture
def incorrect_schema_file(tmp_path_factory):
    file_ = tmp_path_factory.mktemp("schema").joinpath("schema.graphql")
    file_.write_text(INCORRECT_SCHEMA, encoding="utf-8")
    return file_


@pytest.fixture
def schemas_directory(tmp_path_factory):
    schemas_dir = tmp_path_factory.mktemp("schemas")
    first_file = schemas_dir.joinpath(FIRST_FILENAME)
    first_file.write_text(FIRST_SCHEMA, encoding="utf-8")
    second_file = schemas_dir.joinpath(SECOND_FILENAME)
    second_file.write_text(SECOND_SCHEMA, encoding="utf-8")
    return schemas_dir


@pytest.fixture
def schemas_nested_directories(tmp_path_factory):
    schemas_dir = tmp_path_factory.mktemp("schemas")
    nested_dir = schemas_dir.joinpath("nested")
    nested_dir.mkdir()
    first_file = schemas_dir.joinpath(FIRST_FILENAME)
    first_file.write_text(FIRST_SCHEMA, encoding="utf-8")
    second_file = nested_dir.joinpath(SECOND_FILENAME)
    second_file.write_text(SECOND_SCHEMA, encoding="utf-8")
    return schemas_dir


@pytest.fixture
def path_fixture(request):
    return request.getfixturevalue(request.param)


@pytest.fixture
def single_file_query(tmp_path_factory):
    file_ = tmp_path_factory.mktemp("queries").joinpath(FIRST_QUERY_FILENAME)
    file_.write_text(FIRST_QUERY, encoding="utf-8")
    return file_


@pytest.fixture
def incorrect_file_query(tmp_path_factory):
    file_ = tmp_path_factory.mktemp("queries").joinpath(FIRST_QUERY_FILENAME)
    file_.write_text(INCORRECT_QUERY, encoding="utf-8")
    return file_


@pytest.fixture
def queries_directory(tmp_path_factory):
    schemas_dir = tmp_path_factory.mktemp("queries")
    first_file = schemas_dir.joinpath(FIRST_QUERY_FILENAME)
    first_file.write_text(FIRST_QUERY, encoding="utf-8")
    second_file = schemas_dir.joinpath(SECOND_QUERY_FILENAME)
    second_file.write_text(SECOND_QUERY, encoding="utf-8")
    return schemas_dir


def test_read_graphql_file_returns_content_of_file(single_file_schema):
    assert read_graphql_file(single_file_schema) == FIRST_SCHEMA


def test_read_graphql_file_with_invalid_file_raises_invalid_graphql_syntax_exception(
    incorrect_schema_file,
):
    with pytest.raises(InvalidGraphqlSyntax) as exc:
        read_graphql_file(incorrect_schema_file)
    assert str(incorrect_schema_file) in str(exc)


def test_walk_graphql_files_returns_graphql_files_from_directory(schemas_directory):
    assert sorted(f.name for f in walk_graphql_files(schemas_directory)) == sorted(
        [FIRST_FILENAME, SECOND_FILENAME]
    )


def test_walk_graphql_files_returns_graphql_files_from_nested_directory(
    schemas_nested_directories,
):
    assert sorted(
        f.name for f in walk_graphql_files(schemas_nested_directories)
    ) == sorted([FIRST_FILENAME, SECOND_FILENAME])


def test_load_graphql_files_from_path_returns_schema_from_single_file(
    single_file_schema,
):
    assert load_graphql_files_from_path(single_file_schema) == FIRST_SCHEMA


def test_load_graphql_files_from_path_returns_schema_from_directory(
    schemas_directory,
):
    assert load_graphql_files_from_path(schemas_directory) == "\n".join(
        [FIRST_SCHEMA, SECOND_SCHEMA]
    )


def test_load_graphql_files_from_path_returns_schema_from_nested_directory(
    schemas_nested_directories,
):
    assert load_graphql_files_from_path(schemas_nested_directories) == "\n".join(
        [FIRST_SCHEMA, SECOND_SCHEMA]
    )


@pytest.mark.parametrize(
    "path_fixture",
    ["single_file_schema", "schemas_directory", "schemas_nested_directories"],
    indirect=True,
)
def test_get_graphql_schema_returns_graphql_schema(path_fixture):
    assert isinstance(
        get_graphql_schema_from_path(path_fixture.as_posix()), GraphQLSchema
    )


def test_get_graphql_schema_with_invalid_schema_raises_invalid_graphql_syntax_exception(
    incorrect_schema_file,
):
    with pytest.raises(InvalidGraphqlSyntax):
        get_graphql_schema_from_path(incorrect_schema_file.as_posix())


def test_introspect_remote_schema_called_with_invalid_url_raises_introspection_error(
    mocker,
):
    mocker.patch(
        "ariadne_codegen.schema.httpx.post", side_effect=httpx.InvalidURL("msg")
    )

    with pytest.raises(IntrospectionError):
        introspect_remote_schema("invalid_url")


def test_introspect_remote_schema_raises_introspection_error_for_not_success_response(
    mocker,
):
    mocker.patch(
        "ariadne_codegen.schema.httpx.post",
        return_value=httpx.Response(status_code=400),
    )

    with pytest.raises(IntrospectionError) as exc:
        introspect_remote_schema("http://testserver/graphql/")

    assert "400" in exc.value.args[0]


def test_introspect_remote_schema_raises_introspection_error_for_not_json_response(
    mocker,
):
    mocker.patch(
        "ariadne_codegen.schema.httpx.post",
        return_value=httpx.Response(status_code=200, content="invalid_json"),
    )

    with pytest.raises(IntrospectionError):
        introspect_remote_schema("http://testserver/graphql/")


def test_introspect_remote_schema_raises_introspection_error_for_not_dict_response(
    mocker,
):
    mocker.patch(
        "ariadne_codegen.schema.httpx.post",
        return_value=httpx.Response(status_code=200, content="[]"),
    )

    with pytest.raises(IntrospectionError):
        introspect_remote_schema("http://testserver/graphql/")


def test_introspect_remote_schema_raises_introspection_error_for_json_without_data_key(
    mocker,
):
    mocker.patch(
        "ariadne_codegen.schema.httpx.post",
        return_value=httpx.Response(status_code=200, content='{"not_data": null}'),
    )

    with pytest.raises(IntrospectionError):
        introspect_remote_schema("http://testserver/graphql/")


def test_introspect_remote_schema_raises_introspection_error_for_graphql_errors(mocker):
    mocker.patch(
        "ariadne_codegen.schema.httpx.post",
        return_value=httpx.Response(
            status_code=200,
            content="""
            {
                "data": {},
                "errors": {
                    "message": "Error message",
                    "locations": [{"line": 6, "column": 7}],
                    "path": ["field1", "field2", 1, "id"]
                }
            }
            """,
        ),
    )

    with pytest.raises(IntrospectionError) as exc:
        introspect_remote_schema("http://testserver/graphql/")

    assert "Error message" in exc.value.args[0]


def test_introspect_remote_schema_raises_introspection_error_for_invalid_data_value(
    mocker,
):
    mocker.patch(
        "ariadne_codegen.schema.httpx.post",
        return_value=httpx.Response(
            status_code=200,
            content='{"data": []}',
        ),
    )

    with pytest.raises(IntrospectionError):
        introspect_remote_schema("http://testserver/graphql/")


def test_introspect_remote_schema_returns_introspection_result(mocker):
    mocker.patch(
        "ariadne_codegen.schema.httpx.post",
        return_value=httpx.Response(
            status_code=200,
            content='{"data": {"__schema": {}}}',
        ),
    )

    result = introspect_remote_schema("http://testserver/graphql/")

    assert result == {"__schema": {}}


def test_introspect_remote_schema_uses_provided_headers(mocker):
    mocked_post = mocker.patch(
        "ariadne_codegen.schema.httpx.post",
        return_value=httpx.Response(
            status_code=200,
            content='{"data": {"__schema": {}}}',
        ),
    )

    introspect_remote_schema("http://testserver/graphql/", headers={"test": "value"})

    assert mocked_post.called
    assert mocked_post.called_with(headers={"test": "value"})


@pytest.mark.parametrize("verify_ssl", [True, False])
def test_introspect_remote_schema_uses_provided_verify_ssl_flag(verify_ssl, mocker):
    mocked_post = mocker.patch(
        "ariadne_codegen.schema.httpx.post",
        return_value=httpx.Response(
            status_code=200, content='{"data": {"__schema": {}}}'
        ),
    )

    introspect_remote_schema("http://testserver/graphql/", verify_ssl=verify_ssl)

    assert mocked_post.called
    assert mocked_post.called_with(verify=verify_ssl)


def test_get_graphql_queries_returns_schema_definitions_from_single_file(
    single_file_query,
):
    queries = get_graphql_queries(single_file_query.as_posix())
    assert len(queries) == 1
    assert isinstance(queries[0], OperationDefinitionNode)
    assert queries[0].name
    assert queries[0].name.value == "getUsers"


def test_get_graphql_queries_returns_schema_definitions_from_directory(
    queries_directory,
):
    queries = get_graphql_queries(queries_directory.as_posix())
    assert len(queries) == 2
    assert isinstance(queries[0], OperationDefinitionNode)
    assert isinstance(queries[1], OperationDefinitionNode)
    assert queries[0].name
    assert queries[1].name
    assert queries[0].name.value == "getUsers"
    assert queries[1].name.value == "getUsers2"


def test_get_graphql_queries_with_invalid_file_raises_invalid_graphql_syntax_exception(
    incorrect_file_query,
):
    with pytest.raises(InvalidGraphqlSyntax):
        get_graphql_queries(incorrect_file_query.as_posix())
