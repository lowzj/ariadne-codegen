import ast
from typing import Dict, List, Optional, Tuple, Union

from graphql import (
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    ListTypeNode,
    NamedTypeNode,
    NonNullTypeNode,
    TypeNode,
    VariableDefinitionNode,
)

from ..codegen import (
    generate_annotation_name,
    generate_arg,
    generate_arguments,
    generate_call,
    generate_constant,
    generate_dict,
    generate_list_annotation,
    generate_name,
)
from ..exceptions import ParsingError
from ..plugins.manager import PluginManager
from ..utils import str_to_snake_case
from .constants import ANY, OPTIONAL, SIMPLE_TYPE_MAP
from .scalars import ScalarData


class ArgumentsGenerator:
    def __init__(
        self,
        schema: GraphQLSchema,
        convert_to_snake_case: bool = True,
        custom_scalars: Optional[Dict[str, ScalarData]] = None,
        plugin_manager: Optional[PluginManager] = None,
    ) -> None:
        self.schema = schema
        self.convert_to_snake_case = convert_to_snake_case
        self.custom_scalars = custom_scalars if custom_scalars else {}
        self.plugin_manager = plugin_manager

        self.used_types: List[str] = []
        self._used_enums: List[str] = []
        self._used_inputs: List[str] = []
        self._used_custom_scalars: List[str] = []

    def generate(
        self, variable_definitions: Tuple[VariableDefinitionNode, ...]
    ) -> Tuple[ast.arguments, ast.Dict]:
        """Generate arguments from given variable definitions."""
        required_args: List[ast.arg] = [generate_arg("self")]
        optional_args: List[ast.arg] = []
        dict_ = generate_dict()
        for variable_definition in variable_definitions:
            org_name = variable_definition.variable.name.value
            name = self._process_name(org_name)
            annotation, used_custom_scalar = self._parse_type_node(
                variable_definition.type
            )

            arg = generate_arg(name, annotation)
            if self.is_nullable(annotation):
                optional_args.append(arg)
            else:
                required_args.append(arg)

            dict_.keys.append(generate_constant(org_name))
            dict_.values.append(self._get_dict_value(name, used_custom_scalar))

        arguments = generate_arguments(
            args=required_args + optional_args,
            defaults=[generate_constant(None) for _ in optional_args],
        )

        if self.plugin_manager:
            arguments = self.plugin_manager.generate_arguments(
                arguments, variable_definitions=variable_definitions
            )
            dict_ = self.plugin_manager.generate_arguments_dict(
                dict_, variable_definitions=variable_definitions
            )
        return arguments, dict_

    def get_used_enums(self) -> List[str]:
        return self._used_enums

    def get_used_inputs(self) -> List[str]:
        return self._used_inputs

    def get_used_custom_scalars(self) -> List[str]:
        return self._used_custom_scalars

    def _process_name(self, name: str) -> str:
        if self.convert_to_snake_case:
            return str_to_snake_case(name)
        return name

    def _parse_type_node(
        self,
        node: Union[NamedTypeNode, ListTypeNode, NonNullTypeNode, TypeNode],
        nullable: bool = True,
    ) -> Tuple[Union[ast.Name, ast.Subscript], Optional[str]]:
        if isinstance(node, NamedTypeNode):
            return self._parse_named_type_node(node, nullable)

        if isinstance(node, ListTypeNode):
            sub_annotation, used_custom_scalar = self._parse_type_node(
                node.type, nullable
            )
            return (
                generate_list_annotation(sub_annotation, nullable),
                used_custom_scalar,
            )

        if isinstance(node, NonNullTypeNode):
            return self._parse_type_node(node.type, False)

        raise ParsingError("Invalid argument type.")

    def _parse_named_type_node(
        self, node: NamedTypeNode, nullable: bool = True
    ) -> Tuple[Union[ast.Name, ast.Subscript], Optional[str]]:
        name = node.name.value
        type_ = self.schema.type_map.get(name)
        if not type_:
            raise ParsingError(f"Argument type {name} not found in schema.")

        used_custom_scalar = None
        if isinstance(type_, GraphQLInputObjectType):
            self._used_inputs.append(name)
        elif isinstance(type_, GraphQLEnumType):
            self._used_enums.append(name)
        elif isinstance(type_, GraphQLScalarType):
            if name not in self.custom_scalars:
                name = SIMPLE_TYPE_MAP.get(name, ANY)
            else:
                used_custom_scalar = name
                name = self.custom_scalars[name].type_
        else:
            raise ParsingError(f"Incorrect argument type {name}")

        return generate_annotation_name(name, nullable), used_custom_scalar

    def is_nullable(self, annotation: Union[ast.Name, ast.Subscript]) -> bool:
        return (
            isinstance(annotation, ast.Subscript)
            and isinstance(annotation.value, ast.Name)
            and annotation.value.id == OPTIONAL
        )

    def _get_dict_value(
        self, name: str, used_custom_scalar: Optional[str]
    ) -> Union[ast.Name, ast.Call]:
        if used_custom_scalar:
            self._used_custom_scalars.append(used_custom_scalar)
            scalar_data = self.custom_scalars[used_custom_scalar]
            if scalar_data.serialize:
                return generate_call(
                    func=generate_name(scalar_data.serialize),
                    args=[generate_name(name)],
                )

        return generate_name(name)
