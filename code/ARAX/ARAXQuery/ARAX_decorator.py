#!/bin/env python3
import ast
import os
import sqlite3
import sys
from typing import List, Dict, Set

import ujson

sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # ARAXQuery directory
from ARAX_response import ARAXResponse
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.attribute import Attribute
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/Expand/")
import expand_utilities as eu


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


class ARAXDecorator:

    def __init__(self):
        self.core_node_properties = {"name", "category"}
        self.first_tier_attributes = {"description", "iri"}

    def apply(self, response: ARAXResponse) -> ARAXResponse:
        message = response.envelope.message
        response.debug(f"Decorating nodes with metadata from KG2c")

        # Get connected to the local KG2c sqlite database (look up its path using database manager-friendly method)
        path_list = os.path.realpath(__file__).split(os.path.sep)
        rtx_index = path_list.index("RTX")
        rtxc = RTXConfiguration()
        sqlite_dir_path = os.path.sep.join([*path_list[:(rtx_index + 1)], 'code', 'ARAX', 'KnowledgeSources', 'KG2c'])
        sqlite_name = rtxc.kg2c_sqlite_path.split('/')[-1]
        sqlite_file_path = f"{sqlite_dir_path}{os.path.sep}{sqlite_name}"
        connection = sqlite3.connect(sqlite_file_path)
        cursor = connection.cursor()

        # Extract the KG2c nodes from sqlite
        response.debug(f"Looking up corresponding KG2c nodes in sqlite")
        node_keys = set(message.knowledge_graph.nodes)
        node_keys_str = "','".join(node_keys)  # SQL wants ('node1', 'node2') format for string lists
        sql_query = f"SELECT N.node " \
                    f"FROM nodes AS N " \
                    f"WHERE N.id IN ('{node_keys_str}')"
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        cursor.close()
        connection.close()

        # Decorate nodes in the KG with info in these KG2c nodes
        response.debug(f"Adding attributes to nodes in the KG")
        for row in rows:
            kg2c_node_as_dict = ujson.loads(row[0])
            node_id = kg2c_node_as_dict["id"]
            trapi_node = message.knowledge_graph.nodes[node_id]
            if trapi_node.attributes:
                # Only add the critical attributes if this node already has some attributes (prob. came from another KP)
                attributes_to_add = self.first_tier_attributes
                trapi_attributes = self._create_trapi_attributes(attributes_to_add, kg2c_node_as_dict)
                trapi_node.attributes += trapi_attributes
            else:
                # Add all additional info from KG2c if this node doesn't already have any attributes
                kg2c_node_properties = set(kg2c_node_as_dict)
                attributes_to_add = kg2c_node_properties.difference(self.core_node_properties)
                trapi_attributes = self._create_trapi_attributes(attributes_to_add, kg2c_node_as_dict)
                trapi_node.attributes = trapi_attributes

        return response

    @staticmethod
    def _create_trapi_attributes(property_names: Set[str], kg2c_dict_node: Dict[str, any]) -> List[Attribute]:
        new_attributes = []
        for property_name in property_names:
            property_value = kg2c_dict_node.get(property_name)
            if property_value:
                # Extract any booleans that are stored within strings
                if type(property_value) is str:
                    if property_value.lower() == "true" or property_value.lower() == "false":
                        property_value = ast.literal_eval(property_value)
                # Create the actual Attribute object
                trapi_attribute = Attribute(name=property_name,
                                            type=eu.get_attribute_type(property_name),
                                            value=property_value)
                # Also store this value in Attribute.url if it's a URL
                if type(property_value) is str and (property_value.startswith("http:") or property_value.startswith("https:")):
                    trapi_attribute.url = property_value

                new_attributes.append(trapi_attribute)
        return new_attributes

