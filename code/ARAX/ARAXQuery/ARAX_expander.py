#!/bin/env python3


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import sys
import os
import traceback
import json
import ast

from response import Response

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge


class ARAXExpander:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = {'edge_id': None, 'node_id': None, 'kp': None, 'use_synonyms': None, 'synonym_handling': None,
                           'continue_if_no_results': None}

    def describe_me(self):
        """
        Little helper function for internal use that describes the actions and what they can do
        :return:
        """
        # this is quite different than the `describe_me` in ARAX_overlay and ARAX_filter_kg due to expander being less
        # of a dispatcher (like overlay and filter_kg) and more of a single self contained class
        brief_description = """
`expand` effectively takes a query graph (QG) and reaches out to various knowledge providers (KP's) to find all bioentity subgraphs
that satisfy that QG and augments the knowledge graph (KG) with them. As currently implemented, `expand` can utilize the ARA Expander
team KG1 and KG2 Neo4j instances as well as BioThings Explorer to fulfill QG's, with functionality built in to reach out to other KP's as they are rolled out.
        """
        description_list = []
        params_dict = dict()
        params_dict['brief_description'] = brief_description
        params_dict['edge_id'] = {"a query graph edge ID or list of such IDs to expand (optional, default is to expand entire query graph)"}  # this is a workaround due to how self.parameters is utilized in this class
        params_dict['node_id'] = {"a query graph node ID to expand (optional, default is to expand entire query graph)"}
        params_dict['kp'] = {"the knowledge provider to use - current options are `ARAX/KG1`, `ARAX/KG2`, or `BTE` (optional, default is `ARAX/KG1`)"}
        params_dict['enforce_directionality'] = {"whether to obey (vs. ignore) edge directions in query graph - options are `true` or `false` (optional, default is `false`)"}
        params_dict['use_synonyms'] = {"whether to consider synonym curies for query nodes with a curie specified - options are `true` or `false` (optional, default is `true`)"}
        params_dict['synonym_handling'] = {"how to handle synonyms in the answer - options are `map_back` (default; map edges using a synonym back to the original curie) or `add_all` (add synonym nodes as they are - no mapping/merging)"}
        params_dict['continue_if_no_results'] = {"whether to continue execution if no paths are found matching the query graph - options are `true` or `false` (optional, default is `false`)"}
        description_list.append(params_dict)
        return description_list

    #### Top level decision maker for applying filters
    def apply(self, input_message, input_parameters, response=None):

        #### Define a default response
        if response is None:
            response = Response()
        self.response = response
        self.message = input_message
        message = self.message

        #### Basic checks on arguments
        if not isinstance(input_parameters, dict):
            response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return response

        #### Define a complete set of allowed parameters and their defaults
        parameters = self.parameters
        parameters['edge_id'] = [edge.id for edge in self.message.query_graph.edges]
        parameters['node_id'] = self.__get_orphan_query_node_ids(self.message.query_graph)
        parameters['kp'] = "ARAX/KG1"
        parameters['enforce_directionality'] = False
        parameters['use_synonyms'] = True
        parameters['synonym_handling'] = 'map_back'
        parameters['continue_if_no_results'] = False

        #### Loop through the input_parameters and override the defaults and make sure they are allowed
        for key,value in input_parameters.items():
            if key and key not in parameters:
                response.error(f"Supplied parameter {key} is not permitted", error_code="UnknownParameter")
            else:
                if type(value) is str and value.lower() == "true":
                    value = True
                elif type(value) is str and value.lower() == "false":
                    value = False
                parameters[key] = value

        #### Return if any of the parameters generated an error (showing not just the first one)
        if response.status != 'OK':
            return response

        #### Store these final parameters for convenience
        response.data['parameters'] = parameters
        self.parameters = parameters

        #### Do the actual expansion!
        response.debug(f"Applying Expand to Message with parameters {parameters}")
        input_edge_id = self.parameters['edge_id']
        input_node_id = self.parameters['node_id']
        kp_to_use = self.parameters['kp']

        # Convert message knowledge graph to dictionary format, for faster processing
        dict_version_of_kg = self.__convert_standard_kg_to_dict_kg(self.message.knowledge_graph)
        self.message.knowledge_graph = dict_version_of_kg

        if input_edge_id:
            self.response.debug("Extracting sub query graph to expand")
            query_sub_graph = self.__extract_query_subgraph(input_edge_id)
            if response.status != 'OK':
                return response
            self.response.debug(f"Query graph to expand is: {query_sub_graph.to_dict()}")
            # Expand the query graph edge by edge because it's much faster for neo4j queries
            ordered_edges = self.__get_order_to_expand_edges_in(query_sub_graph)
            for edge in ordered_edges:
                self.response.info(f"Expanding edge {edge.id} using {kp_to_use}")
                edge_query_graph = self.__extract_query_subgraph(edge.id)
                answer_knowledge_graph = self.__expand_edge(edge_query_graph, kp_to_use)
                if response.status != 'OK':
                    return response
                self.__merge_answer_kg_into_message_kg(answer_knowledge_graph, edge_query_graph)
                if response.status != 'OK':
                    return response
            # Prune any remaining dead-end paths in our knowledge graph
            # TODO: Update to work for branched query graphs as well (only works for linear currently)
            self.__prune_dead_ends(self.message.knowledge_graph, query_sub_graph)
        if input_node_id:
            input_node_ids = input_node_id if type(input_node_id) is list else [input_node_id]
            for input_node_id in input_node_ids:
                self.response.debug(f"Expanding node {input_node_id} using {kp_to_use}")
                query_node = self.__get_query_node(self.message.query_graph, input_node_id)
                if response.status != 'OK':
                    return response
                answer_knowledge_graph = self.__expand_node(query_node, kp_to_use)
                if response.status != 'OK':
                    return response
                self.__merge_answer_kg_into_message_kg(answer_knowledge_graph, None)
                if response.status != 'OK':
                    return response

        # Convert message knowledge graph back to API standard format
        standard_kg = self.__convert_dict_kg_to_standard_kg(self.message.knowledge_graph)
        self.message.knowledge_graph = standard_kg

        #### Return the response and done
        kg = self.message.knowledge_graph
        response.info(f"After Expand, Message.KnowledgeGraph has {len(kg.nodes)} nodes and {len(kg.edges)} edges")
        return response

    def __get_orphan_query_node_ids(self, query_graph):
        node_ids_used_by_edges = set()
        node_ids = set()
        for edge in query_graph.edges:
            node_ids_used_by_edges.add(edge.source_id)
            node_ids_used_by_edges.add(edge.target_id)
        for node in query_graph.nodes:
            node_ids.add(node.id)
        return list(node_ids.difference(node_ids_used_by_edges))

    def __extract_query_subgraph(self, qedge_ids_to_expand):
        """
        This function extracts the portion of the original query graph (stored in message.query_graph) that this current
        expand() call will expand, based on the query edge ID(s) specified.
        :param qedge_ids_to_expand: A single qedge_id (str) OR a list of qedge_ids.
        :return: A query graph, in Reasoner API standard format.
        """
        query_graph = self.message.query_graph
        sub_query_graph = QueryGraph()
        sub_query_graph.nodes = []
        sub_query_graph.edges = []

        # Make sure edge ID(s) are stored in a list (can be passed in as a string or a list of strings)
        if type(qedge_ids_to_expand) is not list:
            qedge_ids_to_expand = [qedge_ids_to_expand]

        for qedge_id in qedge_ids_to_expand:
            # Make sure this query edge ID actually exists in the larger query graph
            if not any(qedge.id == qedge_id for qedge in query_graph.edges):
                self.response.error(f"An edge with ID '{qedge_id}' does not exist in Message.QueryGraph",
                                    error_code="UnknownValue")
            else:
                # Grab this query edge and its two nodes
                qedge_to_expand = next(qedge for qedge in query_graph.edges if qedge.id == qedge_id)
                qnode_ids = [qedge_to_expand.source_id, qedge_to_expand.target_id]
                qnodes = [qnode for qnode in query_graph.nodes if qnode.id in qnode_ids]

                # Add (a copy of) this edge to our new query sub graph
                new_qedge = self.__copy_qedge(qedge_to_expand)
                if not any(qedge.id == new_qedge.id for qedge in sub_query_graph.edges):
                    sub_query_graph.edges.append(new_qedge)

                # Check for (unusual) case in which this edge has already been expanded (e.g., in a prior Expand() call)
                edge_has_already_been_expanded = False
                if any(node.qnode_id == qnodes[0].id for node in self.message.knowledge_graph['nodes'].values()) and \
                        any(node.qnode_id == qnodes[1].id for node in self.message.knowledge_graph['nodes'].values()):
                    edge_has_already_been_expanded = True

                # Add (copies of) this edge's two nodes to our new query sub graph
                for qnode in qnodes:
                    new_qnode = self.__copy_qnode(qnode)

                    # Handle case where we need to use nodes found in a prior Expand() as the curie for this qnode
                    if not new_qnode.curie and not edge_has_already_been_expanded:
                        curies_of_kg_nodes_with_this_qnode_id = [node.id for node in
                                                                 self.message.knowledge_graph['nodes'].values()
                                                                 if node.qnode_id == new_qnode.id]
                        if curies_of_kg_nodes_with_this_qnode_id:
                            new_qnode.curie = curies_of_kg_nodes_with_this_qnode_id

                    if not any(qnode.id == new_qnode.id for qnode in sub_query_graph.nodes):
                        sub_query_graph.nodes.append(new_qnode)

        return sub_query_graph

    def __expand_edge(self, query_graph, kp_to_use):
        """
        This function answers a single-edge (one-hop) query using the specified knowledge provider. If no KP was
        specified, KG1 is used by default.
        :param query_graph: A (single-edge) Reasoner API standard query graph.
        :param kp_to_use: A string representing the knowledge provider to fulfill this query with.
        :return: An (almost) Reasoner API standard knowledge graph (dictionary version).
        """
        # Make sure we have a valid one-hop query graph
        if len(query_graph.edges) != 1 or len(query_graph.nodes) != 2:
            self.response.error(f"expand_edge() did not receive a valid one-hop query graph: {query_graph.to_dict()}",
                                error_code="InvalidInput")
            return None

        # Route this one-hop query to the proper knowledge provider
        if kp_to_use == 'BTE':
            from Expand.bte_querier import BTEQuerier
            bte_querier = BTEQuerier(self.response)
            answer_kg = bte_querier.answer_one_hop_query(query_graph)
            return answer_kg
        elif kp_to_use == 'ARAX/KG2' or kp_to_use == 'ARAX/KG1':
            from Expand.kg_querier import KGQuerier
            kg_querier = KGQuerier(self.response, kp_to_use)
            answer_kg = kg_querier.answer_one_hop_query(query_graph)
            return answer_kg
        else:
            self.response.error(f"Invalid knowledge provider: {kp_to_use}. Valid options are ARAX/KG1, ARAX/KG2, or BTE",
                                error_code="UnknownValue")
            return None

    def __expand_node(self, query_node, kp_to_use):
        if kp_to_use == 'BTE':
            self.response.error(f"Cannot currently use BTE to answer single node queries", error_code="InvalidQuery")
            return None
        elif kp_to_use == 'ARAX/KG2' or kp_to_use == 'ARAX/KG1':
            from Expand.kg_querier import KGQuerier
            kg_querier = KGQuerier(self.response, kp_to_use)
            answer_kg = kg_querier.answer_single_node_query(query_node)
            return answer_kg
        else:
            self.response.error(f"Invalid knowledge provider: {kp_to_use}. Valid options are ARAX/KG1 or ARAX/KG2")
            return None

    def __merge_answer_kg_into_message_kg(self, answer_knowledge_graph, edge_query_graph):
        """
        This function merges an answer knowledge graph into Message.knowledge_graph. It prevents duplicate nodes/edges
        in the merged KG.
        :param answer_knowledge_graph: An (almost) Reasoner API standard knowledge graph (dictionary version).
        :param edge_query_graph: The single-edge query graph used to generate the answer KG being merged.
        :return: None
        """
        self.response.debug("Merging results into Message.KnowledgeGraph")
        answer_nodes = answer_knowledge_graph.get('nodes')
        answer_edges = answer_knowledge_graph.get('edges')
        existing_nodes = self.message.knowledge_graph.get('nodes')
        existing_edges = self.message.knowledge_graph.get('edges')

        if edge_query_graph:
            # Prune any dead end intermediate nodes in overarching KG, if this is not the first edge to be expanded
            if answer_nodes:
                for qnode in edge_query_graph.nodes:
                    qnode_already_fulfilled = any(node.qnode_id == qnode.id for node in existing_nodes.values())
                    if qnode_already_fulfilled and type(qnode.curie) is list:
                        # Figure out which nodes are dead ends
                        existing_nodes_for_this_qnode = [node.id for node in existing_nodes.values() if node.qnode_id == qnode.id]
                        answer_nodes_for_this_qnode = [node.id for node in answer_nodes.values() if node.qnode_id == qnode.id]
                        existing_nodes_not_in_answer = set(existing_nodes_for_this_qnode).difference(set(answer_nodes_for_this_qnode))
                        if existing_nodes_not_in_answer:
                            self.response.debug(f"Pruning {len(existing_nodes_not_in_answer)} dead end nodes corresponding to "
                                                f"qnode {qnode.id} ({qnode.type})")

                        # Remove them and their connected edges
                        for node_id in existing_nodes_not_in_answer:
                            existing_nodes.pop(node_id)
                            connected_edges_to_remove = [edge.id for edge in existing_edges.values() if
                                                         edge.source_id == node_id or edge.target_id == node_id]
                            for edge in connected_edges_to_remove:
                                existing_edges.pop(edge)

        for node_key, node in answer_nodes.items():
            if not node.qnode_id:
                self.response.error(f"Node {node_key} in answer is missing its corresponding qnode_id", error_code="MissingProperty")
                return
            # Check if this is a duplicate node
            existing_version_of_node = existing_nodes.get(node_key)
            if existing_version_of_node:
                if existing_version_of_node.qnode_id != node.qnode_id:
                    self.response.error(f"Node {node_key} has been returned as an answer for multiple query graph nodes"
                                        f" ({node.qnode_id} and {existing_version_of_node.qnode_id})", error_code="MultipleQGIDs")
                    return
            else:
                existing_nodes[node_key] = node

        for edge_key, edge in answer_edges.items():
            if not edge.qedge_id:
                self.response.error(f"Edge {edge_key} in answer is missing its corresponding qedge_id", error_code="MissingProperty")
                return
            # Check if this is a duplicate edge
            existing_version_of_edge = existing_edges.get(edge_key)
            if existing_version_of_edge:
                if existing_version_of_edge.qedge_id != edge.qedge_id:
                    self.response.error(f"Edge {edge_key} has been returned as an answer for multiple query graph edges"
                                        f" ({edge.qedge_id} and {existing_version_of_edge.qedge_id})", error_code="MultipleQGIDs")
                    return
            else:
                existing_edges[edge_key] = edge

    def __prune_dead_ends(self, knowledge_graph, query_sub_graph):
        """
        This function removes any 'dead-end' paths from the knowledge graph after expansion is done. (Dead-end paths can
        occur because edges are expanded one-by-one.)
        :param knowledge_graph: An (almost) Reasoner API standard knowledge graph (dictionary version).
        :param query_sub_graph: The query graph that was expanded for the current expand call.
        :return: None
        """
        # First figure out our intermediate query nodes and their corresponding query edges
        ordered_qnodes = self.__get_ordered_query_nodes(query_sub_graph)
        qnodes_to_qedges_dict = self.__get_qnode_to_qedge_dict(query_sub_graph)

        if len(ordered_qnodes) > 2:
            # Loop through ordered qnodes (layers) in reverse order (skipping the last)
            index = len(ordered_qnodes) - 2
            while index >= 0:
                current_qnode_id = ordered_qnodes[index].id
                left_qedge_id = qnodes_to_qedges_dict[current_qnode_id].get('left')

                # Start by adding all nodes of this qnode_id to the dict
                nodes_to_edges_dict = dict()
                for node in knowledge_graph['nodes'].values():
                    if node.qnode_id == current_qnode_id:
                        nodes_to_edges_dict[node.id] = {'left': [], 'right': []}

                # Fill out the dict, adding edges to their nodes' edge lists
                for edge in knowledge_graph['edges'].values():
                    edge_node_ids = [edge.source_id, edge.target_id]
                    side = 'left' if edge.qedge_id == left_qedge_id else 'right'
                    for node_id in edge_node_ids:
                        if node_id in nodes_to_edges_dict:
                            nodes_to_edges_dict[node_id][side].append(edge.id)

                # Make sure each node has a right-side edge (indicating it's not a dead end)
                for node_id, edge_dict in nodes_to_edges_dict.items():
                    if not edge_dict.get('right'):
                        # If not, remove it and its left edges from the knowledge graph
                        knowledge_graph['nodes'].pop(node_id)
                        for left_edge_id in edge_dict.get('left'):
                            knowledge_graph['edges'].pop(left_edge_id)

                index -= 1

    def __get_order_to_expand_edges_in(self, query_graph):
        edges_remaining = [edge for edge in query_graph.edges]
        ordered_edges = []
        while edges_remaining:
            if not ordered_edges:
                # Start with an edge that has a node with a curie specified
                edge_with_curie = self.__get_edge_with_curie_node(query_graph)
                first_edge = edge_with_curie if edge_with_curie else edges_remaining[0]
                ordered_edges = [first_edge]
                edges_remaining.pop(edges_remaining.index(first_edge))
            else:
                # Add connected edges in a rightward direction if possible
                right_end_edge = ordered_edges[-1]
                edge_connected_to_right_end = self.__find_connected_edge(edges_remaining, right_end_edge)
                if edge_connected_to_right_end:
                    ordered_edges.append(edge_connected_to_right_end)
                    edges_remaining.pop(edges_remaining.index(edge_connected_to_right_end))
                else:
                    left_end_edge = ordered_edges[0]
                    edge_connected_to_left_end = self.__find_connected_edge(edges_remaining, left_end_edge)
                    if edge_connected_to_left_end:
                        ordered_edges.insert(0, edge_connected_to_left_end)
                        edges_remaining.pop(edges_remaining.index(edge_connected_to_left_end))
        return ordered_edges

    def __get_ordered_query_nodes(self, query_graph):
        ordered_edges = self.__get_order_to_expand_edges_in(query_graph)
        ordered_nodes = []
        # First add intermediate nodes in order
        if len(ordered_edges) > 1:
            for num in range(len(ordered_edges) - 1):
                current_edge = ordered_edges[num]
                next_edge = ordered_edges[num + 1]
                current_edge_node_ids = {current_edge.source_id, current_edge.target_id}
                next_edge_node_ids = {next_edge.source_id, next_edge.target_id}
                common_node_id = list(current_edge_node_ids.intersection(next_edge_node_ids))[0]  # Note: Only handle linear query graphs
                ordered_nodes.append(self.__get_query_node(query_graph, common_node_id))

            # Then tack the initial node onto the beginning
            first_edge = ordered_edges[0]
            second_edge = ordered_edges[1]
            first_edge_node_ids = {first_edge.source_id, first_edge.target_id}
            second_edge_node_ids = {second_edge.source_id, second_edge.target_id}
            first_node_id = list(first_edge_node_ids.difference(second_edge_node_ids))[0]
            ordered_nodes.insert(0, self.__get_query_node(query_graph, first_node_id))

            # And tack the last node onto the end
            last_edge = ordered_edges[-1]
            second_to_last_edge = ordered_edges[-2]
            last_edge_node_ids = {last_edge.source_id, last_edge.target_id}
            second_to_last_edge_node_ids = {second_to_last_edge.source_id, second_to_last_edge.target_id}
            last_node_id = list(last_edge_node_ids.difference(second_to_last_edge_node_ids))[0]
            ordered_nodes.append(self.__get_query_node(query_graph, last_node_id))
        else:
            # TODO: Pick first node to be one with curie?
            source_node = self.__get_query_node(query_graph, ordered_edges[0].source_id)
            target_node = self.__get_query_node(query_graph, ordered_edges[0].target_id)
            ordered_nodes = [source_node, target_node]

        return ordered_nodes

    def __get_qnode_to_qedge_dict(self, query_graph):
        ordered_edges = self.__get_order_to_expand_edges_in(query_graph)
        ordered_nodes = self.__get_ordered_query_nodes(query_graph)
        qnode_to_qedge_dict = dict()
        for node in ordered_nodes:
            node_index = ordered_nodes.index(node)
            left_edge_index = node_index - 1
            right_edge_index = node_index
            left_edge_id = ordered_edges[left_edge_index].id if left_edge_index >= 0 else None
            right_edge_id = ordered_edges[right_edge_index].id if right_edge_index < len(ordered_edges) else None
            qnode_to_qedge_dict[node.id] = {'left': left_edge_id, 'right': right_edge_id}
        return qnode_to_qedge_dict

    def __get_edge_with_curie_node(self, query_graph):
        for edge in query_graph.edges:
            source_node = self.__get_query_node(query_graph, edge.source_id)
            target_node = self.__get_query_node(query_graph, edge.target_id)
            if source_node.curie or target_node.curie:
                return edge
        return None

    def __find_connected_edge(self, edge_list, edge):
        edge_node_ids = {edge.source_id, edge.target_id}
        for potential_connected_edge in edge_list:
            potential_connected_edge_node_ids = {potential_connected_edge.source_id, potential_connected_edge.target_id}
            if edge_node_ids.intersection(potential_connected_edge_node_ids):
                return potential_connected_edge
        return None

    def __get_query_node(self, query_graph, qnode_id):
        matching_nodes = [node for node in query_graph.nodes if node.id == qnode_id]
        if not matching_nodes:
            self.response.error(f"A node with ID '{qnode_id}' does not exist in Message.QueryGraph", error_code="UnknownValue")
            return None
        else:
            return matching_nodes[0]

    def __convert_standard_kg_to_dict_kg(self, knowledge_graph):
        dict_kg = dict()
        dict_kg['nodes'] = dict()
        dict_kg['edges'] = dict()
        if knowledge_graph.nodes is not None:
            for node in knowledge_graph.nodes:
                dict_kg['nodes'][node.id] = node
        if knowledge_graph.edges is not None:
            for edge in knowledge_graph.edges:
                dict_kg['edges'][edge.id] = edge
        return dict_kg

    def __convert_dict_kg_to_standard_kg(self, dict_kg):
        standard_kg = KnowledgeGraph()
        standard_kg.nodes = []
        standard_kg.edges = []
        for node_key, node in dict_kg.get('nodes').items():
            standard_kg.nodes.append(node)
        for edge_key, edge in dict_kg.get('edges').items():
            standard_kg.edges.append(edge)
        return standard_kg

    def __copy_qedge(self, old_qedge):
        new_qedge = QEdge()
        for edge_property in new_qedge.to_dict():
            value = getattr(old_qedge, edge_property)
            setattr(new_qedge, edge_property, value)
        return new_qedge

    def __copy_qnode(self, old_qnode):
        new_qnode = QNode()
        for node_property in new_qnode.to_dict():
            value = getattr(old_qnode, node_property)
            setattr(new_qnode, node_property, value)
        return new_qnode

##########################################################################################
def main():

    #### Note that most of this is just manually doing what ARAXQuery() would normally do for you

    #### Create a response object
    response = Response()

    #### Create an ActionsParser object
    from actions_parser import ActionsParser
    actions_parser = ActionsParser()
 
    #### Set a list of actions
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL112)",  # acetaminophen
        "add_qnode(id=n01, type=protein, is_set=true)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        # "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        # "add_qnode(id=n01, type=protein, is_set=True)",
        # "add_qnode(id=n02, type=chemical_substance)",
        # "add_qedge(id=e00, source_id=n01, target_id=n00)",
        # "add_qedge(id=e01, source_id=n01, target_id=n02, type=physically_interacts_with)",
        # "add_qnode(curie=DOID:8398, id=n00)",  # osteoarthritis
        # "add_qnode(type=phenotypic_feature, is_set=True, id=n01)",
        # "add_qnode(type=disease, is_set=true, id=n02)",
        # "add_qedge(source_id=n01, target_id=n00, id=e00)",
        # "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(edge_id=e00, kp=BTE)",
        # "expand(edge_id=e00, kp=ARAX/KG2)",
        # "expand(edge_id=e01, kp=ARAX/KG2)",
        # "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
        "return(message=true, store=false)",
    ]

    #### Parse the raw action_list into commands and parameters
    result = actions_parser.parse(actions_list)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response
    actions = result.data['actions']

    #### Create a Messager and an Expander and execute the command list
    from ARAX_messenger import ARAXMessenger
    messenger = ARAXMessenger()
    expander = ARAXExpander()

    #### Loop over each action and dispatch to the correct place
    for action in actions:
        if action['command'] == 'create_message':
            result = messenger.create_message()
            message = result.data['message']
            response.data = result.data
        elif action['command'] == 'add_qnode':
            result = messenger.add_qnode(message,action['parameters'])
        elif action['command'] == 'add_qedge':
            result = messenger.add_qedge(message,action['parameters'])
        elif action['command'] == 'expand':
            result = expander.apply(message,action['parameters'])
        elif action['command'] == 'return':
            break
        else:
            response.error(f"Unrecognized command {action['command']}", error_code="UnrecognizedCommand")
            print(response.show(level=Response.DEBUG))
            return response

        #### Merge down this result and end if we're in an error state
        response.merge(result)
        if result.status != 'OK':
            print(response.show(level=Response.DEBUG))
            return response

    #### Show the final response
    # print(json.dumps(ast.literal_eval(repr(message.knowledge_graph)),sort_keys=True,indent=2))
    print(response.show(level=Response.DEBUG))


if __name__ == "__main__":
    main()
