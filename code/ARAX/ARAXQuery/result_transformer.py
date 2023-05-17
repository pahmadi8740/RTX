import os
import sys
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # ARAXQuery directory
from ARAX_response import ARAXResponse

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.auxiliary_graph import AuxiliaryGraph


class ResultTransformer:

    @staticmethod
    def transform(response: ARAXResponse):
        message = response.envelope.message
        if message.results:
            if not hasattr(response, "original_query_graph") or not response.original_query_graph.nodes:
                response.error(f"The original QG was never saved before ARAX edited it! So we can't transform results "
                               f"to TRAPI 1.4 format (i.e., support_graphs).", error_code="NoOriginalQG")
                return

            response.info(f"Transforming results to TRAPI 1.4 format (moving 'virtual' nodes/edges to support graphs)")

            original_qedge_keys = set(response.original_query_graph.edges)
            original_qnode_keys = set(response.original_query_graph.nodes)
            non_orphan_qnode_keys = {qnode_key for qedge in response.original_query_graph.edges.values()
                                     for qnode_key in {qedge.subject, qedge.object}}
            response.debug(f"Original input QG contained qnodes {original_qnode_keys} and qedges {original_qedge_keys}")
            response.debug(f"Non-orphan qnodes in original QG are: {non_orphan_qnode_keys}")
            all_virtual_qedge_keys = set()

            for result in message.results:
                # First figure out which edges in this result are 'virtual' and what option groups they belong to
                edge_bindings = result.analyses[0].edge_bindings
                qedge_keys_in_result = set(edge_bindings)
                virtual_qedge_keys = qedge_keys_in_result.difference(original_qedge_keys)
                all_virtual_qedge_keys = all_virtual_qedge_keys.union(virtual_qedge_keys)  # Record these for log info
                virtual_edge_groups_dict = defaultdict(set)
                for virtual_qedge_key in virtual_qedge_keys:
                    virtual_qedge = message.query_graph.edges[virtual_qedge_key]
                    option_group_id = virtual_qedge.option_group_id
                    virtual_edge_keys = {edge_binding.id for edge_binding in edge_bindings[virtual_qedge_key]}
                    virtual_edge_groups_dict[option_group_id] = virtual_edge_groups_dict[option_group_id].union(virtual_edge_keys)
                    # Note: All edges not belonging to an option group are lumped together under 'None' key

                # Create a support graph for each group
                if virtual_edge_groups_dict:
                    if message.auxiliary_graphs is None:
                        message.auxiliary_graphs = dict()
                    if result.analyses[0].support_graphs is None:
                        result.analyses[0].support_graphs = []
                for group_id, group_edge_keys in virtual_edge_groups_dict.items():
                    group_id_str = f"_{group_id}" if group_id else ""
                    ordered_edge_keys = sorted(list(group_edge_keys))
                    aux_graph_id_str = ";".join(ordered_edge_keys) if len(ordered_edge_keys) < 5 else f"{len(message.auxiliary_graphs)}"
                    aux_graph_key = f"aux_graph_{aux_graph_id_str}{group_id_str}"
                    # Refer to this aux graph from the current result
                    result.analyses[0].support_graphs.append(aux_graph_key)
                    # Create and save the aux graph in the central location (on Message), if it doesn't yet exist
                    if aux_graph_key not in message.auxiliary_graphs:
                        message.auxiliary_graphs[aux_graph_key] = AuxiliaryGraph(edges=list(group_edge_keys))

                # Delete virtual edges (since we moved them to supporting_graphs)
                for virtual_qedge_key in virtual_qedge_keys:
                    del edge_bindings[virtual_qedge_key]

                # Delete any virtual node bindings (strangely, nodes aren't allowed in AuxGraphs; only live in KG)
                node_bindings = result.node_bindings
                qnode_keys_in_result = set(node_bindings)
                virtual_qnode_keys = qnode_keys_in_result.difference(original_qnode_keys)
                for virtual_qnode_key in virtual_qnode_keys:
                    del node_bindings[virtual_qnode_key]

                # Delete bindings for any subclass parent nodes that are now orphans (they'll still be in the KG)
                for non_orphan_qnode_key in non_orphan_qnode_keys:
                    node_keys = {binding.id for binding in node_bindings[non_orphan_qnode_key]}
                    node_keys_used_by_result_edges = {node_key for qedge_key in original_qedge_keys
                                                      for binding in result.analyses[0].edge_bindings[qedge_key]
                                                      for node_key in {message.knowledge_graph.edges[binding.id].subject,
                                                                       message.knowledge_graph.edges[binding.id].object}}
                    orphan_node_keys = node_keys.difference(node_keys_used_by_result_edges)
                    non_orphan_node_bindings = [binding for binding in result.node_bindings[non_orphan_qnode_key]
                                                if binding.id not in orphan_node_keys]
                    result.node_bindings[non_orphan_qnode_key] = non_orphan_node_bindings

            # Return the original query graph in the response, rather than our edited version
            response.debug(f"Replacing ARAX's internal edited QG with the original input QG..")
            message.query_graph = response.original_query_graph

            # Log some final stats about result transformation
            response.debug(f"Virtual qedge keys moved to support_graphs were: {all_virtual_qedge_keys}")
            response.debug(f"There are a total of {len(message.auxiliary_graphs) if message.auxiliary_graphs else 0} AuxiliaryGraphs.")
            response.info(f"Done transforming results to TRAPI 1.4 format (i.e., using support_graphs)")